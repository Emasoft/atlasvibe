#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `get_file_encoding`:
#   - If chardet provides an encoding and it can decode the sample, use it, even if confidence is not very high (e.g., > 0.3).
#   - This aims to better handle encodings like cp1252 that chardet might detect with lower confidence than UTF-8 but are correct.
# - `scan_directory_for_occurrences`: Changed `item_abs_path.read_text(..., newline='')`
#   to use `with open(item_abs_path, 'r', ..., newline='') as f: f.read()`
#   to resolve the "unexpected keyword argument 'newline'" error seen in test logs.
#   This ensures consistent file reading for line ending preservation.
# - `_execute_content_line_transaction`: Changed `open(current_abs_path, 'r', ..., newline=None)`
#   to `open(current_abs_path, 'r', ..., newline='')` to preserve line endings during file reading.
#   This ensures that the `ORIGINAL_LINE_CONTENT` stored in transactions and processed by
#   `replace_occurrences` retains its true line endings, which are then preserved on write.
# - `execute_all_transactions`: Modified the logic for populating `path_translation_map`
#   when `resume=True` or (`skip_scan=True` and `not resume`). The condition
#   `tx.get("ERROR_MESSAGE") != "DRY_RUN"` was removed when checking for COMPLETED rename
#   transactions. This allows `skip_scan` mode to correctly use the renames planned
#   during a previous dry run to build its understanding of the current file paths.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import os
import shutil
import json
import uuid
from pathlib import Path
from typing import Any, cast # Keep Any and cast if specifically needed for dynamic parts
import collections.abc # For Iterator, Callable
from enum import Enum
import chardet
import unicodedata # For NFC normalization
import time
import pathspec
import errno
from striprtf.striprtf import rtf_to_text
from isbinary import is_binary_file

from replace_logic import replace_occurrences, get_scan_pattern, get_raw_stripped_keys, strip_diacritics, strip_control_characters

class SandboxViolationError(Exception):
    pass
class MockableRetriableError(OSError):
    pass

DEFAULT_ENCODING_FALLBACK = 'utf-8'
TRANSACTION_FILE_BACKUP_EXT = ".bak"
SELF_TEST_ERROR_FILE_BASENAME = "error_file_flojoy.txt"
BINARY_MATCHES_LOG_FILE = "binary_files_matches.log"

RETRYABLE_OS_ERRORNOS = {
    errno.EACCES, errno.EBUSY, errno.ETXTBSY,
}

class TransactionType(str, Enum):
    FILE_NAME = "FILE_NAME"
    FOLDER_NAME = "FOLDER_NAME"
    FILE_CONTENT_LINE = "FILE_CONTENT_LINE"

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRY_LATER = "RETRY_LATER"

def get_file_encoding(file_path: Path, sample_size: int = 10240) -> str | None:
    if file_path.suffix.lower() == '.rtf':
        return 'latin-1'
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
        if not raw_data:
            return DEFAULT_ENCODING_FALLBACK

        detected = chardet.detect(raw_data)
        detected_encoding: str | None = detected.get('encoding')
        confidence: float = detected.get('confidence', 0.0)

        # Try chardet's suggestion first if it's somewhat confident and can decode the sample
        if detected_encoding and confidence > 0.3: # Lowered confidence threshold slightly
            try:
                raw_data.decode(detected_encoding)
                # print(f"DEBUG: Using chardet's encoding: {detected_encoding} (confidence: {confidence}) for {file_path.name}")
                return detected_encoding
            except (UnicodeDecodeError, LookupError):
                # print(f"DEBUG: Chardet's encoding {detected_encoding} failed to decode sample for {file_path.name}. Confidence: {confidence}")
                pass # Fall through

        # If chardet's suggestion failed or confidence was too low, try UTF-8
        try:
            raw_data.decode('utf-8')
            # print(f"DEBUG: Using UTF-8 for {file_path.name} (chardet failed or low conf)")
            return 'utf-8'
        except UnicodeDecodeError:
            # print(f"DEBUG: UTF-8 decoding also failed for {file_path.name}")
            # If UTF-8 also fails, and chardet had a suggestion (even if it failed sample decode or was low conf),
            # it might be a last resort if it's a known encoding.
            if detected_encoding and detected_encoding.lower() != 'ascii': # Avoid using 'ascii' if UTF-8 failed.
                try:
                    # Test again, maybe the sample was tricky but the whole file might be okay with it.
                    # This is a bit of a stretch but could save some cp1252/latin1 files.
                    b"test".decode(detected_encoding) # Quick check if encoding name is valid
                    # print(f"DEBUG: Re-trying chardet's initial low-confidence/failed-sample encoding {detected_encoding} for {file_path.name}")
                    return detected_encoding
                except (UnicodeDecodeError, LookupError):
                    pass # Fall through to default
            
            # print(f"DEBUG: Falling back to {DEFAULT_ENCODING_FALLBACK} for {file_path.name}")
            return DEFAULT_ENCODING_FALLBACK
            
    except Exception as e:
        # print(f"DEBUG: Exception in get_file_encoding for {file_path.name}: {e}. Falling back to {DEFAULT_ENCODING_FALLBACK}.")
        return DEFAULT_ENCODING_FALLBACK


