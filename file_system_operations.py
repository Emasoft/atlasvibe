#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `get_file_encoding`:
#   - If chardet provides an encoding and it can decode the sample, use it, even if confidence is not very high (e.g., > 0.3).
#   - This aims to better handle encodings like cp1252 that chardet might detect with lower confidence than UTF-8 but are correct.
#   - Refined logic:
#     1. Handle RTF.
#     2. Read sample. If empty, default.
#     3. Try UTF-8 first. If decodes sample, use it.
#     4. Else, use chardet. If chardet's encoding decodes sample, use it (after normalizing common aliases).
#     5. Else, try cp1252 as a fallback.
#     6. Else, use DEFAULT_ENCODING_FALLBACK.
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
# - Fixed Ruff linting errors (E701).
# - `get_file_encoding`: Revised logic to prioritize chardet for common single-byte encodings
#   before trying UTF-8, then other chardet suggestions, then cp1252 fallback.
# - `_execute_content_line_transaction`: Added strict encoding check. If original line was strictly
#   encodable but the new line (after replacement) is not, the transaction is marked FAILED.
#   Otherwise, proceeds with surrogateescape for writing.
# - `get_file_encoding`: Further refined logic. Prioritize chardet's guess for common single-byte
#   encodings if it decodes the sample. Then try UTF-8. Then try other chardet guesses.
#   Then try cp1252 as a general fallback. This aims to improve cp1252 detection.
# - `get_file_encoding`: Corrected F821 Undefined name error by using the correct variable name `common_single_byte_western_encodings`.
# - `_execute_content_line_transaction`: Implemented strict byte-for-byte verification after writing to a temporary file.
#   The modified file's bytes must exactly match the expected bytes (original file with only the target line surgically replaced and re-encoded).
#   If not, the transaction fails, and the original file is preserved.
# - Fixed Ruff E701 linting errors in `_execute_content_line_transaction` by moving `unlink` calls to new lines.
# - `get_file_encoding`: Revised logic again.
#   1. RTF & Empty file checks.
#   2. Chardet. If it suggests a common Western encoding AND it decodes the sample, use it.
#   3. Else, try UTF-8. If it decodes, use it.
#   4. Else, if chardet had another (non-Western, non-UTF-8) suggestion AND it decodes, use it.
#   5. Else, try cp1252 as a general fallback if not already tried and failed.
#   6. Default to DEFAULT_ENCODING_FALLBACK.
# - `get_file_encoding`: Final refined logic:
#   1. RTF & Empty file checks.
#   2. Chardet. If suggestion exists:
#      a. Normalize aliases (cp1252, latin1).
#      b. Try decoding with this normalized chardet suggestion. If success, return it.
#   3. If chardet failed or no suggestion: Try UTF-8. If success, return it.
#   4. If still no encoding: Try cp1252. If success, return it.
#   5. If still no encoding: Try latin1. If success, return it.
#   6. Fallback to DEFAULT_ENCODING_FALLBACK.
# - Modified functions to accept an optional logger argument.
# - Replaced `print` statements for warnings/errors with logger calls.
# - `get_file_encoding`: Refined logic to prioritize `cp1252` over `latin1` if both can decode a sample when `latin1` is suggested by chardet.
# - `execute_all_transactions`: Corrected logic for `path_translation_map` initialization in `skip_scan` (non-resume) mode. It should start empty.
# - `get_file_encoding`: Changed internal decode attempts to use `errors='surrogateescape'` to align with how files are actually read for processing.
# - `scan_directory_for_occurrences`: Added try-except OSError around item property checks (is_dir, is_file, is_symlink) to handle stat errors gracefully.
# - `execute_all_transactions`: Made "TYPE" key access safe using .get() when populating path_translation_map and in sort_key.
# - Added direct print to stderr in `execute_all_transactions` before dispatching a transaction.
# - Added direct print to stderr at the entry of `_execute_content_line_transaction`.
# - Added diagnostic print at the start of the main loop in `execute_all_transactions` to show each transaction being iterated.
# - `execute_all_transactions`: Changed `path_translation_map` pre-population to only occur if `resume=True`.
#   For `skip_scan` without `resume`, the map starts empty.
# - `_execute_rename_transaction`: Added more diagnostic prints and a hard check after `Path.rename()` to verify on-disk state.
# - `_execute_rename_transaction`: Changed on-disk verification after rename to use `os.path.exists(str(path))` to align with test assertions.
# - `_execute_content_line_transaction`: Modified to use original path for `current_abs_path` when `dry_run` is True.
# - Converted direct `print(..., file=sys.stderr)` calls in `execute_all_transactions`, `_execute_rename_transaction`,
#   and `_execute_content_line_transaction` to use `_log_fs_op_message(logging.DEBUG, ...)` for better log level control.
# - Added `interactive_mode` parameter to `execute_all_transactions`.
# - Implemented interactive prompting before each transaction if `interactive_mode` is True.
# - Added ANSI color codes for interactive mode display.
# - Helper function `_get_user_interactive_choice` to handle user input.
# - Context display for content transactions in interactive mode.
# - Enhanced `_get_user_interactive_choice` to highlight all occurrences of matched key strings in the original name/line.
# - Added `_highlight_string` helper function for coloring matched keys.
# - Removed unused `current_overall_retry_attempt` from `execute_all_transactions` as the complex retry loop was simplified for interactive mode.
# - Reinstated and enhanced the main retry loop in `execute_all_transactions` for robust automated retries,
#   respecting timeouts and max passes, with exponential backoff for `RETRY_LATER` items.
#   This works alongside interactive mode.
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
from typing import Any, cast # Keep Any if specifically needed for dynamic parts
import collections.abc # For Iterator, Callable
from enum import Enum
import chardet
import unicodedata # For NFC normalization
import time
import pathspec
import errno
from striprtf.striprtf import rtf_to_text
from isbinary import is_binary_file
import logging
import sys # For direct stderr prints
import re # For highlighting in interactive mode

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

