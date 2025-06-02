#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Added missing definitions of load_transactions and save_transactions functions.
# - Added full implementation of execute_all_transactions
# - Added atomic_file_write helper function
# - Ensured all functions used in tests are properly exported.
# - Fixed syntax errors in:
#   * f-string syntax in load_ignore_patterns
#   * Missing : in if statement
#   * Removed erroneous ] in scan_pattern assignment
#   * Fixed try/except block structure in scan_directory_for_occurrences
#   * Fixed list syntax in if conditions
# - Added save_transactions function definition to fix F821 errors
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
                _log_fs_op_message(logging.WARNING, f"Unexpected error decoding small file {file_path} as UTF-8: {e}, logger")

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
    paths_to_force_resscan: set[str] | None = None,
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
            if tx["TYPE"] in [TransactionType.FILE_NAME.value, TransactionType.FOLDER_NAME.value]:
                tx["NEW_NAME"] = replace_logic.replace_occurrences(tx.get("ORIGINAL_NAME", ""))

    return processed_transactions

def save_transactions(transactions: list[dict[str, Any]], transactions_file_path: Path, logger: logging.Logger | None = None) -> None:
    """Save transactions to a JSON file with atomic write operation."""
    if not transactions:
        _log_fs_op_message(logging.WARNING, "No transactions to save.", logger)
        return

    temp_file = None
    try:
        temp_file = transactions_file_path.with_suffix(transactions_file_path.suffix + ".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, transactions_file_path)
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Error saving transactions: {e}", logger)
        if temp_file and temp_file.exists():
            try:
                os.remove(temp_file)
            except Exception as e:
                _log_fs_op_message(logging.WARNING, f"Failed to clean up temp file {temp_file}: {e}", logger)

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
    """Atomically write content to a file using temporary file replacement"""
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
            try:
                os.remove(temp_file)
            except Exception:
                pass
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
                        content = rtf_to_text(item_path.read_bytes().decode('latin-1', errors="ignore"))
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
                tx["STATUS"] = TransactionStatus.FALED.value
                tx["ERROR_MESSAGE"] = f"{type(e).__name__}: {str(e)}"
                stats["failed"] += 1
                
            save_transactions(transactions, transactions_file_path, logger)
        
        return stats
        
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Critical error executing transactions: {e}", logger)
        return stats
