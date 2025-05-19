#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Fixed NameError: 'max_overall_retry_attempts' to 'max_overall_retry_passes'.
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
from typing import List, Tuple, Optional, Dict, Any, Iterator, cast, Callable, Union, Set
from enum import Enum
import chardet
import time
import pathspec
import errno
from striprtf.striprtf import rtf_to_text
from isbinary import is_binary_file

from replace_logic import replace_occurrences, get_scan_pattern, get_raw_stripped_keys

class SandboxViolationError(Exception): pass
class MockableRetriableError(OSError): pass

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

def get_file_encoding(file_path: Path, sample_size: int = 10240) -> Optional[str]:
    if file_path.suffix.lower() == '.rtf':
        return 'latin-1'
    try:
        with open(file_path, 'rb') as f: raw_data = f.read(sample_size)
        if not raw_data: return DEFAULT_ENCODING_FALLBACK
        detected = chardet.detect(raw_data)
        encoding: Optional[str] = detected.get('encoding')
        confidence: float = detected.get('confidence', 0.0)
        if encoding and confidence and confidence > 0.7:
            norm_enc = encoding.lower()
            if norm_enc == 'ascii': return 'ascii'
            if 'utf-8' in norm_enc or 'utf8' in norm_enc: return 'utf-8'
            try: b"test".decode(encoding); return encoding
            except (LookupError, UnicodeDecodeError): pass
        try: raw_data.decode('utf-8'); return 'utf-8'
        except UnicodeDecodeError:
            if encoding:
                try: raw_data.decode(encoding); return encoding
                except (UnicodeDecodeError, LookupError): pass
            return DEFAULT_ENCODING_FALLBACK
    except Exception: return DEFAULT_ENCODING_FALLBACK

def load_ignore_patterns(ignore_file_path: Path) -> Optional[pathspec.PathSpec]:
    if not ignore_file_path.is_file(): return None
    try:
        with open(ignore_file_path, 'r', encoding='utf-8', errors='ignore') as f: patterns = f.readlines()
        valid_patterns = [p for p in (line.strip() for line in patterns) if p and not p.startswith('#')]
        return pathspec.PathSpec.from_lines('gitwildmatch', valid_patterns) if valid_patterns else None
    except Exception as e: print(f"Warning: Could not load ignore file {ignore_file_path}: {e}"); return None

def _walk_for_scan(
    root_dir: Path, excluded_dirs_abs: List[Path],
    ignore_symlinks: bool, ignore_spec: Optional[pathspec.PathSpec]
) -> Iterator[Path]:
    for item_path in root_dir.rglob("*"):
        item_abs_path = item_path.resolve(strict=False)
        if ignore_symlinks and item_abs_path.is_symlink(): continue
        is_excluded_by_dir_arg = any(item_abs_path == ex_dir or \
                                   (ex_dir.is_dir() and str(item_abs_path).startswith(str(ex_dir) + os.sep))
                                   for ex_dir in excluded_dirs_abs)
        if is_excluded_by_dir_arg: continue
        if ignore_spec:
            try:
                path_rel_to_root_for_spec = item_abs_path.relative_to(root_dir)
                if ignore_spec.match_file(str(path_rel_to_root_for_spec)) or \
                   (item_abs_path.is_dir() and ignore_spec.match_file(str(path_rel_to_root_for_spec) + '/')):
                    continue
            except ValueError: pass
            except Exception as e:
                print(f"Warning: Error during ignore_spec matching for {item_abs_path} relative to {root_dir}: {e}")
        yield item_abs_path

def _get_current_absolute_path(
    original_relative_path_str: str, root_dir: Path,
    path_translation_map: Dict[str, str], cache: Dict[str, Path]
) -> Path:
    if original_relative_path_str in cache: return cache[original_relative_path_str]
    if original_relative_path_str == ".": cache["."] = root_dir; return root_dir
    original_path_obj = Path(original_relative_path_str)
    parent_rel_str = "." if original_path_obj.parent == Path('.') else str(original_path_obj.parent)
    current_parent_abs_path = _get_current_absolute_path(parent_rel_str, root_dir, path_translation_map, cache)
    current_item_name = path_translation_map.get(original_relative_path_str, original_path_obj.name)
    current_abs_path = (current_parent_abs_path / current_item_name).resolve(strict=False)
    cache[original_relative_path_str] = current_abs_path
    return current_abs_path