# ANSI escape codes for interactive mode
GREEN_FG = "\033[32m"
YELLOW_FG = "\033[33m"
BLUE_FG = "\033[94m"
MAGENTA_FG = "\033[35m"
CYAN_FG = "\033[36m"
RED_FG = "\033[31m"
DIM_STYLE = "\033[2m"
BOLD_STYLE = "\033[1m"
RESET_STYLE = "\033[0m"


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

def _log_fs_op_message(level: int, message: str, logger: logging.Logger | None = None):
    """Helper to log messages using provided logger or print as fallback for fs_operations."""
    if logger:
        logger.log(level, message)
    else:
        prefix = ""
        if level == logging.ERROR:
            prefix = "ERROR (fs_op): "
        elif level == logging.WARNING:
            prefix = "WARNING (fs_op): "
        elif level == logging.INFO:
            prefix = "INFO (fs_op): "
        print(f"{prefix}{message}")


def get_file_encoding(file_path: Path, sample_size: int = 10240, logger: logging.Logger | None = None) -> str | None:
    if file_path.suffix.lower() == '.rtf':
        return 'latin-1' 

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
        if not raw_data:
            return DEFAULT_ENCODING_FALLBACK 

        # 1. Try UTF-8 first as it's very common and chardet can misidentify it for small samples
        try:
            raw_data.decode('utf-8', errors='strict') # Use strict for UTF-8 detection
            return 'utf-8'
        except UnicodeDecodeError:
            pass 

        # 2. Use chardet as a strong hint
        detected_by_chardet = chardet.detect(raw_data)
        chardet_encoding: str | None = detected_by_chardet.get('encoding')
        
        normalized_chardet_candidate = None
        if chardet_encoding:
            norm_low = chardet_encoding.lower()
            # Normalize common aliases
            if norm_low in ('windows-1252', '1252'):
                normalized_chardet_candidate = 'cp1252'
            elif norm_low in ('latin_1', 'iso-8859-1', 'iso8859_1', 'iso-8859-15', 'iso8859-15'):
                normalized_chardet_candidate = 'latin1'
            elif norm_low in ('windows-1254', '1254'): # Turkish, often confused with cp1252
                 # If chardet suggests a specific windows codepage like 1254,
                 # and cp1252 can also decode it, prefer cp1252 as it's more common for "Western-like" text.
                try:
                    raw_data.decode('cp1252', errors='surrogateescape')
                    return 'cp1252' 
                except (UnicodeDecodeError, LookupError):
                    # cp1252 failed, try the original chardet suggestion if it's different
                    if norm_low != 'cp1252': 
                        try:
                            raw_data.decode(norm_low, errors='surrogateescape')
                            return norm_low
                        except (UnicodeDecodeError, LookupError):
                            pass 
            else:
                normalized_chardet_candidate = norm_low
        
        # Try chardet's normalized candidate if it exists and hasn't been returned yet
        if normalized_chardet_candidate and normalized_chardet_candidate != 'utf-8':
            try:
                raw_data.decode(normalized_chardet_candidate, errors='surrogateescape')
                if normalized_chardet_candidate == 'latin1':
                    # If latin1 was suggested and works, check if cp1252 also works, as it's a more specific superset for Western text
                    try:
                        raw_data.decode('cp1252', errors='surrogateescape')
                        return 'cp1252' 
                    except (UnicodeDecodeError, LookupError):
                        return 'latin1' # cp1252 failed, stick with latin1
                return normalized_chardet_candidate
            except (UnicodeDecodeError, LookupError):
                pass

        # 3. Fallback explicit checks if UTF-8 and chardet's primary suggestion failed or wasn't definitive
        for enc_try in ['cp1252', 'latin1']:
            if normalized_chardet_candidate != enc_try: # Avoid re-trying if it was chardet's candidate and failed
                try:
                    raw_data.decode(enc_try, errors='surrogateescape')
                    return enc_try
                except (UnicodeDecodeError, LookupError):
                    pass
            
        _log_fs_op_message(logging.DEBUG, f"Encoding for {file_path} could not be confidently determined. Chardet: {detected_by_chardet}. Using {DEFAULT_ENCODING_FALLBACK}.", logger)
        return DEFAULT_ENCODING_FALLBACK
            
    except Exception as e:
        _log_fs_op_message(logging.WARNING, f"Error detecting encoding for {file_path}: {e}. Falling back to {DEFAULT_ENCODING_FALLBACK}.", logger)
        return DEFAULT_ENCODING_FALLBACK