def load_ignore_patterns(ignore_file_path: Path) -> pathspec.PathSpec | None:
    if not ignore_file_path.is_file():
        return None
    try:
        with open(ignore_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            patterns = f.readlines()
        valid_patterns = [p for p in (line.strip() for line in patterns) if p and not p.startswith('#')]
        return pathspec.PathSpec.from_lines('gitwildmatch', valid_patterns) if valid_patterns else None
    except Exception as e:
        print(f"Warning: Could not load ignore file {ignore_file_path}: {e}")
        return None

def _walk_for_scan(
    root_dir: Path, excluded_dirs_abs: list[Path],
    ignore_symlinks: bool, ignore_spec: pathspec.PathSpec | None
) -> collections.abc.Iterator[Path]:
    for item_path_from_rglob in root_dir.rglob("*"): # item_path_from_rglob is already absolute
        # Use item_path_from_rglob directly for checks. Do not resolve symlinks at this stage.
        if ignore_symlinks and item_path_from_rglob.is_symlink():
            continue
        is_excluded_by_dir_arg = any(item_path_from_rglob == ex_dir or \
                                   (ex_dir.is_dir() and str(item_path_from_rglob).startswith(str(ex_dir) + os.sep))
                                   for ex_dir in excluded_dirs_abs)
        if is_excluded_by_dir_arg:
            continue
        if ignore_spec:
            try:
                path_rel_to_root_for_spec = item_path_from_rglob.relative_to(root_dir)
                if ignore_spec.match_file(str(path_rel_to_root_for_spec)) or \
                   (item_path_from_rglob.is_dir() and ignore_spec.match_file(str(path_rel_to_root_for_spec) + '/')):
                    continue
            except ValueError:
                # item is not under root_dir, should not happen if rglob is on absolute root_dir
                pass
            except Exception as e:
                print(f"Warning: Error during ignore_spec matching for {item_path_from_rglob} relative to {root_dir}: {e}")
        yield item_path_from_rglob

def _get_current_absolute_path(
    original_relative_path_str: str, root_dir: Path,
    path_translation_map: dict[str, str], cache: dict[str, Path]
) -> Path:
    if original_relative_path_str in cache:
        return cache[original_relative_path_str]
    if original_relative_path_str == ".":
        cache["."] = root_dir
        return root_dir
    original_path_obj = Path(original_relative_path_str)
    parent_rel_str = "." if original_path_obj.parent == Path('.') else str(original_path_obj.parent)
    current_parent_abs_path = _get_current_absolute_path(parent_rel_str, root_dir, path_translation_map, cache)
    current_item_name = path_translation_map.get(original_relative_path_str, original_path_obj.name)
    current_abs_path = current_parent_abs_path / current_item_name
    cache[original_relative_path_str] = current_abs_path
    return current_abs_path

def scan_directory_for_occurrences(
    root_dir: Path, excluded_dirs: list[str], excluded_files: list[str],
    file_extensions: list[str] | None, ignore_symlinks: bool,
    ignore_spec: pathspec.PathSpec | None,
    resume_from_transactions: list[dict[str, Any]] | None = None,
    paths_to_force_rescan: set[str] | None = None,
    skip_file_renaming: bool = False, skip_folder_renaming: bool = False, skip_content: bool = False
) -> list[dict[str, Any]]:
    processed_transactions: list[dict[str, Any]] = []
    existing_transaction_ids: set[tuple[str, str, int]] = set()
    paths_to_force_rescan_internal: set[str] = paths_to_force_rescan if paths_to_force_rescan is not None else set()
    abs_root_dir = root_dir

    scan_pattern = get_scan_pattern()
    raw_keys_for_binary_search = get_raw_stripped_keys()

    if resume_from_transactions is not None:
        processed_transactions = list(resume_from_transactions)
        for tx in resume_from_transactions:
            tx_rel_path = tx.get("PATH")
            if tx_rel_path in paths_to_force_rescan_internal and tx.get("TYPE") == TransactionType.FILE_CONTENT_LINE.value:
                continue
            tx_type, tx_line = tx.get("TYPE"), tx.get("LINE_NUMBER", 0)
            if tx_type and tx_rel_path:
                existing_transaction_ids.add((tx_rel_path, tx_type, tx_line))

    resolved_abs_excluded_dirs = []
    for d_str in excluded_dirs:
        try:
            resolved_abs_excluded_dirs.append(abs_root_dir.joinpath(d_str).resolve(strict=False))
        except Exception:
            resolved_abs_excluded_dirs.append(abs_root_dir.joinpath(d_str).absolute())

    excluded_basenames = {Path(f).name for f in excluded_files if Path(f).name == f and os.path.sep not in f and not ('/' in f or '\\' in f)}
    excluded_relative_paths_set = {f.replace("\\", "/") for f in excluded_files if os.path.sep in f or '/' in f or '\\' in f}

    normalized_extensions = {ext.lower() for ext in file_extensions} if file_extensions else None
    binary_log_path = abs_root_dir / BINARY_MATCHES_LOG_FILE

    item_iterator = _walk_for_scan(abs_root_dir, resolved_abs_excluded_dirs, ignore_symlinks, ignore_spec)
    first_item = next(item_iterator, None)
    if first_item is None: # No items found at all after basic walk setup
        return [] # Ensure it returns a list
    def combined_iterator() -> collections.abc.Iterator[Path]:
        if first_item:
            yield first_item
        yield from item_iterator

    for item_abs_path in combined_iterator():
        try:
            relative_path_str = str(item_abs_path.relative_to(abs_root_dir)).replace("\\", "/")
        except ValueError:
            continue
        if item_abs_path.name in excluded_basenames or relative_path_str in excluded_relative_paths_set:
            continue

        original_name = item_abs_path.name
        # For scanning, we need to see if the name *would* change if processed.
        # The scan_pattern is built from NFC-normalized, stripped keys.
        # To check if scan_pattern matches, we should search on a similarly processed version of original_name.
        # `strip_diacritics` does NFD internally.
        searchable_name = unicodedata.normalize('NFC', strip_control_characters(strip_diacritics(original_name)))
        if (scan_pattern and scan_pattern.search(searchable_name)) and \
           (replace_occurrences(original_name) != original_name): # Pass original_name to replace_occurrences
            tx_type: str | None = None
            if item_abs_path.is_dir() and not item_abs_path.is_symlink():
                if not skip_folder_renaming:
                    tx_type = TransactionType.FOLDER_NAME.value
            elif item_abs_path.is_file() or item_abs_path.is_symlink():
                if not skip_file_renaming:
                    tx_type = TransactionType.FILE_NAME.value
            if tx_type:
                tx_id_tuple = (relative_path_str, tx_type, 0)
                if tx_id_tuple not in existing_transaction_ids:
                    processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":tx_type, "PATH":relative_path_str, "ORIGINAL_NAME":original_name, "LINE_NUMBER":0, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                    existing_transaction_ids.add(tx_id_tuple)

        if not skip_content and item_abs_path.is_file() and not item_abs_path.is_symlink():
            is_rtf = item_abs_path.suffix.lower() == '.rtf'
            try:
                is_bin = is_binary_file(str(item_abs_path))
            except FileNotFoundError:
                continue
            except Exception as e_isbin:
                print(f"Warning: Could not determine if {item_abs_path} is binary: {e_isbin}. Skipping content scan.")
                continue

            if is_bin and not is_rtf:
                if raw_keys_for_binary_search:
                    try:
                        with open(item_abs_path, 'rb') as bf:
                            content_bytes = bf.read()
                        for key_str in raw_keys_for_binary_search:
                            try:
                                key_bytes = key_str.encode('utf-8')
                            except UnicodeEncodeError:
                                continue
                            offset = 0
                            while True:
                                idx = content_bytes.find(key_bytes, offset)
                                if idx == -1:
                                    break
                                with open(binary_log_path, 'a', encoding='utf-8') as log_f:
                                    log_f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - MATCH: File: {relative_path_str}, Key: '{key_str}', Offset: {idx}\n")
                                offset = idx + len(key_bytes)
                    except Exception as e:
                        print(f"Warn: Error processing binary {item_abs_path} for logging: {e}")
                continue

            if normalized_extensions and item_abs_path.suffix.lower() not in normalized_extensions and not is_rtf:
                 continue

            file_content_for_scan: str | None = None
            file_encoding = DEFAULT_ENCODING_FALLBACK

            if is_rtf:
                try:
                    rtf_source_bytes = item_abs_path.read_bytes()
                    rtf_source_str = ""
                    for enc_try in ['latin-1', 'cp1252', 'utf-8']:
                        try:
                            rtf_source_str = rtf_source_bytes.decode(enc_try)
                            break
                        except UnicodeDecodeError:
                            pass
                    if not rtf_source_str:
                        rtf_source_str = rtf_source_bytes.decode('utf-8', errors='ignore')
                    file_content_for_scan = rtf_to_text(rtf_source_str, errors="ignore")
                    file_encoding = 'utf-8' # Extracted text is effectively UTF-8
                except Exception as e:
                    print(f"Warn: Error extracting text from RTF {item_abs_path}: {e}")
                    continue
            else:
                file_encoding = get_file_encoding(item_abs_path)
                try:
                    # Read with newline='' to preserve original line endings in lines_for_scan
                    with open(item_abs_path, 'r', encoding=file_encoding, errors='surrogateescape', newline='') as f_scan:
                        file_content_for_scan = f_scan.read()
                except Exception as e:
                    print(f"Warn: Error reading text file {item_abs_path} (enc:{file_encoding}): {e}")
                    continue

            if file_content_for_scan is not None:
                lines_for_scan = file_content_for_scan.splitlines(keepends=True)
                if not lines_for_scan and file_content_for_scan: # Handle files with no newlines but content
                    lines_for_scan = [file_content_for_scan]

                for line_idx, line_content in enumerate(lines_for_scan):
                    # For scanning, process line_content similarly to how keys are processed for scan_pattern
                    # `strip_diacritics` does NFD internally.
                    searchable_line_content = unicodedata.normalize('NFC', strip_control_characters(strip_diacritics(line_content)))
                    if (scan_pattern and scan_pattern.search(searchable_line_content)) and \
                       (replace_occurrences(line_content) != line_content): # Pass original line_content
                        tx_id_tuple = (relative_path_str, TransactionType.FILE_CONTENT_LINE.value, line_idx + 1)
                        if tx_id_tuple not in existing_transaction_ids:
                            processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":TransactionType.FILE_CONTENT_LINE.value, "PATH":relative_path_str, "LINE_NUMBER":line_idx+1, "ORIGINAL_LINE_CONTENT":line_content, "ORIGINAL_ENCODING":file_encoding, "IS_RTF":is_rtf, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                            existing_transaction_ids.add(tx_id_tuple)
    return processed_transactions

def load_transactions(json_file_path: Path) -> list[dict[str, Any]] | None:
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    paths_to_try = [json_file_path, backup_path]
    loaded_data = None
    for path_to_try in paths_to_try:
        if path_to_try.exists():
            try:
                with open(path_to_try, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f) # type: ignore
                if isinstance(loaded_data, list):
                    return cast(list[dict[str, Any]], loaded_data)
                else:
                    print(f"Warning: Invalid format in {path_to_try}. Expected a list.")
                    loaded_data = None
            except json.JSONDecodeError as jde:
                print(f"Warning: Failed to decode JSON from {path_to_try}: {jde}")
            except Exception as e:
                print(f"Warning: Failed to load transactions from {path_to_try}: {e}")
    if loaded_data is None:
        print(f"Error: Could not load valid transactions from {json_file_path} or its backup.")
    return None

def save_transactions(transactions: list[dict[str, Any]], json_file_path: Path) -> None:
    if json_file_path.exists():
        try:
            shutil.copy2(json_file_path, json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT))
        except Exception as e:
            print(f"Warning: Could not backup {json_file_path}: {e}")
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=4)
    except Exception as e:
        print(f"Error: Could not save transactions to {json_file_path}: {e}")
        raise