def scan_directory_for_occurrences(
    root_dir: Path, excluded_dirs: List[str], excluded_files: List[str],
    file_extensions: Optional[List[str]], ignore_symlinks: bool,
    ignore_spec: Optional[pathspec.PathSpec],
    resume_from_transactions: Optional[List[Dict[str, Any]]] = None,
    paths_to_force_rescan: Optional[Set[str]] = None,
    skip_file_renaming: bool = False, skip_folder_renaming: bool = False, skip_content: bool = False
) -> List[Dict[str, Any]]:
    processed_transactions: List[Dict[str, Any]] = []
    existing_transaction_ids: Set[Tuple[str, str, int]] = set()
    paths_to_force_rescan = paths_to_force_rescan or set()
    abs_root_dir = root_dir

    scan_pattern = get_scan_pattern()
    raw_keys_for_binary_search = get_raw_stripped_keys()

    if resume_from_transactions is not None:
        processed_transactions = list(resume_from_transactions)
        for tx in resume_from_transactions:
            tx_rel_path = tx.get("PATH")
            if tx_rel_path in paths_to_force_rescan and tx.get("TYPE") == TransactionType.FILE_CONTENT_LINE.value: continue
            tx_type, tx_line = tx.get("TYPE"), tx.get("LINE_NUMBER", 0)
            if tx_type and tx_rel_path: existing_transaction_ids.add((tx_rel_path, tx_type, tx_line))

    resolved_abs_excluded_dirs = []
    for d_str in excluded_dirs:
        try: resolved_abs_excluded_dirs.append(abs_root_dir.joinpath(d_str).resolve(strict=False))
        except Exception: resolved_abs_excluded_dirs.append(abs_root_dir.joinpath(d_str).absolute())

    excluded_basenames = {Path(f).name for f in excluded_files if Path(f).name == f and not os.path.sep in f and not ('/' in f or '\\' in f)}
    excluded_relative_paths_set = {f.replace("\\", "/") for f in excluded_files if os.path.sep in f or '/' in f or '\\' in f}

    normalized_extensions = {ext.lower() for ext in file_extensions} if file_extensions else None
    binary_log_path = abs_root_dir / BINARY_MATCHES_LOG_FILE

    item_iterator = _walk_for_scan(abs_root_dir, resolved_abs_excluded_dirs, ignore_symlinks, ignore_spec)
    first_item = next(item_iterator, None)
    if first_item is None: return []
    def combined_iterator() -> Iterator[Path]:
        if first_item: yield first_item
        yield from item_iterator

    for item_abs_path in combined_iterator():
        try: relative_path_str = str(item_abs_path.relative_to(abs_root_dir)).replace("\\", "/")
        except ValueError: continue
        if item_abs_path.name in excluded_basenames or relative_path_str in excluded_relative_paths_set: continue

        original_name = item_abs_path.name
        if (scan_pattern and scan_pattern.search(original_name)) and \
           (replace_occurrences(original_name) != original_name):
            tx_type: Optional[str] = None
            if item_abs_path.is_dir() and not item_abs_path.is_symlink():
                if not skip_folder_renaming: tx_type = TransactionType.FOLDER_NAME.value
            elif item_abs_path.is_file() or item_abs_path.is_symlink():
                if not skip_file_renaming: tx_type = TransactionType.FILE_NAME.value
            if tx_type:
                tx_id_tuple = (relative_path_str, tx_type, 0)
                if tx_id_tuple not in existing_transaction_ids:
                    processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":tx_type, "PATH":relative_path_str, "ORIGINAL_NAME":original_name, "LINE_NUMBER":0, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                    existing_transaction_ids.add(tx_id_tuple)

        if not skip_content and item_abs_path.is_file() and not item_abs_path.is_symlink():
            is_rtf = item_abs_path.suffix.lower() == '.rtf'
            try:
                is_bin = is_binary_file(str(item_abs_path))
            except FileNotFoundError: continue
            except Exception as e_isbin:
                print(f"Warning: Could not determine if {item_abs_path} is binary: {e_isbin}. Skipping content scan.")
                continue

            if is_bin and not is_rtf:
                if raw_keys_for_binary_search:
                    try:
                        with open(item_abs_path, 'rb') as bf: content_bytes = bf.read()
                        for key_str in raw_keys_for_binary_search:
                            try: key_bytes = key_str.encode('utf-8')
                            except UnicodeEncodeError: continue
                            offset = 0
                            while True:
                                idx = content_bytes.find(key_bytes, offset)
                                if idx == -1: break
                                with open(binary_log_path, 'a', encoding='utf-8') as log_f:
                                    log_f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - MATCH: File: {relative_path_str}, Key: '{key_str}', Offset: {idx}\n")
                                offset = idx + len(key_bytes)
                    except Exception as e: print(f"Warn: Error processing binary {item_abs_path} for logging: {e}")
                continue

            if normalized_extensions and item_abs_path.suffix.lower() not in normalized_extensions and not is_rtf:
                 continue

            file_content_for_scan: Optional[str] = None
            file_encoding = DEFAULT_ENCODING_FALLBACK

            if is_rtf:
                try:
                    rtf_source_bytes = item_abs_path.read_bytes()
                    rtf_source_str = ""
                    for enc_try in ['latin-1', 'cp1252', 'utf-8']:
                        try: rtf_source_str = rtf_source_bytes.decode(enc_try); break
                        except UnicodeDecodeError: pass
                    if not rtf_source_str: rtf_source_str = rtf_source_bytes.decode('utf-8', errors='ignore')
                    file_content_for_scan = rtf_to_text(rtf_source_str, errors="ignore")
                    file_encoding = 'utf-8'
                except Exception as e: print(f"Warn: Error extracting text from RTF {item_abs_path}: {e}"); continue
            else:
                file_encoding = get_file_encoding(item_abs_path)
                try:
                    file_content_for_scan = item_abs_path.read_text(encoding=file_encoding, errors='surrogateescape')
                except Exception as e: print(f"Warn: Error reading text file {item_abs_path} (enc:{file_encoding}): {e}"); continue

            if file_content_for_scan is not None:
                lines_for_scan = file_content_for_scan.splitlines(keepends=True)
                if not lines_for_scan and file_content_for_scan:
                    lines_for_scan = [file_content_for_scan]

                for line_idx, line_content in enumerate(lines_for_scan):
                    if (scan_pattern and scan_pattern.search(line_content)) and \
                       (replace_occurrences(line_content) != line_content):
                        tx_id_tuple = (relative_path_str, TransactionType.FILE_CONTENT_LINE.value, line_idx + 1)
                        if tx_id_tuple not in existing_transaction_ids:
                            processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":TransactionType.FILE_CONTENT_LINE.value, "PATH":relative_path_str, "LINE_NUMBER":line_idx+1, "ORIGINAL_LINE_CONTENT":line_content, "ORIGINAL_ENCODING":file_encoding, "IS_RTF":is_rtf, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                            existing_transaction_ids.add(tx_id_tuple)
    return processed_transactions