def load_ignore_patterns(ignore_file_path: Path, logger: logging.Logger | None = None) -> pathspec.PathSpec | None:
    if not ignore_file_path.is_file():
        return None
    try:
        with open(ignore_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            patterns = f.readlines()
        valid_patterns = [p for p in (line.strip() for line in patterns) if p and not p.startswith('#')]
        return pathspec.PathSpec.from_lines('gitwildmatch', valid_patterns) if valid_patterns else None
    except Exception as e:
        _log_fs_op_message(logging.WARNING, f"Could not load ignore file {ignore_file_path}: {e}", logger)
        return None

def _walk_for_scan(
    root_dir: Path, excluded_dirs_abs: list[Path],
    ignore_symlinks: bool, ignore_spec: pathspec.PathSpec | None,
    logger: logging.Logger | None = None
) -> collections.abc.Iterator[Path]:
    for item_path_from_rglob in root_dir.rglob("*"):
        try:
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
                except ValueError: # Not relative, should not happen with rglob from root
                    pass 
                except Exception as e_spec: # Catch other pathspec errors
                    _log_fs_op_message(logging.WARNING, f"Error during ignore_spec matching for {item_path_from_rglob} relative to {root_dir}: {e_spec}", logger)
            yield item_path_from_rglob
        except OSError as e_os: # Catch OSError from is_symlink, is_dir
            _log_fs_op_message(logging.WARNING, f"OS error accessing attributes of {item_path_from_rglob}: {e_os}. Skipping item.", logger)
            continue
        except Exception as e_gen: # Catch any other unexpected error for this item
            _log_fs_op_message(logging.ERROR, f"Unexpected error processing item {item_path_from_rglob} in _walk_for_scan: {e_gen}. Skipping item.", logger)
            continue


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
    skip_file_renaming: bool = False, skip_folder_renaming: bool = False, skip_content: bool = False,
    logger: logging.Logger | None = None
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

    item_iterator = _walk_for_scan(abs_root_dir, resolved_abs_excluded_dirs, ignore_symlinks, ignore_spec, logger=logger)
    
    for item_abs_path in item_iterator:
        try:
            relative_path_str = str(item_abs_path.relative_to(abs_root_dir)).replace("\\", "/")
        except ValueError:
            _log_fs_op_message(logging.WARNING, f"Could not get relative path for {item_abs_path} against {abs_root_dir}. Skipping.", logger)
            continue
        
        if item_abs_path.name in excluded_basenames or relative_path_str in excluded_relative_paths_set:
            continue

        original_name = item_abs_path.name
        searchable_name = unicodedata.normalize('NFC', strip_control_characters(strip_diacritics(original_name)))
        
        item_is_dir = False
        item_is_file = False
        item_is_symlink = False
        try:
            item_is_symlink = item_abs_path.is_symlink()
            if not item_is_symlink:
                item_is_dir = item_abs_path.is_dir()
                item_is_file = item_abs_path.is_file()
            elif ignore_symlinks:
                 continue
            else: 
                 # For name replacement, treat symlinks (to files or dirs) as if they are files
                 # so their names can be processed. Content is handled based on actual type.
                 item_is_file = True # This allows symlink name to be processed by file logic
        except OSError as e_stat:
            _log_fs_op_message(logging.WARNING, f"OS error checking type of {item_abs_path}: {e_stat}. Skipping item.", logger)
            continue


        if (scan_pattern and scan_pattern.search(searchable_name)) and \
           (replace_occurrences(original_name) != original_name):
            tx_type_val: str | None = None
            if item_is_dir: # True only if not a symlink and is_dir() was true
                if not skip_folder_renaming:
                    tx_type_val = TransactionType.FOLDER_NAME.value
            elif item_is_file or item_is_symlink: # True if is_file() or is_symlink() (and not ignore_symlinks)
                if not skip_file_renaming:
                    tx_type_val = TransactionType.FILE_NAME.value
            
            if tx_type_val:
                tx_id_tuple = (relative_path_str, tx_type_val, 0)
                if tx_id_tuple not in existing_transaction_ids:
                    processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":tx_type_val, "PATH":relative_path_str, "ORIGINAL_NAME":original_name, "LINE_NUMBER":0, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                    existing_transaction_ids.add(tx_id_tuple)

        # Content processing should only happen for actual files, not symlinks to directories
        # and only if item_is_file was true (meaning it's a file or a symlink we are considering for content if it points to a file)
        # The `item_abs_path.is_file()` check inside this block will resolve the symlink if it's one.
        if not skip_content:
            try:
                if item_abs_path.is_file(): # This resolves symlinks to files
                    is_rtf = item_abs_path.suffix.lower() == '.rtf'
                    try:
                        is_bin = is_binary_file(str(item_abs_path))
                    except FileNotFoundError: 
                        _log_fs_op_message(logging.WARNING, f"File not found for binary check: {item_abs_path}. Skipping content scan.", logger)
                        continue
                    except Exception as e_isbin:
                        _log_fs_op_message(logging.WARNING, f"Could not determine if {item_abs_path} is binary: {e_isbin}. Skipping content scan.", logger)
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
                            except OSError as e_bin_read: 
                                _log_fs_op_message(logging.WARNING, f"OS error reading binary file {item_abs_path} for logging: {e_bin_read}", logger)
                            except Exception as e_bin_proc: 
                                _log_fs_op_message(logging.WARNING, f"Error processing binary {item_abs_path} for logging: {e_bin_proc}", logger)
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
                            file_encoding = 'utf-8' # Content is now plain text
                        except OSError as e_rtf_read:
                            _log_fs_op_message(logging.WARNING, f"OS error reading RTF file {item_abs_path}: {e_rtf_read}", logger)
                            continue
                        except Exception as e_rtf_proc:
                            _log_fs_op_message(logging.WARNING, f"Error extracting text from RTF {item_abs_path}: {e_rtf_proc}", logger)
                            continue
                    else:
                        file_encoding = get_file_encoding(item_abs_path, logger=logger) or DEFAULT_ENCODING_FALLBACK
                        try:
                            with open(item_abs_path, 'r', encoding=file_encoding, errors='surrogateescape', newline='') as f_scan:
                                file_content_for_scan = f_scan.read()
                        except OSError as e_txt_read:
                            _log_fs_op_message(logging.WARNING, f"OS error reading text file {item_abs_path} (enc:{file_encoding}): {e_txt_read}", logger)
                            continue
                        except Exception as e_txt_proc: # Catch other errors like LookupError for encoding
                            _log_fs_op_message(logging.WARNING, f"Error reading text file {item_abs_path} (enc:{file_encoding}): {e_txt_proc}", logger)
                            continue
                    
                    if file_content_for_scan is not None:
                        lines_for_scan = file_content_for_scan.splitlines(keepends=True)
                        if not lines_for_scan and file_content_for_scan: # Handle files with no newlines but content
                            lines_for_scan = [file_content_for_scan]

                        for line_idx, line_content in enumerate(lines_for_scan):
                            searchable_line_content = unicodedata.normalize('NFC', strip_control_characters(strip_diacritics(line_content)))
                            if (scan_pattern and scan_pattern.search(searchable_line_content)) and \
                               (replace_occurrences(line_content) != line_content):
                                tx_id_tuple = (relative_path_str, TransactionType.FILE_CONTENT_LINE.value, line_idx + 1)
                                if tx_id_tuple not in existing_transaction_ids:
                                    processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":TransactionType.FILE_CONTENT_LINE.value, "PATH":relative_path_str, "LINE_NUMBER":line_idx+1, "ORIGINAL_LINE_CONTENT":line_content, "ORIGINAL_ENCODING":file_encoding, "IS_RTF":is_rtf, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                                    existing_transaction_ids.add(tx_id_tuple)
            except OSError as e_stat_content: # Catch OSError from item_abs_path.is_file()
                _log_fs_op_message(logging.WARNING, f"OS error checking if {item_abs_path} is a file for content processing: {e_stat_content}. Skipping content scan for this item.", logger)

    return processed_transactions

def load_transactions(json_file_path: Path, logger: logging.Logger | None = None) -> list[dict[str, Any]] | None:
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
                    _log_fs_op_message(logging.WARNING, f"Invalid format in {path_to_try}. Expected a list.", logger)
                    loaded_data = None
            except json.JSONDecodeError as jde:
                _log_fs_op_message(logging.WARNING, f"Failed to decode JSON from {path_to_try}: {jde}", logger)
            except Exception as e:
                _log_fs_op_message(logging.WARNING, f"Failed to load transactions from {path_to_try}: {e}", logger)
    if loaded_data is None and json_file_path.exists(): # Only log error if primary file existed and failed
        _log_fs_op_message(logging.ERROR, f"Could not load valid transactions from {json_file_path} or its backup.", logger)
    return None

def save_transactions(transactions: list[dict[str, Any]], json_file_path: Path, logger: logging.Logger | None = None) -> None:
    if json_file_path.exists():
        try:
            shutil.copy2(json_file_path, json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT))
        except Exception as e:
            _log_fs_op_message(logging.WARNING, f"Could not backup {json_file_path}: {e}", logger)
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=4)
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Could not save transactions to {json_file_path}: {e}", logger)
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

            if tx_item.get('TYPE') == TransactionType.FILE_CONTENT_LINE.value and proposed_content_after_execution is not None: # Safe access to TYPE
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
    path_translation_map: dict[str, str], path_cache: dict[str, Path], dry_run: bool,
    logger: logging.Logger | None = None
) -> tuple[TransactionStatus, str | None, bool]:
    orig_rel_path = tx_item["PATH"]
    orig_name = tx_item["ORIGINAL_NAME"]
    try:
        current_abs_path = _get_current_absolute_path(orig_rel_path, root_dir, path_translation_map, path_cache)
    except FileNotFoundError:
        return TransactionStatus.SKIPPED, f"Parent for '{orig_rel_path}' not found.", False
    except Exception as e:
        return TransactionStatus.FAILED, f"Error resolving path for '{orig_rel_path}': {e}", False
    
    _log_fs_op_message(logging.DEBUG, f"FS_OP_RENAME: Attempting rename for orig_rel_path='{orig_rel_path}'. current_abs_path='{current_abs_path}', os.path.exists={os.path.exists(str(current_abs_path))}", logger)

    if not os.path.exists(str(current_abs_path)): # Use os.path.exists for consistency with test
        return TransactionStatus.SKIPPED, f"Item '{current_abs_path}' (derived from '{orig_rel_path}') not found by os.path.exists before rename.", False
        
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

        if os.path.exists(str(new_abs_path)): # Use os.path.exists
            return TransactionStatus.SKIPPED, f"Target path '{new_abs_path}' for new name already exists.", False
        
        _log_fs_op_message(logging.DEBUG, f"FS_OP_RENAME: Executing: Path('{current_abs_path}').rename('{new_abs_path}')", logger)
        
        Path(current_abs_path).rename(new_abs_path)
        
        new_path_exists_after_rename = os.path.exists(str(new_abs_path))
        old_path_gone_after_rename = not os.path.exists(str(current_abs_path))
        rename_successful_on_disk = new_path_exists_after_rename and old_path_gone_after_rename

        _log_fs_op_message(logging.DEBUG, f"FS_OP_RENAME: After rename attempt (using os.path.exists): new_abs_path ('{new_abs_path}') exists: {new_path_exists_after_rename}. old_abs_path ('{current_abs_path}') exists: {not old_path_gone_after_rename}. rename_successful_on_disk: {rename_successful_on_disk}", logger)

        if not rename_successful_on_disk:
            return TransactionStatus.FAILED, f"Rename of '{current_abs_path}' to '{new_abs_path}' did not complete as expected on disk (new_exists={new_path_exists_after_rename}, old_gone={old_path_gone_after_rename}).", False

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
    path_translation_map: dict[str, str], path_cache: dict[str, Path], dry_run: bool,
    logger: logging.Logger | None = None
) -> tuple[TransactionStatus, str | None, bool]:
    _log_fs_op_message(logging.DEBUG, f"FS_OP_EXEC_CONTENT_ENTRY: tx_path='{tx_item.get('PATH')}', line={tx_item.get('LINE_NUMBER')}, dry_run={dry_run}", logger)

    orig_rel_path = tx_item["PATH"]
    line_num = tx_item["LINE_NUMBER"]
    orig_line_content_from_tx = tx_item["ORIGINAL_LINE_CONTENT"]
    encoding = tx_item["ORIGINAL_ENCODING"] or DEFAULT_ENCODING_FALLBACK
    is_rtf = tx_item.get("IS_RTF", False)

    actual_new_line_content_unicode = replace_occurrences(orig_line_content_from_tx)
    tx_item["PROPOSED_LINE_CONTENT"] = actual_new_line_content_unicode

    if actual_new_line_content_unicode == orig_line_content_from_tx:
        return TransactionStatus.SKIPPED, "Line content unchanged by replacement logic.", False

    current_abs_path: Path
    if dry_run:
        # For dry run content checks, always use the original path,
        # as the file rename hasn't actually happened on disk.
        current_abs_path = root_dir / Path(orig_rel_path)
    else:
        try:
            current_abs_path = _get_current_absolute_path(orig_rel_path, root_dir, path_translation_map, path_cache)
        except FileNotFoundError:
            return TransactionStatus.SKIPPED, f"Parent for '{orig_rel_path}' not found.", False
        except Exception as e:
            return TransactionStatus.FAILED, f"Error resolving path for '{orig_rel_path}': {e}", False

    if current_abs_path.is_symlink(): # This check is fine for both dry and real runs
        return TransactionStatus.SKIPPED, f"'{current_abs_path}' is a symlink; content modification skipped.", False
    if not current_abs_path.is_file():
        return TransactionStatus.SKIPPED, f"'{current_abs_path}' not found or not a file.", False
    
    if dry_run: # If it passed the checks above and is a dry_run, it's COMPLETED (for planning)
        return TransactionStatus.COMPLETED, "DRY_RUN", False

    if is_rtf: # This check is after dry_run, so it only applies to actual execution
        return TransactionStatus.SKIPPED, "RTF content modification is skipped to preserve formatting. Match was based on extracted text.", False

    can_orig_be_strictly_encoded = False
    try:
        orig_line_content_from_tx.encode(encoding, 'strict')
        can_orig_be_strictly_encoded = True
    except UnicodeEncodeError:
        pass 

    can_new_be_strictly_encoded = False
    try:
        actual_new_line_content_unicode.encode(encoding, 'strict')
        can_new_be_strictly_encoded = True
    except UnicodeEncodeError:
        pass
    
    if can_orig_be_strictly_encoded and not can_new_be_strictly_encoded:
        return TransactionStatus.FAILED, f"Replacement introduced characters unencodable in '{encoding}' (strict check). Original line was strictly encodable.", False

    temp_file_path: Path | None = None
    original_file_bytes: bytes | None = None
    try:
        _ensure_within_sandbox(current_abs_path, root_dir, f"content write for {current_abs_path.name}")
        original_file_bytes = current_abs_path.read_bytes()
        
        temp_file_path = current_abs_path.with_name(f"{current_abs_path.name}.{uuid.uuid4()}.tmp")
        
        full_original_content_unicode = original_file_bytes.decode(encoding, errors='surrogateescape')
        lines_unicode = full_original_content_unicode.splitlines(keepends=True)
        if not lines_unicode and full_original_content_unicode:
            lines_unicode = [full_original_content_unicode]

        if not (0 <= line_num - 1 < len(lines_unicode)):
            if temp_file_path.exists():
                temp_file_path.unlink(missing_ok=True)
            return TransactionStatus.FAILED, f"Line number {line_num} out of bounds for file {current_abs_path} (has {len(lines_unicode)} lines). File may have changed.", False

        current_line_in_file_decoded = lines_unicode[line_num - 1]
        if current_line_in_file_decoded != orig_line_content_from_tx:
            if temp_file_path.exists():
                temp_file_path.unlink(missing_ok=True)
            return TransactionStatus.FAILED, f"Content of line {line_num} in {current_abs_path} has changed since scan. Expected: {repr(orig_line_content_from_tx)}, Found: {repr(current_line_in_file_decoded)}", False

        lines_unicode[line_num - 1] = actual_new_line_content_unicode
        expected_new_full_content_unicode = "".join(lines_unicode)
        
        with open(temp_file_path, 'w', encoding=encoding, errors='surrogateescape', newline='') as outf:
            outf.write(expected_new_full_content_unicode)
        
        temp_file_bytes = temp_file_path.read_bytes()
        expected_new_bytes = expected_new_full_content_unicode.encode(encoding, errors='surrogateescape')

        if temp_file_bytes != expected_new_bytes:
            if temp_file_path.exists():
                temp_file_path.unlink(missing_ok=True)
            return TransactionStatus.FAILED, f"Byte-for-byte verification failed for {current_abs_path}. Temp file content did not match expected byte reconstruction.", False

        shutil.copymode(current_abs_path, temp_file_path)
        os.replace(temp_file_path, current_abs_path)
        temp_file_path = None 
        return TransactionStatus.COMPLETED, None, False

    except OSError as e:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        if _is_retryable_os_error(e):
            return TransactionStatus.RETRY_LATER, f"OS error (retryable): {e}", True
        return TransactionStatus.FAILED, f"OS error: {e}", False
    except SandboxViolationError as sve:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        return TransactionStatus.FAILED, f"SandboxViolation: {sve}", False
    except RuntimeError as rte: 
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        return TransactionStatus.FAILED, str(rte), False
    except Exception as e:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        return TransactionStatus.FAILED, f"Unexpected content update error for {current_abs_path}: {e}", False
    finally:
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink(missing_ok=True)
            except OSError: 
                pass 