def update_transaction_status_in_list(
    transactions: list[dict[str, Any]], transaction_id: str, new_status: TransactionStatus,
    error_message: str | None = None, proposed_content_after_execution: str | None = None,
    is_retryable_error: bool = False
) -> bool:
    current_time = time.time()
    for tx_item in transactions:
        if tx_item['id'] == transaction_id:
            tx_item['STATUS'] = new_status.value
            tx_item['timestamp_last_attempt'] = current_time
            if error_message:
                tx_item['ERROR_MESSAGE'] = error_message
            elif new_status not in [TransactionStatus.FAILED, TransactionStatus.RETRY_LATER] :
                tx_item.pop('ERROR_MESSAGE', None)

            if tx_item['TYPE'] == TransactionType.FILE_CONTENT_LINE.value and proposed_content_after_execution is not None:
                tx_item['PROPOSED_LINE_CONTENT'] = proposed_content_after_execution

            if new_status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED]:
                tx_item["timestamp_processed"] = current_time

            if new_status == TransactionStatus.RETRY_LATER:
                tx_item['retry_count'] = tx_item.get('retry_count', 0) + 1
            return True
    return False

def _ensure_within_sandbox(path_to_check: Path, sandbox_root: Path, operation_desc: str):
    try:
        resolved_path = path_to_check.resolve(strict=False)
        resolved_root = sandbox_root.resolve(strict=True)
        if resolved_path == resolved_root:
            return
        if not str(resolved_path).startswith(str(resolved_root) + os.sep):
             raise SandboxViolationError(f"Op '{operation_desc}' path '{resolved_path}' outside sandbox '{resolved_root}'.")
    except FileNotFoundError as e:
        raise SandboxViolationError(f"Sandbox root '{sandbox_root}' or path '{path_to_check}' not found for check during '{operation_desc}'. Error: {e}") from e
    except Exception as e:
        raise SandboxViolationError(f"Error during sandbox check ('{path_to_check}', sandbox '{sandbox_root}') for '{operation_desc}'. Error: {e}") from e

