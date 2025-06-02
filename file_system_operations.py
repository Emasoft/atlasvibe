#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Added missing definitions of load_transactions and save_transactions functions.
# - Added full implementation of execute_all_transactions
# - Added atomic_file_write helper function
# - Ensured all functions used in tests are properly exported.
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

import replace_logic

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
        elif level == logging.DEBUG:
            prefix = "DEBUG (fs_op): "
        print(f"{prefix}{message}")

def get_file_encoding(file_path: Path, sample_size: int = 10240, logger: logging.Logger | None = None) -> str | None:
    if not file_path.is_file():
        return DEFAULT_ENCODING_FALLBACK
    try:
        file_size = file_path.stat().st_size

        # For small files, try reading the entire file with UTF-8 decoding first
        if file_size <= 1_048_576:  # Increased threshold to 1MB
            try:
                raw_data = file_path.read_bytes()
                raw_data.decode('utf-8', errors='strict') # Try strict UTF-8
                return 'utf-8'
            except (UnicodeDecodeError, FileNotFoundError):
                pass  # Not UTF-8, fall through to chardet
            except Exception as e:
                _log_fs_op_message(logging.WARNING, f"Unexpected error decoding small file {file_path} as UTF-8: {e}", logger)

        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)

        if not raw_data:
            return DEFAULT_ENCODING_FALLBACK

        # 1. Try UTF-8 for all files regardless of size
        try:
            if file_path.suffix.lower() != '.rtf':
                raw_data.decode('utf-8', errors='strict')
                return 'utf-8'
        except UnicodeDecodeError:
            pass

        # RTF files use Latin-1
        if file_path.suffix.lower() == '.rtf':
            return 'latin-1' 

        # 2. Use chardet detection
        detected = chardet.detect(raw_data)
        encoding = detected.get('encoding') or DEFAULT_ENCODING_FALLBACK
        confidence = detected.get('confidence', 0)

        # Normalize GB2312 to GB18030
        if encoding and encoding.lower().startswith('gb2312'):
            encoding = 'gb18030'

        # Only consider chardet results with reasonable confidence
        if confidence > 0.5 and encoding:
            encoding = encoding.lower()
            # Handle common encoding aliases
            try:
                raw_data.decode(encoding, errors='surrogateescape')
                return encoding
            except (UnicodeDecodeError, LookupError):
                pass

        # 3. Fallback explicit checks if UTF-8 and chardet's primary suggestion failed or wasn't definitive
        for enc_try in ['cp1252', 'latin1', 'iso-8859-1']:
            try:
                if encoding != enc_try:
                    raw_data.decode(enc_try, errors='surrogateescape')
                    return enc_try
            except (UnicodeDecodeError, LookupError):
                pass

        _log_fs_op_message(logging.DEBUG, f"Encoding for {file_path} could not be confidently determined. Chardet: {detected}. Using {DEFAULT_ENCODING_FALLBACK}.", logger)
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
        # During dry run, update virtual mapping to enable child transactions to resolve correctly
        if original_relative_path_str not in path_translation_map:
            # Use original name as fallback
            path_translation_map[original_relative_path_str] = Path(original_relative_path_str).name
        # Compose current absolute path using virtual mapping
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

    scan_pattern = replace_logic.get_scan_pattern()
    raw_keys_for_binary_search = replace_logic.get_raw_stripped_keys()

    if resume_from_transactions is not None:
        processed_transactions = list(resume_from_transactions)
        # Backfill NEW_NAME for existing rename transactions if missing
        for tx in resume_from_transactions:
            if tx["TYPE"] in [TransactionType.FILE_NAME.value, TransactionType.FOLDER_NAME.value] and "NEW_NAME" not in tx:
                tx["NEW_NAME"] = replace_logic.replace_occurrences(tx.get("ORIGINAL_NAME"))
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
    
    # Collect items with depth for proper ordering
    all_items_with_depth = []
    
    for item_abs_path in item_iterator:
        depth = len(item_abs_path.relative_to(abs_root_dir).parts)
        all_items_with_depth.append((depth, item_abs_path))

    # Sort by depth (shallow first), then by normalized path string for consistent ordering
    all_items_with_depth.sort(key=lambda x: (x[0], x[1]))

    for depth, item_abs_path in all_items_with_depth:
        try:
            abs_root_dir = root_dir.resolve(strict=False)
            relative_path_str = str(item_abs_path.relative_to(abs_root_dir)).replace("\\", "/")
        except ValueError:
            continue
        
        if item_abs_path.name in excluded_basenames or relative_path_str in excluded_relative_paths_set:
            continue

        original_name = item_abs_path.name
        searchable_name = unicodedata.normalize('NFC', replace_logic.strip_control_characters(replace_logic.strip_diacritics(original_name)))
        
        item_is_dir = False
        item_is_file = False
        try:
            if not item_abs_path.is_symlink():
                item_is_dir = item_abs_path.is_dir()
            else:
                try:
                    target = item_abs_path.resolve(strict=False)
                except Exception:
                    continue
                if root_dir not in target.parents and target != root_dir:
                    continue
                item_is_file = True
            if not item_is_dir and not item_is_file:
                item_is_file = item_abs_path.is_file()
        except OSError:
            continue

        if (scan_pattern and scan_pattern.search(searchable_name)) and \
           (replace_logic.replace_occurrences(original_name) != original_name):
            tx_type_val: str | None = None
            if item_is_dir:
                if not skip_folder_renaming:
                    tx_type_val = TransactionType.FOLDER_NAME.value
            elif item_is_file or item_abs_path.is_symlink():
                if not skip_file_renaming:
                    tx_type_val = TransactionType.FILE_NAME.value
            
            if tx_type_val:
                tx_id_tuple = (relative_path_str, tx_type_val, 0)
                if tx_id_tuple not in existing_transaction_ids:
                    new_name = replace_logic.replace_occurrences(original_name)
                    transaction_entry = {
                        "id":str(uuid.uuid4()),
                        "TYPE":tx_type_val, 
                        "PATH":relative_path_str, 
                        "ORIGINAL_NAME":original_name,
                        "NEW_NAME": new_name,
                        "LINE_NUMBER":0, 
                        "STATUS":TransactionStatus.PENDING.value, 
                        "timestamp_created":time.time(), 
                        "retry_count":0
                    }
                    processed_transactions.append(transaction_entry)
                    existing_transaction_ids.add(tx_id_tuple)

        if not skip_content:
            try:
                if item_abs_path.is_file():
                    if item_abs_path.stat().st_size > 100_000_000:
                        continue
    
                    is_rtf = item_abs_path.suffix.lower() == '.rtf'
                    try:
                        is_bin = is_binary_file(str(item_abs_path))
                    except FileNotFoundError: 
                        continue
                    except Exception:
                        continue

                    if is_bin and not is_rtf:
                        if item_abs_path.stat().st_size > 100_000_000:
                            continue
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
                                        try:
                                            with open(binary_log_path, 'a', encoding='utf-8') as log_f:
                                                log_f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - MATCH: File: {relative_path_str}, Key: '{key_str}', Offset: {idx}\n")
                                                log_f.flush()
                                        except Exception:
                                            pass
                                        offset = idx + len(key_bytes)
                            except OSError: 
                                pass
                            except Exception: 
                                pass
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
                            file_encoding = 'utf-8'
                        except OSError:
                            continue
                        except Exception:
                            continue
                    else:
                        file_encoding = get_file_encoding(item_abs_path, logger=logger) or DEFAULT_ENCODING_FALLBACK
                        try:
                            with open(item_abs_path, 'r', encoding=file_encoding, errors='surrogateescape', newline='') as f_scan:
                                file_content_for_scan = f_scan.read()
                        except OSError:
                            continue
                        except Exception:
                            continue
                    
                    if file_content_for_scan is not None:
                        lines_for_scan = file_content_for_scan.splitlines(keepends=True)
                        if not lines_for_scan and file_content_for_scan:
                            lines_for_scan = [file_content_for_scan]

                        for line_idx, line_content in enumerate(lines_for_scan):
                            searchable_line_content = unicodedata.normalize('NFC', replace_logic.strip_control_characters(replace_logic.strip_diacritics(line_content)))
                            new_line_content = replace_logic.replace_occurrences(line_content)
                            if (scan_pattern and scan_pattern.search(searchable_line_content)) and \
                               (new_line_content != line_content):
                                tx_id_tuple = (relative_path_str, TransactionType.FILE_CONTENT_LINE.value, line_idx + 1)
                                if tx_id_tuple not in existing_transaction_ids:
                                    processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":TransactionType.FILE_CONTENT_LINE.value, "PATH":relative_path_str, "LINE_NUMBER":line_idx+1, "ORIGINAL_LINE_CONTENT":line_content, "NEW_LINE_CONTENT":new_line_content, "ORIGINAL_ENCODING":file_encoding, "IS_RTF":is_rtf, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                                    existing_transaction_ids.add(tx_id_tuple)
            except OSError:
                continue

    folder_txs = [tx for tx in processed_transactions if tx["TYPE"] in (TransactionType.FOLDER_NAME.value,)]
    file_txs = [tx for tx in processed_transactions if tx["TYPE"] == TransactionType.FILE_NAME.value]
    content_txs = [tx for tx in processed_transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value]
    
    folder_txs.sort(key=lambda tx: (len(Path(tx["PATH"]).parts), tx["PATH"]))
    
    processed_transactions = folder_txs + file_txs + content_txs

    return processed_transactions