def load_transactions(json_file_path: Path) -> Optional[List[Dict[str, Any]]]:
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    paths_to_try = [json_file_path, backup_path]
    loaded_data = None
    for path_to_try in paths_to_try:
        if path_to_try.exists():
            try:
                with open(path_to_try, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                if isinstance(loaded_data, list):
                    return cast(List[Dict[str, Any]], loaded_data)
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

def save_transactions(transactions: List[Dict[str, Any]], json_file_path: Path) -> None:
    if json_file_path.exists():
        try: shutil.copy2(json_file_path, json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT))
        except Exception as e: print(f"Warning: Could not backup {json_file_path}: {e}")
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f: json.dump(transactions, f, indent=4)
    except Exception as e: print(f"Error: Could not save transactions to {json_file_path}: {e}"); raise

def update_transaction_status_in_list(
    transactions: List[Dict[str, Any]], transaction_id: str, new_status: TransactionStatus,
    error_message: Optional[str] = None, proposed_content_after_execution: Optional[str] = None,
    is_retryable_error: bool = False
) -> bool:
    current_time = time.time()
    for tx_item in transactions:
        if tx_item['id'] == transaction_id:
            tx_item['STATUS'] = new_status.value
            tx_item['timestamp_last_attempt'] = current_time
            if error_message: tx_item['ERROR_MESSAGE'] = error_message
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
        if resolved_path == resolved_root: return
        if not str(resolved_path).startswith(str(resolved_root) + os.sep):
             raise SandboxViolationError(f"Op '{operation_desc}' path '{resolved_path}' outside sandbox '{resolved_root}'.")
    except FileNotFoundError as e: raise SandboxViolationError(f"Sandbox root '{sandbox_root}' or path '{path_to_check}' not found for check during '{operation_desc}'. Error: {e}") from e
    except Exception as e: raise SandboxViolationError(f"Error during sandbox check ('{path_to_check}', sandbox '{sandbox_root}') for '{operation_desc}'. Error: {e}") from e