def _is_retryable_os_error(e: OSError) -> bool:
    if isinstance(e, PermissionError):
        return True
    if hasattr(e, 'errno') and e.errno in RETRYABLE_OS_ERRORNOS:
        return True
    if os.name == 'nt' and hasattr(e, 'winerror') and e.winerror in [32, 33]: # type: ignore
        return True
    return False

def _execute_rename_transaction(
    tx_item: dict[str, Any], root_dir: Path,
    path_translation_map: dict[str, str], path_cache: dict[str, Path], dry_run: bool
) -> tuple[TransactionStatus, str | None, bool]:
    orig_rel_path = tx_item["PATH"]
    orig_name = tx_item["ORIGINAL_NAME"]
    try:
        current_abs_path = _get_current_absolute_path(orig_rel_path, root_dir, path_translation_map, path_cache)
    except FileNotFoundError:
        return TransactionStatus.SKIPPED, f"Parent for '{orig_rel_path}' not found.", False
    except Exception as e:
        return TransactionStatus.FAILED, f"Error resolving path for '{orig_rel_path}': {e}", False
    if not os.path.lexists(current_abs_path):
        return TransactionStatus.SKIPPED, f"Item '{current_abs_path}' not found by lexists.", False
    new_name = replace_occurrences(orig_name)
    if new_name == orig_name:
        return TransactionStatus.SKIPPED, "Name unchanged by replacement logic.", False
    new_abs_path = current_abs_path.with_name(new_name)
    if not dry_run and orig_name == SELF_TEST_ERROR_FILE_BASENAME:
        return TransactionStatus.FAILED, "Simulated rename error for self-test.", False
    if dry_run:
        path_translation_map[orig_rel_path] = new_name
        path_cache.pop(orig_rel_path, None)
        return TransactionStatus.COMPLETED, "DRY_RUN", False
    try:
        _ensure_within_sandbox(current_abs_path, root_dir, f"rename src '{orig_name}'")
        _ensure_within_sandbox(new_abs_path, root_dir, f"rename dest '{new_name}'")
        if os.path.lexists(new_abs_path):
            return TransactionStatus.SKIPPED, f"Target path '{new_abs_path}' for new name already exists.", False
        Path(current_abs_path).rename(new_abs_path)
        path_translation_map[orig_rel_path] = new_name
        path_cache.pop(orig_rel_path, None)
        path_cache[orig_rel_path] = new_abs_path
        return TransactionStatus.COMPLETED, None, False
    except OSError as e:
        if _is_retryable_os_error(e):
            return TransactionStatus.RETRY_LATER, f"OS error (retryable): {e}", True
        return TransactionStatus.FAILED, f"OS error: {e}", False
    except SandboxViolationError as sve:
        return TransactionStatus.FAILED, f"SandboxViolation: {sve}", False
    except Exception as e:
        return TransactionStatus.FAILED, f"Unexpected rename error: {e}", False

