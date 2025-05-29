#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Added dry_run parameter to _get_current_absolute_path to avoid path translation during dry run.
# - Adjusted _get_current_absolute_path to return root_dir / original_relative_path_str directly if dry_run is True.
# - Moved binary_log_path initialization to the start of scan_directory_for_occurrences to ensure correct path usage.
# - Minor fix: removed undefined variable abs_root_dir usage in scan_directory_for_occurrences.
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
        with open(ignore_file_path, 'r', encoding=DEFAULT_ENCODING_FALLBACK, errors='ignore') as f:
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
                    rel_posix = str(path_rel_to_root_for_spec).replace('\\', '/')
                    if ignore_spec.match_file(rel_posix) or \
                       (item_path_from_rglob.is_dir() and ignore_spec.match_file(rel_posix + '/')):
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
    path_translation_map: dict[str, str], cache: dict[str, Path],
    dry_run: bool = False
) -> Path:
    if dry_run:
        # During dry run, do not apply path translation map; use original path directly
        return root_dir / original_relative_path_str
    if original_relative_path_str in cache:
        return cache[original_relative_path_str]
    if original_relative_path_str == ".":
        cache["."] = root_dir
        return root_dir
    original_path_obj = Path(original_relative_path_str)
    parent_rel_str = "." if original_path_obj.parent == Path('.') else str(original_path_obj.parent)
    current_parent_abs_path = _get_current_absolute_path(parent_rel_str, root_dir, path_translation_map, cache, dry_run)
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

    binary_log_path = root_dir / BINARY_MATCHES_LOG_FILE

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

# ... rest of file_system_operations.py unchanged ...