def _is_retryable_os_error(e: OSError) -> bool:
    if isinstance(e, PermissionError): return True
    if hasattr(e, 'errno') and e.errno in RETRYABLE_OS_ERRORNOS: return True
    if os.name == 'nt' and hasattr(e, 'winerror') and e.winerror in [32, 33]: return True
    return False

def _execute_rename_transaction(
    tx_item: Dict[str, Any], root_dir: Path,
    path_translation_map: Dict[str, str], path_cache: Dict[str, Path], dry_run: bool
) -> Tuple[TransactionStatus, Optional[str], bool]:
    orig_rel_path = tx_item["PATH"]; orig_name = tx_item["ORIGINAL_NAME"]
    try: current_abs_path = _get_current_absolute_path(orig_rel_path, root_dir, path_translation_map, path_cache)
    except FileNotFoundError: return TransactionStatus.SKIPPED, f"Parent for '{orig_rel_path}' not found.", False
    except Exception as e: return TransactionStatus.FAILED, f"Error resolving path for '{orig_rel_path}': {e}", False
    if not os.path.lexists(current_abs_path): return TransactionStatus.SKIPPED, f"Item '{current_abs_path}' not found by lexists.", False
    new_name = replace_occurrences(orig_name)
    if new_name == orig_name: return TransactionStatus.SKIPPED, "Name unchanged by replacement logic.", False
    new_abs_path = current_abs_path.with_name(new_name)
    if not dry_run and orig_name == SELF_TEST_ERROR_FILE_BASENAME: return TransactionStatus.FAILED, "Simulated rename error for self-test.", False
    if dry_run:
        path_translation_map[orig_rel_path] = new_name; path_cache.pop(orig_rel_path, None)
        return TransactionStatus.COMPLETED, "DRY_RUN", False
    try:
        _ensure_within_sandbox(current_abs_path, root_dir, f"rename src '{orig_name}'")
        _ensure_within_sandbox(new_abs_path, root_dir, f"rename dest '{new_name}'")
        if os.path.lexists(new_abs_path): return TransactionStatus.SKIPPED, f"Target path '{new_abs_path}' for new name already exists.", False
        os.rename(current_abs_path, new_abs_path)
        path_translation_map[orig_rel_path] = new_name; path_cache.pop(orig_rel_path, None)
        path_cache[orig_rel_path] = new_abs_path
        return TransactionStatus.COMPLETED, None, False
    except OSError as e:
        if _is_retryable_os_error(e): return TransactionStatus.RETRY_LATER, f"OS error (retryable): {e}", True
        return TransactionStatus.FAILED, f"OS error: {e}", False
    except SandboxViolationError as sve: return TransactionStatus.FAILED, f"SandboxViolation: {sve}", False
    except Exception as e: return TransactionStatus.FAILED, f"Unexpected rename error: {e}", False