def _execute_content_line_transaction(
    tx_item: dict[str, Any], root_dir: Path,
    path_translation_map: dict[str, str], path_cache: dict[str, Path], dry_run: bool
) -> tuple[TransactionStatus, str | None, bool]:
    orig_rel_path = tx_item["PATH"]
    line_num = tx_item["LINE_NUMBER"]
    orig_line_content = tx_item["ORIGINAL_LINE_CONTENT"]
    encoding = tx_item["ORIGINAL_ENCODING"] or DEFAULT_ENCODING_FALLBACK
    is_rtf = tx_item.get("IS_RTF", False)

    actual_new_line_content = replace_occurrences(orig_line_content)
    tx_item["PROPOSED_LINE_CONTENT"] = actual_new_line_content

    if actual_new_line_content == orig_line_content:
        return TransactionStatus.SKIPPED, "Line content unchanged by replacement logic.", False
    try:
        current_abs_path = _get_current_absolute_path(orig_rel_path, root_dir, path_translation_map, path_cache)
    except FileNotFoundError:
        return TransactionStatus.SKIPPED, f"Parent for '{orig_rel_path}' not found.", False
    except Exception as e:
        return TransactionStatus.FAILED, f"Error resolving path for '{orig_rel_path}': {e}", False
    if current_abs_path.is_symlink():
        return TransactionStatus.SKIPPED, f"'{current_abs_path}' is a symlink; content modification skipped.", False
    if not current_abs_path.is_file():
        return TransactionStatus.SKIPPED, f"'{current_abs_path}' not found or not a file.", False
    if dry_run:
        return TransactionStatus.COMPLETED, "DRY_RUN", False

    if is_rtf:
        return TransactionStatus.SKIPPED, "RTF content modification is skipped to preserve formatting. Match was based on extracted text.", False

    temp_file_path: Path | None = None
    try:
        _ensure_within_sandbox(current_abs_path, root_dir, f"content write for {current_abs_path.name}")
        temp_file_path = current_abs_path.with_name(f"{current_abs_path.name}.{uuid.uuid4()}.tmp")
        line_processed_flag = False
        # Read with newline='' to preserve original line endings
        with open(current_abs_path,'r',encoding=encoding,errors='surrogateescape',newline='') as inf, \
             open(temp_file_path,'w',encoding=encoding,errors='surrogateescape',newline='') as outf:
            current_line_idx = 0
            for current_line_in_file in inf:
                current_line_idx += 1
                if current_line_idx == line_num:
                    line_processed_flag = True
                    # Compare with original line content from transaction (which also had preserved newlines if scan was correct)
                    if current_line_in_file == orig_line_content:
                        outf.write(actual_new_line_content)
                    else:
                        # If content changed since scan, write current line and abort for this file to be safe
                        outf.write(current_line_in_file)
                        # Write rest of file as is
                        for rest_line in inf:
                            outf.write(rest_line)
                        raise RuntimeError(f"Content of line {line_num} in {current_abs_path} has changed since scan. Expected: {repr(orig_line_content)}, Found: {repr(current_line_in_file)}")
                else:
                    outf.write(current_line_in_file)
            if not line_processed_flag and line_num > current_line_idx: # Should not happen if scan was correct
                raise RuntimeError(f"Line number {line_num} is out of bounds for file {current_abs_path} (file has {current_line_idx} lines).")
        
        if line_processed_flag: # Ensure the target line was actually found and processed
            shutil.copymode(current_abs_path, temp_file_path)
            os.replace(temp_file_path, current_abs_path)
            temp_file_path = None # Prevent deletion in finally
            return TransactionStatus.COMPLETED, None, False
        # This case (line_processed_flag is False but no error raised) should be unlikely
        return TransactionStatus.FAILED, "Content update logic error: target line not processed as expected.", False
    except OSError as e:
        if _is_retryable_os_error(e):
            return TransactionStatus.RETRY_LATER, f"OS error (retryable): {e}", True
        return TransactionStatus.FAILED, f"OS error: {e}", False
    except SandboxViolationError as sve:
        return TransactionStatus.FAILED, f"SandboxViolation: {sve}", False
    except RuntimeError as rte: # Catch our specific "content changed" or "line out of bounds"
        return TransactionStatus.FAILED, str(rte), False
    except Exception as e:
        return TransactionStatus.FAILED, f"Unexpected content update error for {current_abs_path}: {e}", False
    finally:
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink(missing_ok=True)
            except OSError: # nosec
                pass # Best effort to clean up