def _highlight_string(text: str, pattern: re.Pattern | None, color: str) -> str:
    """Highlights occurrences of pattern in text with the given color."""
    if not pattern or not text:
        return text
    
    # Use NFC normalized version of text for matching, as pattern is based on canonical keys
    nfc_text = unicodedata.normalize('NFC', text)
    
    # Substitute matches in the NFC text with colored versions
    # The lambda function gets the matched object `m` and wraps `m.group(0)` (the matched string)
    # with color codes.
    highlighted_nfc_text = pattern.sub(lambda m: f"{color}{m.group(0)}{RESET_STYLE}", nfc_text)
    
    # If the original text was different from its NFC form, it's complex to map highlights back perfectly.
    # For display, showing the highlighted NFC form is the most straightforward and consistent
    # with how the matching logic (which uses NFC) operates.
    # If text == nfc_text, then highlighted_nfc_text is directly applicable to original structure.
    # If they differ, user sees highlights on the NFC normalized version.
    return highlighted_nfc_text


def _get_user_interactive_choice(tx_item: dict[str, Any], root_dir: Path, path_translation_map: dict[str, str], path_cache: dict[str, Path], logger: logging.Logger | None) -> str:
    """Displays transaction details and prompts user for action in interactive mode."""
    print(f"\n{MAGENTA_FG}--- Interactive Mode: Pending Transaction ---{RESET_STYLE}")
    tx_type = tx_item.get("TYPE")
    tx_path = tx_item.get("PATH", "N/A")
    scan_pattern = get_scan_pattern() # Get the compiled regex pattern for highlighting

    if tx_type in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
        item_kind = "Folder" if tx_type == TransactionType.FOLDER_NAME.value else "File"
        original_name = tx_item.get("ORIGINAL_NAME", "N/A")
        proposed_name = replace_occurrences(original_name)
        
        highlighted_original_name = _highlight_string(original_name, scan_pattern, RED_FG)
        
        print(f"{CYAN_FG}Action:{RESET_STYLE} Rename {item_kind}")
        print(f"{CYAN_FG}Path:{RESET_STYLE}   {tx_path}")
        print(f"{DIM_STYLE}Original Name:{RESET_STYLE} {DIM_STYLE}{highlighted_original_name}{RESET_STYLE}")
        print(f"{YELLOW_FG}Proposed Name:{RESET_STYLE} {proposed_name}")
    
    elif tx_type == TransactionType.FILE_CONTENT_LINE.value:
        line_num = tx_item.get("LINE_NUMBER", "N/A")
        original_line_content = tx_item.get("ORIGINAL_LINE_CONTENT", "")
        # Proposed line is already calculated and stored if scan was done, or will be by _execute_content_line_transaction
        # For display, we re-calculate it here to show the user.
        proposed_line_content = replace_occurrences(original_line_content) 
        encoding = tx_item.get("ORIGINAL_ENCODING", "N/A")

        print(f"{CYAN_FG}Action:{RESET_STYLE} Modify File Content")
        print(f"{CYAN_FG}File:{RESET_STYLE}   {tx_path} (Line: {line_num}, Encoding: {encoding})")
        
        try:
            current_abs_path_for_context = _get_current_absolute_path(tx_path, root_dir, path_translation_map, path_cache)
            if current_abs_path_for_context.is_file():
                full_content_bytes = current_abs_path_for_context.read_bytes()
                full_content_unicode = full_content_bytes.decode(encoding, errors='surrogateescape')
                all_lines = full_content_unicode.splitlines(keepends=True)
                if not all_lines and full_content_unicode:
                    all_lines = [full_content_unicode]

                actual_line_num_for_array = line_num -1 # Adjust for 0-based indexing

                context_start_idx = max(0, actual_line_num_for_array - 2)
                context_end_idx = min(len(all_lines), actual_line_num_for_array + 3)
                
                print(f"{DIM_STYLE}--- Context ---{RESET_STYLE}")
                for i in range(context_start_idx, context_end_idx):
                    line_to_print_raw = all_lines[i]
                    # Rstrip only for display to avoid messing with calculations or actual content
                    display_line = line_to_print_raw.rstrip('\r\n') 

                    if i == actual_line_num_for_array: # Target line
                        highlighted_original_line = _highlight_string(display_line, scan_pattern, RED_FG)
                        print(f"{DIM_STYLE}Original Line {i+1}:{RESET_STYLE} {DIM_STYLE}{highlighted_original_line}{RESET_STYLE}")
                        
                        # Display proposed line (already has replacements applied)
                        # No need to highlight proposed line's keys, as they should be values now.
                        # We could highlight the *differences* but that's more complex.
                        print(f"{YELLOW_FG}{BOLD_STYLE}Proposed Line {i+1}:{RESET_STYLE}{YELLOW_FG} {proposed_line_content.rstrip(os.linesep)}{RESET_STYLE}")
                    else: # Context lines
                        # For context lines, do not highlight internal matches to keep focus on target line
                        print(f"{DIM_STYLE}Line {i+1}:{RESET_STYLE} {DIM_STYLE}{display_line}{RESET_STYLE}")
                print(f"{DIM_STYLE}---------------{RESET_STYLE}")
            else: # File not found for context
                print(f"{RED_FG}Could not read file for context: {current_abs_path_for_context}{RESET_STYLE}")
                highlighted_original_line = _highlight_string(original_line_content.rstrip(os.linesep), scan_pattern, RED_FG)
                print(f"{DIM_STYLE}Original Line:{RESET_STYLE} {DIM_STYLE}{highlighted_original_line}{RESET_STYLE}")
                print(f"{YELLOW_FG}Proposed Line:{RESET_STYLE} {proposed_line_content.rstrip(os.linesep)}")

        except Exception as e:
            _log_fs_op_message(logging.WARNING, f"Error reading file for interactive context ({tx_path}): {e}", logger)
            print(f"{RED_FG}Error getting context. Displaying raw lines:{RESET_STYLE}")
            highlighted_original_line = _highlight_string(original_line_content.rstrip(os.linesep), scan_pattern, RED_FG)
            print(f"{DIM_STYLE}Original Line:{RESET_STYLE} {DIM_STYLE}{highlighted_original_line}{RESET_STYLE}")
            print(f"{YELLOW_FG}Proposed Line:{RESET_STYLE} {proposed_line_content.rstrip(os.linesep)}")
    else: # Unknown transaction type
        print(f"{RED_FG}Unknown transaction type: {tx_type}{RESET_STYLE}")
        return 's' 

    while True:
        choice = input(f"{BLUE_FG}Approve? ({GREEN_FG}A/Approve{BLUE_FG}, {YELLOW_FG}S/Skip{BLUE_FG}, {RED_FG}Q/Quit{BLUE_FG}): {RESET_STYLE}").lower()
        if choice in ['a', 'approve', 'y', 'yes']:
            return 'approve'
        if choice in ['s', 'skip', 'n', 'no']:
            return 'skip'
        if choice in ['q', 'quit']:
            return 'quit'
        print(f"{RED_FG}Invalid choice. Please enter 'A', 'S', or 'Q'.{RESET_STYLE}")