def _execute_content_line_transaction(
    tx_item: Dict[str, Any], root_dir: Path,
    path_translation_map: Dict[str, str], path_cache: Dict[str, Path], dry_run: bool
) -> Tuple[TransactionStatus, Optional[str], bool]:
    orig_rel_path = tx_item["PATH"]; line_num = tx_item["LINE_NUMBER"]
    orig_line_content = tx_item["ORIGINAL_LINE_CONTENT"]; encoding = tx_item["ORIGINAL_ENCODING"] or DEFAULT_ENCODING_FALLBACK
    is_rtf = tx_item.get("IS_RTF", False)

    actual_new_line_content = replace_occurrences(orig_line_content)
    tx_item["PROPOSED_LINE_CONTENT"] = actual_new_line_content

    if actual_new_line_content == orig_line_content: return TransactionStatus.SKIPPED, "Line content unchanged by replacement logic.", False
    try: current_abs_path = _get_current_absolute_path(orig_rel_path, root_dir, path_translation_map, path_cache)
    except FileNotFoundError: return TransactionStatus.SKIPPED, f"Parent for '{orig_rel_path}' not found.", False
    except Exception as e: return TransactionStatus.FAILED, f"Error resolving path for '{orig_rel_path}': {e}", False
    if current_abs_path.is_symlink(): return TransactionStatus.SKIPPED, f"'{current_abs_path}' is a symlink; content modification skipped.", False
    if not current_abs_path.is_file(): return TransactionStatus.SKIPPED, f"'{current_abs_path}' not found or not a file.", False
    if dry_run: return TransactionStatus.COMPLETED, "DRY_RUN", False

    if is_rtf:
        return TransactionStatus.SKIPPED, "RTF content modification is skipped to preserve formatting. Match was based on extracted text.", False

    temp_file_path: Optional[Path] = None
    try:
        _ensure_within_sandbox(current_abs_path, root_dir, f"content write for {current_abs_path.name}")
        temp_file_path = current_abs_path.with_name(f"{current_abs_path.name}.{uuid.uuid4()}.tmp")
        line_processed_flag = False
        with open(current_abs_path,'r',encoding=encoding,errors='surrogateescape',newline=None) as inf, \
             open(temp_file_path,'w',encoding=encoding,errors='surrogateescape',newline='') as outf:
            current_line_idx = 0
            for current_line_in_file in inf:
                current_line_idx += 1
                if current_line_idx == line_num:
                    line_processed_flag = True
                    if current_line_in_file == orig_line_content:
                        outf.write(actual_new_line_content)
                    else:
                        outf.write(current_line_in_file)
                        for rest_line in inf: outf.write(rest_line)
                        raise RuntimeError(f"Content of line {line_num} in {current_abs_path} has changed since scan. Expected: {repr(orig_line_content)}, Found: {repr(current_line_in_file)}")
                else:
                    outf.write(current_line_in_file)
            if not line_processed_flag and line_num > current_line_idx:
                raise RuntimeError(f"Line number {line_num} is out of bounds for file {current_abs_path} (file has {current_line_idx} lines).")
        if line_processed_flag:
            shutil.copymode(current_abs_path, temp_file_path); os.replace(temp_file_path, current_abs_path)
            temp_file_path = None
            return TransactionStatus.COMPLETED, None, False
        return TransactionStatus.FAILED, "Content update logic error: target line not processed as expected.", False
    except OSError as e:
        if _is_retryable_os_error(e): return TransactionStatus.RETRY_LATER, f"OS error (retryable): {e}", True
        return TransactionStatus.FAILED, f"OS error: {e}", False
    except SandboxViolationError as sve: return TransactionStatus.FAILED, f"SandboxViolation: {sve}", False
    except RuntimeError as rte: return TransactionStatus.FAILED, str(rte), False
    except Exception as e: return TransactionStatus.FAILED, f"Unexpected content update error for {current_abs_path}: {e}", False
    finally:
        if temp_file_path and temp_file_path.exists():
            try: temp_file_path.unlink(missing_ok=True)
            except OSError: pass