def execute_all_transactions(
    transactions_file_path: Path, root_dir: Path, dry_run: bool, resume: bool,
    global_timeout_minutes: int,
    skip_file_renaming: bool, skip_folder_renaming: bool, skip_content: bool,
    skip_scan: bool
) -> dict[str, int]:
    transactions = load_transactions(transactions_file_path)
    if not transactions:
        return {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}

    stats = {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}
    path_translation_map: dict[str,str] = {}
    path_cache: dict[str,Path] = {}
    abs_r_dir = root_dir

    # Initialize path_translation_map from COMPLETED renames if resuming or skipping scan.
    if resume or skip_scan:
        for tx in transactions:
            if tx.get("STATUS") == TransactionStatus.COMPLETED.value and \
               tx["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
                # For skip_scan, we trust the "COMPLETED" (even if from DRY_RUN) as the plan.
                # For resume, actual completed renames are used.
                # The key is that `replace_occurrences` will give the *target* name.
                path_translation_map[tx["PATH"]] = replace_occurrences(tx["ORIGINAL_NAME"])


    def sort_key(tx):
        type_o={TransactionType.FOLDER_NAME.value:0,TransactionType.FILE_NAME.value:1,TransactionType.FILE_CONTENT_LINE.value:2}
        return (type_o[tx["TYPE"]], tx["PATH"].count('/'), tx["PATH"], tx.get("LINE_NUMBER",0))
    transactions.sort(key=sort_key)

    execution_start_time = time.time()
    max_overall_retry_passes = 500 if global_timeout_minutes == 0 else 20 # Max passes for timed, effectively infinite for timeout=0
    current_overall_retry_attempt = 0
    
    # Initial status reset for relevant transactions if resuming or skipping scan
    if resume or skip_scan: # Apply to both resume and skip_scan
        for tx_item_for_reset in transactions:
            current_tx_status = tx_item_for_reset.get("STATUS")
            # If resuming or skipping scan, reset "DRY_RUN" completed items to PENDING
            if current_tx_status == TransactionStatus.COMPLETED.value and \
               tx_item_for_reset.get("ERROR_MESSAGE") == "DRY_RUN":
                tx_item_for_reset["STATUS"] = TransactionStatus.PENDING.value
                tx_item_for_reset.pop('ERROR_MESSAGE', None)
                tx_item_for_reset.pop('timestamp_processed', None)
                tx_item_for_reset.pop('timestamp_next_retry', None)
                tx_item_for_reset['retry_count'] = 0
            # If resuming, also reset FAILED items to PENDING for a retry attempt
            elif resume and current_tx_status == TransactionStatus.FAILED.value:
                print(f"Resuming FAILED tx as PENDING: {tx_item_for_reset.get('id','N/A')} ({tx_item_for_reset.get('PATH','N/A')})")
                tx_item_for_reset["STATUS"] = TransactionStatus.PENDING.value
                tx_item_for_reset.pop('ERROR_MESSAGE', None)
                tx_item_for_reset.pop('timestamp_processed', None)
                tx_item_for_reset.pop('timestamp_next_retry', None)
                tx_item_for_reset['retry_count'] = 0


    while True:
        processed_in_this_pass = 0
        items_still_requiring_retry = []

        for tx_item in transactions:
            tx_id = tx_item.setdefault("id", str(uuid.uuid4()))
            current_status = TransactionStatus(tx_item.get("STATUS", TransactionStatus.PENDING.value))

            if (skip_folder_renaming and tx_item["TYPE"] == TransactionType.FOLDER_NAME.value) or \
               (skip_file_renaming and tx_item["TYPE"] == TransactionType.FILE_NAME.value) or \
               (skip_content and tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value):
                if current_status not in [TransactionStatus.COMPLETED, TransactionStatus.SKIPPED, TransactionStatus.FAILED]:
                    update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "Skipped by CLI option.")
                    processed_in_this_pass +=1
                continue

            if current_status in [TransactionStatus.COMPLETED, TransactionStatus.SKIPPED, TransactionStatus.FAILED]:
                continue

            if current_status == TransactionStatus.IN_PROGRESS and not resume and current_overall_retry_attempt == 0:
                # If a previous run was interrupted, IN_PROGRESS items should be re-evaluated
                current_status = TransactionStatus.PENDING
            
            if current_status == TransactionStatus.RETRY_LATER:
                if tx_item.get("timestamp_next_retry", 0) > time.time():
                    items_still_requiring_retry.append(tx_item)
                    continue
                else: # Timer expired, try again
                    current_status = TransactionStatus.PENDING
            
            tx_item["STATUS"] = current_status.value # Ensure current_status is reflected in tx_item for this pass

            if current_status == TransactionStatus.PENDING:
                update_transaction_status_in_list(transactions, tx_id, TransactionStatus.IN_PROGRESS)

                new_stat_from_exec: TransactionStatus
                err_msg_from_exec: str | None = None
                final_prop_content_for_log: str | None = None
                is_retryable_error_from_exec = False

                try:
                    if tx_item["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
                        new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = _execute_rename_transaction(tx_item, abs_r_dir, path_translation_map, path_cache, dry_run)
                    elif tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
                        new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = _execute_content_line_transaction(tx_item, abs_r_dir, path_translation_map, path_cache, dry_run)
                        final_prop_content_for_log = tx_item.get("PROPOSED_LINE_CONTENT")
                    else:
                        new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = TransactionStatus.FAILED, f"Unknown type: {tx_item['TYPE']}", False
                except Exception as e_outer:
                    new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = TransactionStatus.FAILED, f"Outer execution error: {e_outer}", False
                    print(f"CRITICAL outer error processing tx {tx_id}: {e_outer}")

                if new_stat_from_exec == TransactionStatus.RETRY_LATER and is_retryable_error_from_exec:
                    retry_count = tx_item.get('retry_count', 0)
                    base_delay_seconds = 5
                    max_backoff_seconds = 300 # 5 minutes
                    backoff_seconds = min( (2 ** retry_count) * base_delay_seconds, max_backoff_seconds)
                    tx_item['timestamp_next_retry'] = time.time() + backoff_seconds
                    print(f"Transaction {tx_id} ({tx_item['PATH']}) set to RETRY_LATER. Next attempt in ~{backoff_seconds:.0f}s (Attempt {retry_count + 1}). Error: {err_msg_from_exec}")
                    items_still_requiring_retry.append(tx_item)

                update_transaction_status_in_list(transactions, tx_id, new_stat_from_exec, err_msg_from_exec, final_prop_content_for_log, is_retryable_error_from_exec)
                save_transactions(transactions, transactions_file_path)
                processed_in_this_pass += 1

        current_overall_retry_attempt += 1

        if not items_still_requiring_retry: # All items processed or no retries needed
            break

        timed_out = False
        if global_timeout_minutes > 0 and (time.time() - execution_start_time) / 60 >= global_timeout_minutes:
            print(f"Global execution timeout of {global_timeout_minutes} minutes reached.")
            timed_out = True

        max_retries_hit_for_timed_run = False
        if global_timeout_minutes != 0 and current_overall_retry_attempt >= max_overall_retry_passes:
            print(f"Warning: Max retry passes ({max_overall_retry_passes}) reached for timed execution.")
            max_retries_hit_for_timed_run = True
        
        # For indefinite timeout, we don't cap by max_overall_retry_passes in the same way,
        # but we might log if it's taking too many passes.
        if global_timeout_minutes == 0 and current_overall_retry_attempt >= max_overall_retry_passes:
             print(f"Warning: Indefinite timeout, but max retry passes ({max_overall_retry_passes}) reached. This may indicate a persistent issue or very long backoffs.")


        if timed_out or max_retries_hit_for_timed_run: # Only for timed runs
            failure_reason = "Global timeout reached." if timed_out else "Max retry passes reached for timed execution."
            for tx_item_failed_retry in items_still_requiring_retry:
                if tx_item_failed_retry["STATUS"] == TransactionStatus.RETRY_LATER.value: # Only fail those still in RETRY_LATER
                    update_transaction_status_in_list(transactions, tx_item_failed_retry["id"], TransactionStatus.FAILED, failure_reason)
            save_transactions(transactions, transactions_file_path)
            break # Exit retry loop

        if items_still_requiring_retry: # If still items to retry (and not timed out for timed runs)
            next_due_retry_timestamp = min(itx.get("timestamp_next_retry", float('inf')) for itx in items_still_requiring_retry)
            sleep_duration = max(0.1, next_due_retry_timestamp - time.time())

            if global_timeout_minutes > 0: # If timed, ensure sleep doesn't exceed remaining budget
                remaining_time_budget = (execution_start_time + global_timeout_minutes * 60) - time.time()
                if remaining_time_budget <= 0: # Double check timeout before sleep
                    print(f"Global execution timeout of {global_timeout_minutes} minutes reached (checked before sleep).")
                    for tx_item_timeout_retry in items_still_requiring_retry:
                         if tx_item_timeout_retry["STATUS"] == TransactionStatus.RETRY_LATER.value:
                            update_transaction_status_in_list(transactions, tx_item_timeout_retry["id"], TransactionStatus.FAILED, "Global timeout reached during retry phase.")
                    save_transactions(transactions, transactions_file_path)
                    break # Exit retry loop
                sleep_duration = min(sleep_duration, remaining_time_budget, 60.0) # Cap sleep at 60s or remaining budget
            else: # Indefinite timeout, cap sleep at 60s for responsiveness
                sleep_duration = min(sleep_duration, 60.0)

            if sleep_duration > 0.05 : # Avoid spamming logs for very short sleeps
                 print(f"Retry Pass {current_overall_retry_attempt} complete. {len(items_still_requiring_retry)} items pending retry. Next check in ~{sleep_duration:.1f}s.")
                 time.sleep(sleep_duration)
            else: # Minimal sleep if next retry is almost immediate
                time.sleep(0.05) 
        elif not processed_in_this_pass: # No items processed, no items to retry
            break

    # Final count of statuses
    stats = {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}
    for t in transactions:
        status_key = t.get("STATUS", TransactionStatus.PENDING.value).lower()
        stats[status_key] = stats.get(status_key, 0) + 1
    return stats