def execute_all_transactions(
    transactions_file_path: Path, root_dir: Path, dry_run: bool, resume: bool,
    global_timeout_minutes: int,
    skip_file_renaming: bool, skip_folder_renaming: bool, skip_content: bool,
    skip_scan: bool, interactive_mode: bool, logger: logging.Logger | None = None
) -> dict[str, int]:
    transactions = load_transactions(transactions_file_path, logger=logger)
    if not transactions:
        return {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}

    stats = {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}
    path_translation_map: dict[str,str] = {}
    path_cache: dict[str,Path] = {}
    abs_r_dir = root_dir

    if resume: 
        for tx in transactions:
            tx_type = tx.get("TYPE")
            if tx.get("STATUS") == TransactionStatus.COMPLETED.value and \
               tx.get("ERROR_MESSAGE") != "DRY_RUN" and \
               tx_type in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
                if "ORIGINAL_NAME" in tx:
                    path_translation_map[tx["PATH"]] = replace_occurrences(tx["ORIGINAL_NAME"])
                else:
                    _log_fs_op_message(logging.WARNING, f"Resuming: Transaction {tx.get('id')} for path {tx.get('PATH')} is a completed rename but missing ORIGINAL_NAME. Cannot accurately reflect this rename in path translation map for subsequent transactions in this run.", logger)
    
    def sort_key(tx):
        type_o={TransactionType.FOLDER_NAME.value:0,TransactionType.FILE_NAME.value:1,TransactionType.FILE_CONTENT_LINE.value:2}
        return (type_o.get(tx.get("TYPE"), 3), tx["PATH"].count('/'), tx["PATH"], tx.get("LINE_NUMBER",0)) 
    transactions.sort(key=sort_key)

    execution_start_time = time.time()
    max_overall_retry_passes = 500 if global_timeout_minutes == 0 else 20 # Max passes for non-interactive or if timeout is 0
    if interactive_mode and global_timeout_minutes !=0 : # For interactive, allow fewer passes if timeout is set
        max_overall_retry_passes = 5 
    
    current_overall_retry_attempt = 0
    
    if resume or skip_scan: 
        for tx_item_for_reset in transactions:
            current_tx_status_str = tx_item_for_reset.get("STATUS")
            if current_tx_status_str == TransactionStatus.COMPLETED.value and \
               tx_item_for_reset.get("ERROR_MESSAGE") == "DRY_RUN":
                tx_item_for_reset["STATUS"] = TransactionStatus.PENDING.value
                tx_item_for_reset.pop('ERROR_MESSAGE', None)
                tx_item_for_reset.pop('timestamp_processed', None)
                tx_item_for_reset.pop('timestamp_next_retry', None)
                tx_item_for_reset['retry_count'] = 0
            elif resume and current_tx_status_str == TransactionStatus.FAILED.value:
                _log_fs_op_message(logging.INFO, f"Resuming FAILED tx as PENDING: {tx_item_for_reset.get('id','N/A')} ({tx_item_for_reset.get('PATH','N/A')})", logger)
                tx_item_for_reset["STATUS"] = TransactionStatus.PENDING.value
                tx_item_for_reset.pop('ERROR_MESSAGE', None)
                tx_item_for_reset.pop('timestamp_processed', None)
                tx_item_for_reset.pop('timestamp_next_retry', None)
                tx_item_for_reset['retry_count'] = 0
            elif resume and current_tx_status_str == TransactionStatus.RETRY_LATER.value: # Also reset RETRY_LATER on resume
                _log_fs_op_message(logging.INFO, f"Resuming RETRY_LATER tx as PENDING: {tx_item_for_reset.get('id','N/A')} ({tx_item_for_reset.get('PATH','N/A')})", logger)
                tx_item_for_reset["STATUS"] = TransactionStatus.PENDING.value
                tx_item_for_reset.pop('timestamp_next_retry', None)


    user_quit_interactive = False
    while True: # Main retry loop
        processed_in_this_pass = 0
        items_still_requiring_retry = []

        for tx_item in transactions:
            if user_quit_interactive:
                if tx_item.get("STATUS") == TransactionStatus.PENDING.value: 
                    update_transaction_status_in_list(transactions, tx_item["id"], TransactionStatus.SKIPPED, "Operation aborted by user in interactive mode.")
                continue 

            _log_fs_op_message(logging.DEBUG, f"FS_OP_EXEC_ALL_ITERATING_TX: {tx_item}", logger)

            tx_id = tx_item.setdefault("id", str(uuid.uuid4()))
            current_status = TransactionStatus(tx_item.get("STATUS", TransactionStatus.PENDING.value))
            tx_type = tx_item.get("TYPE") 

            if (skip_folder_renaming and tx_type == TransactionType.FOLDER_NAME.value) or \
               (skip_file_renaming and tx_type == TransactionType.FILE_NAME.value) or \
               (skip_content and tx_type == TransactionType.FILE_CONTENT_LINE.value):
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
                else: # Retry time is due
                    current_status = TransactionStatus.PENDING 
            
            tx_item["STATUS"] = current_status.value 

            if current_status == TransactionStatus.PENDING:
                if interactive_mode and not dry_run:
                    user_choice = _get_user_interactive_choice(tx_item, abs_r_dir, path_translation_map, path_cache, logger)
                    if user_choice == 'skip':
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "Skipped by user in interactive mode.")
                        save_transactions(transactions, transactions_file_path, logger=logger)
                        processed_in_this_pass +=1
                        continue
                    elif user_choice == 'quit':
                        _log_fs_op_message(logging.INFO, "Operation aborted by user in interactive mode.", logger)
                        print(f"{YELLOW_FG}Operation aborted by user.{RESET_STYLE}")
                        user_quit_interactive = True
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "Operation aborted by user in interactive mode.") 
                        save_transactions(transactions, transactions_file_path, logger=logger)
                        processed_in_this_pass +=1
                        continue 
                
                update_transaction_status_in_list(transactions, tx_id, TransactionStatus.IN_PROGRESS)
                _log_fs_op_message(logging.DEBUG, f"FS_OP_EXEC_ALL_ATTEMPTING: tx_id='{tx_id}', type='{tx_type}', path='{tx_item.get('PATH')}', line={tx_item.get('LINE_NUMBER', 'N/A')}, status_before_exec_call='IN_PROGRESS', dry_run={dry_run}", logger)

                new_stat_from_exec: TransactionStatus
                err_msg_from_exec: str | None = None
                final_prop_content_for_log: str | None = None
                is_retryable_error_from_exec = False

                try:
                    if tx_type in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
                        new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = _execute_rename_transaction(tx_item, abs_r_dir, path_translation_map, path_cache, dry_run, logger=logger)
                    elif tx_type == TransactionType.FILE_CONTENT_LINE.value:
                        new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = _execute_content_line_transaction(tx_item, abs_r_dir, path_translation_map, path_cache, dry_run, logger=logger)
                        final_prop_content_for_log = tx_item.get("PROPOSED_LINE_CONTENT")
                    else:
                        new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = TransactionStatus.FAILED, f"Unknown type: {tx_type}", False
                except Exception as e_outer:
                    new_stat_from_exec, err_msg_from_exec, is_retryable_error_from_exec = TransactionStatus.FAILED, f"Outer execution error: {e_outer}", False
                    _log_fs_op_message(logging.CRITICAL, f"CRITICAL outer error processing tx {tx_id}: {e_outer}", logger) 

                if new_stat_from_exec == TransactionStatus.RETRY_LATER and is_retryable_error_from_exec:
                    retry_count = tx_item.get('retry_count', 0) # Already incremented by update_transaction_status_in_list
                    base_delay_seconds = 2 # Shorter base for quicker retries initially
                    max_backoff_seconds = 120 # Max 2 minutes for a single backoff
                    # Exponential backoff: 2^0*2=2s, 2^1*2=4s, 2^2*2=8s, ...
                    backoff_seconds = min( (2 ** retry_count) * base_delay_seconds, max_backoff_seconds)
                    tx_item['timestamp_next_retry'] = time.time() + backoff_seconds
                    _log_fs_op_message(logging.INFO, f"Transaction {tx_id} ({tx_item['PATH']}) set to RETRY_LATER. Next attempt in ~{backoff_seconds:.0f}s (Attempt {retry_count + 1}). Error: {err_msg_from_exec}", logger)
                    items_still_requiring_retry.append(tx_item)

                update_transaction_status_in_list(transactions, tx_id, new_stat_from_exec, err_msg_from_exec, final_prop_content_for_log, is_retryable_error_from_exec)
                save_transactions(transactions, transactions_file_path, logger=logger)
                processed_in_this_pass += 1
        
        current_overall_retry_attempt += 1

        if user_quit_interactive: # If user quit, no more retries needed for this run
            break

        if not items_still_requiring_retry:
            _log_fs_op_message(logging.DEBUG, "No items require further retry in this pass. Exiting retry loop.", logger)
            break # All items processed or failed definitively

        timed_out = False
        if global_timeout_minutes > 0 and (time.time() - execution_start_time) / 60 >= global_timeout_minutes:
            _log_fs_op_message(logging.INFO, f"Global execution timeout of {global_timeout_minutes} minutes reached.", logger)
            timed_out = True
        
        max_retries_hit = False
        if current_overall_retry_attempt >= max_overall_retry_passes:
            _log_fs_op_message(logging.WARNING, f"Max retry passes ({max_overall_retry_passes}) reached.", logger)
            max_retries_hit = True
        
        if timed_out or max_retries_hit:
            failure_reason = "Global timeout reached." if timed_out else "Max retry passes reached."
            for tx_item_failed_retry in items_still_requiring_retry:
                if tx_item_failed_retry["STATUS"] == TransactionStatus.RETRY_LATER.value: # Check if it's still marked for retry
                    update_transaction_status_in_list(transactions, tx_item_failed_retry["id"], TransactionStatus.FAILED, failure_reason)
            save_transactions(transactions, transactions_file_path, logger=logger)
            break # Exit main retry loop

        if items_still_requiring_retry: # If there are items, but no timeout/max_pass condition met
            next_due_retry_timestamp = min(itx.get("timestamp_next_retry", float('inf')) for itx in items_still_requiring_retry)
            sleep_duration = max(0.1, next_due_retry_timestamp - time.time())

            if global_timeout_minutes > 0:
                remaining_time_budget = (execution_start_time + global_timeout_minutes * 60) - time.time()
                if remaining_time_budget <= 0: # Double check timeout before sleep
                    _log_fs_op_message(logging.INFO, f"Global execution timeout of {global_timeout_minutes} minutes reached (checked before sleep).", logger)
                    for tx_item_timeout_retry in items_still_requiring_retry:
                         if tx_item_timeout_retry["STATUS"] == TransactionStatus.RETRY_LATER.value:
                            update_transaction_status_in_list(transactions, tx_item_timeout_retry["id"], TransactionStatus.FAILED, "Global timeout reached during retry phase.")
                    save_transactions(transactions, transactions_file_path, logger=logger)
                    break
                sleep_duration = min(sleep_duration, remaining_time_budget, 60.0) # Cap sleep to 60s or remaining budget
            else: # Indefinite timeout
                sleep_duration = min(sleep_duration, 60.0) # Cap sleep to 60s

            if sleep_duration > 0.05 :
                 _log_fs_op_message(logging.INFO, f"Retry Pass {current_overall_retry_attempt} complete. {len(items_still_requiring_retry)} items pending retry. Next check in ~{sleep_duration:.1f}s.", logger)
                 time.sleep(sleep_duration)
            else: # Very short or no sleep needed if next retry is immediate
                time.sleep(0.05) 
        elif not processed_in_this_pass: # No items require retry, and nothing was processed in this pass
            _log_fs_op_message(logging.DEBUG, "No items processed and no items require retry. Exiting retry loop.", logger)
            break


    # Final pass to update stats for any items skipped due to user quitting interactively
    if user_quit_interactive:
        for tx_item_final_skip_check in transactions:
            if tx_item_final_skip_check.get("STATUS") == TransactionStatus.PENDING.value:
                update_transaction_status_in_list(transactions, tx_item_final_skip_check["id"], TransactionStatus.SKIPPED, "Operation aborted by user in interactive mode.")
        save_transactions(transactions, transactions_file_path, logger=logger)


    stats = {"completed":0,"failed":0,"skipped":0,"pending":0,"in_progress":0,"retry_later":0}
    for t in transactions:
        status_key = t.get("STATUS", TransactionStatus.PENDING.value).lower()
        stats[status_key] = stats.get(status_key, 0) + 1
    return stats