def execute_all_transactions(
    transactions_file_path: Path, root_dir: Path, dry_run: bool, resume: bool,
    global_timeout_minutes: int,
    skip_file_renaming: bool, skip_folder_renaming: bool, skip_content: bool,
    skip_scan: bool
) -> Dict[str, int]:
    transactions = load_transactions(transactions_file_path)
    if not transactions: return {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}

    stats = {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}
    path_translation_map: Dict[str,str] = {}; path_cache: Dict[str,Path] = {}
    abs_r_dir = root_dir

    if resume:
        for tx in transactions:
            if tx.get("STATUS") == TransactionStatus.COMPLETED.value and \
               tx["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value] and \
               tx.get("ERROR_MESSAGE") != "DRY_RUN":
                path_translation_map[tx["PATH"]] = replace_occurrences(tx["ORIGINAL_NAME"])

    def sort_key(tx): type_o={TransactionType.FOLDER_NAME.value:0,TransactionType.FILE_NAME.value:1,TransactionType.FILE_CONTENT_LINE.value:2}; return (type_o[tx["TYPE"]], tx["PATH"].count('/'), tx["PATH"], tx.get("LINE_NUMBER",0))
    transactions.sort(key=sort_key)

    execution_start_time = time.time()
    max_overall_retry_passes = 500 if global_timeout_minutes == 0 else 20
    current_overall_retry_attempt = 0

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
                current_status = TransactionStatus.PENDING

            if current_status == TransactionStatus.RETRY_LATER:
                if tx_item.get("timestamp_next_retry", 0) > time.time():
                    items_still_requiring_retry.append(tx_item)
                    continue
                else:
                    current_status = TransactionStatus.PENDING

            if resume and tx_item.get("STATUS") == TransactionStatus.FAILED.value and current_overall_retry_attempt == 0 :
                print(f"Resuming FAILED tx as PENDING: {tx_id} ({tx_item.get('PATH','N/A')})")
                current_status = TransactionStatus.PENDING

            tx_item["STATUS"] = current_status.value

            if skip_scan and not resume and current_status == TransactionStatus.COMPLETED and tx_item.get("ERROR_MESSAGE") == "DRY_RUN":
                current_status = TransactionStatus.PENDING
                tx_item["STATUS"] = TransactionStatus.PENDING.value
                tx_item.pop('ERROR_MESSAGE', None)
                tx_item.pop('timestamp_processed', None)

            if current_status == TransactionStatus.PENDING:
                update_transaction_status_in_list(transactions, tx_id, TransactionStatus.IN_PROGRESS)

                new_stat_from_exec: TransactionStatus; err_msg_from_exec: Optional[str] = None;
                final_prop_content_for_log: Optional[str] = None
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
                    max_backoff_seconds = 300
                    backoff_seconds = min( (2 ** retry_count) * base_delay_seconds, max_backoff_seconds)
                    tx_item['timestamp_next_retry'] = time.time() + backoff_seconds
                    print(f"Transaction {tx_id} ({tx_item['PATH']}) set to RETRY_LATER. Next attempt in ~{backoff_seconds:.0f}s (Attempt {retry_count + 1}). Error: {err_msg_from_exec}")
                    items_still_requiring_retry.append(tx_item)

                update_transaction_status_in_list(transactions, tx_id, new_stat_from_exec, err_msg_from_exec, final_prop_content_for_log, is_retryable_error_from_exec)
                save_transactions(transactions, transactions_file_path)
                processed_in_this_pass += 1

        current_overall_retry_attempt += 1

        if not items_still_requiring_retry:
            break

        timed_out = False
        if global_timeout_minutes > 0 and (time.time() - execution_start_time) / 60 >= global_timeout_minutes:
            print(f"Global execution timeout of {global_timeout_minutes} minutes reached.")
            timed_out = True

        max_retries_hit_for_timed_run = False
        if global_timeout_minutes != 0 and current_overall_retry_attempt >= max_overall_retry_passes:
            print(f"Warning: Max retry passes ({max_overall_retry_passes}) reached for timed execution.")
            max_retries_hit_for_timed_run = True

        if global_timeout_minutes == 0 and current_overall_retry_attempt >= max_overall_retry_passes:
             print(f"Warning: Indefinite timeout, but max retry passes ({max_overall_retry_passes}) reached. This may indicate a persistent issue or very long backoffs.")


        if timed_out or max_retries_hit_for_timed_run:
            failure_reason = "Global timeout reached." if timed_out else "Max retry passes reached for timed execution."
            for tx_item_failed_retry in items_still_requiring_retry:
                if tx_item_failed_retry["STATUS"] == TransactionStatus.RETRY_LATER.value:
                    update_transaction_status_in_list(transactions, tx_item_failed_retry["id"], TransactionStatus.FAILED, failure_reason)
            save_transactions(transactions, transactions_file_path)
            break

        if items_still_requiring_retry:
            next_due_retry_timestamp = min(itx.get("timestamp_next_retry", float('inf')) for itx in items_still_requiring_retry)
            sleep_duration = max(0.1, next_due_retry_timestamp - time.time())

            if global_timeout_minutes > 0:
                remaining_time_budget = (execution_start_time + global_timeout_minutes * 60) - time.time()
                if remaining_time_budget <= 0:
                    print(f"Global execution timeout of {global_timeout_minutes} minutes reached (checked before sleep).")
                    for tx_item_timeout_retry in items_still_requiring_retry:
                         update_transaction_status_in_list(transactions, tx_item_timeout_retry["id"], TransactionStatus.FAILED, "Global timeout reached during retry phase.")
                    save_transactions(transactions, transactions_file_path)
                    break
                sleep_duration = min(sleep_duration, remaining_time_budget, 60.0)
            else:
                sleep_duration = min(sleep_duration, 60.0)

            if sleep_duration > 0.05 :
                 print(f"Retry Pass {current_overall_retry_attempt} complete. {len(items_still_requiring_retry)} items pending retry. Next check in ~{sleep_duration:.1f}s.")
                 time.sleep(sleep_duration)
            else:
                time.sleep(0.05)
        elif not processed_in_this_pass:
            break

    stats = {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}
    for t in transactions:
        status_key = t.get("STATUS", TransactionStatus.PENDING.value).lower()
        stats[status_key] = stats.get(status_key, 0) + 1
    return stats