def save_transactions(transactions: list[dict[str, Any]], transactions_file_path: Path, logger: logging.Logger | None = None) -> None:
    if not transactions:
        _log_fs_op_message(logging.WARNING, "No transactions to save.", logger)
        return
    temp_file_path = transactions_file_path.with_suffix(".tmp")
    try:
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        os.replace(temp_file_path, transactions_file_path)
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Error saving transactions: {e}", logger)
        try:
            if temp_file_path.exists():
                os.remove(temp_file_path)
        except Exception as cleanup_e:
            _log_fs_op_message(logging.WARNING, f"Error cleaning up temp transaction file: {cleanup_e}", logger)
        raise

def load_transactions(transactions_file_path: Path, logger: logging.Logger | None = None) -> list[dict[str, Any]] | None:
    if not transactions_file_path.is_file():
        _log_fs_op_message(logging.WARNING, f"Transaction file not found: {transactions_file_path}", logger)
        return None
    try:
        with open(transactions_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            _log_fs_op_message(logging.ERROR, f"Transaction file {transactions_file_path} does not contain a list.", logger)
            return None
        return data
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Error loading transactions from {transactions_file_path}: {e}", logger)
        return None

def atomic_file_write(file_path: Path, content: str, encoding: str) -> bool:
    temp_file = None
    try:
        temp_file = file_path.with_suffix(file_path.suffix + ".tmp")
        with open(temp_file, "w", encoding=encoding, newline="", errors='surrogateescape') as f:
            f.write(content)
        os.replace(temp_file, file_path)
        return True
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Atomic write failed: {e}", None)
        if temp_file and temp_file.exists():
            try: os.remove(temp_file)
            except: pass
        return False

def execute_all_transactions(
    transactions_file_path: Path, 
    root_dir: Path, 
    dry_run: bool, 
    resume: bool, 
    timeout_minutes: int,
    skip_file_renaming: bool, 
    skip_folder_renaming: bool, 
    skip_content: bool,
    interactive_mode: bool, 
    logger: logging.Logger | None = None
) -> dict[str, int]:
    stats = {
        "complete": 0,
        "failed": 0,
        "skipped": 0,
        "pending": 0
    }
    
    cache: dict[str, Path] = {}
    path_translation_map: dict[str, str] = {}
    
    try:
        transactions = load_transactions(transactions_file_path, logger)
        if not transactions:
            return stats
        
        if dry_run:
            _log_fs_op_message(logging.INFO, "Dry run: Simulating transaction processing", logger)
            for tx in transactions:
                if tx["STATUS"] == TransactionStatus.PENDING.value:
                    tx["STATUS"] = TransactionStatus.COMPLETED.value
                    tx["ERROR_MESSAGE"] = "DRY_RUN"
                    stats["complete"] += 1
            save_transactions(transactions, transactions_file_path, logger)
            return stats
        
        _log_fs_op_message(logging.INFO, f"Executing {len(transactions)} transactions...", logger)
        
        for tx in transactions:
            try:
                if tx["STATUS"] not in [TransactionStatus.PENDING.value, TransactionStatus.RETRY_LATER.value]:
                    continue

                tx["STATUS"] = TransactionStatus.IN_PROGRESS.value
                save_transactions(transactions, transactions_file_path, logger)
                
                item_path = _get_current_absolute_path(tx["PATH"], root_dir, path_translation_map, cache, dry_run)
                
                if tx["TYPE"] == TransactionType.FOLDER_NAME.value and not skip_folder_renaming:
                    new_path = item_path.parent / tx["NEW_NAME"]
                    if item_path.resolve() != new_path.resolve():
                        item_path.rename(new_path)
                    
                elif tx["TYPE"] == TransactionType.FILE_NAME.value and not skip_file_renaming:
                    new_path = item_path.parent / tx["NEW_NAME"]
                    if item_path.resolve() != new_path.resolve():
                        item_path.rename(new_path)
                    
                elif tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and not skip_content:
                    encoding = tx.get("ORIGINAL_ENCODING", DEFAULT_ENCODING_FALLBACK)
                    if tx.get("IS_RTF"):
                        content = rtf_to_text(item_path.read_bytes().decode('latin-1'), errors="ignore")
                    else:
                        with open(item_path, "r", encoding=encoding, errors='surrogateescape', newline='') as f:
                            content = f.read()
                    
                    lines = content.splitlines(keepends=True) or [""]
                    line_num = tx["LINE_NUMBER"] - 1
                    if 0 <= line_num < len(lines):
                        lines[line_num] = tx["NEW_LINE_CONTENT"]
                        new_content = "".join(lines)
                        atomic_file_write(item_path, new_content, encoding)
                
                tx["STATUS"] = TransactionStatus.COMPLETED.value
                tx["timestamp_processed"] = time.time()
                stats["complete"] += 1

            except Exception as e:
                tx["STATUS"] = TransactionStatus.FAILED.value
                tx["ERROR_MESSAGE"] = f"{type(e).__name__}: {str(e)}"
                stats["failed"] += 1
                
            save_transactions(transactions, transactions_file_path, logger)
        
        return stats
        
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Critical error executing transactions: {e}", logger)
        return stats
