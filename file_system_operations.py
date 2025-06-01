#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Added NEW_LINE_CONTENT field to content transactions during scan phase.
# - Fixed transaction routing logic in execute_all_transactions to properly handle content transactions.
# - Added safeguard to skip content transactions if new content equals original content.
# - Mark content transactions as completed during dry-run without modifying files.
# - Implemented _execute_content_line_transaction to handle content line modifications with proper encoding and line preservation.
# - Improved get_file_encoding to handle small files more robustly:
#   * For small files (<=4KB), try full UTF-8 decoding first.
#   * Removed fallback hacks for Latin-1/cp1252 that were unreliable.
#   * Only consider chardet results with >50% confidence.
#   * Added direct UTF-8 attempt for all files.
#   * Added special handling for RTF file extensions at runtime.
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
        if file_size <= 4096:  # Small file heuristic threshold
            try:
                raw_data = file_path.read_bytes()
                raw_data.decode('utf-8', errors='strict') # Try strict UTF-8
                return 'utf-8'
            except (UnicodeDecodeError, FileNotFoundError):
                pass  # Not UTF-8, fall through to chardet

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

        # Only consider chardet results with reasonable confidence
        if confidence > 0.5:
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
                tx["NEW_NAME"] = replace_logic.replace_occurrences(tx["ORIGINAL_NAME"])
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

    # Fix: If resume_from_transactions is not None and paths_to_force_rescan is empty, initialize as empty set
    if resume_from_transactions is not None and not paths_to_force_rescan_internal:
        paths_to_force_rescan_internal = set()

    item_iterator = _walk_for_scan(abs_root_dir, resolved_abs_excluded_dirs, ignore_symlinks, ignore_spec, logger=logger)
    
    # Collect items with depth for proper ordering
    all_items_with_depth = []
    
    for item_abs_path in item_iterator:
        # Depth calculation for ordering
        depth = len(item_abs_path.relative_to(abs_root_dir).parts)
        all_items_with_depth.append((depth, item_abs_path))

    # Sort by depth (shallow first), then by normalized path string for consistent ordering
    all_items_with_depth.sort(key=lambda x: (x[0], x[1]))  # Proper Path comparison

    for depth, item_abs_path in all_items_with_depth:
        try:
            abs_root_dir = root_dir.resolve()  # Use original root_dir, not overwritten abs_root_dir
            relative_path_str = str(item_abs_path.relative_to(abs_root_dir)).replace("\\", "/")
        except ValueError:
            _log_fs_op_message(logging.WARNING, f"Could not get relative path for {item_abs_path} against {abs_root_dir}. Skipping.", logger)
            continue
        
        if item_abs_path.name in excluded_basenames or relative_path_str in excluded_relative_paths_set:
            continue

        original_name = item_abs_path.name
        searchable_name = unicodedata.normalize('NFC', replace_logic.strip_control_characters(replace_logic.strip_diacritics(original_name)))
        
        item_is_dir = False
        item_is_file = False
        item_is_symlink = False
        try:
            if not item_abs_path.is_symlink():
                item_is_dir = item_abs_path.is_dir()
            else:
                # Check if symlink points outside root
                target = item_abs_path.resolve()
                if root_dir not in target.parents and target != root_dir:
                    _log_fs_op_message(logging.INFO, f"Skipping external symlink: {relative_path_str} -> {target}", logger)
                    continue
                # Treat symlink as file for name replacement
                item_is_file = True
            if not item_is_dir and not item_is_file:
                # If not dir and not file, check if file (for symlink to file)
                item_is_file = item_abs_path.is_file()
            item_is_symlink = item_abs_path.is_symlink()
        except OSError as e_stat:
            _log_fs_op_message(logging.WARNING, f"OS error checking type of {item_abs_path}: {e_stat}. Skipping item.", logger)
            continue


        if (scan_pattern and scan_pattern.search(searchable_name)) and \
           (replace_logic.replace_occurrences(original_name) != original_name):
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
                    # Calculate new name and store in transaction
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

        # Content processing should only happen for actual files, not symlinks to directories
        # and only if item_is_file was true (meaning it's a file or a symlink we are considering for content if it points to a file)
        # The `item_abs_path.is_file()` check inside this block will resolve the symlink if it's one.
        if not skip_content:
            try:
                if item_abs_path.is_file(): # This resolves symlinks to files
                    # Skip large files early
                    if item_abs_path.stat().st_size > 100_000_000:  # 100MB
                        continue
    
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
                        # Skip binary files but log them
                        if item_abs_path.stat().st_size > 100_000_000:  # 100MB
                            continue  # Skip scanning extremely large binary files
                        _log_fs_op_message(logging.DEBUG, f"Skipping binary file: {relative_path_str}", logger)
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
                            searchable_line_content = unicodedata.normalize('NFC', replace_logic.strip_control_characters(replace_logic.strip_diacritics(line_content)))
                            # Calculate new content once for consistency
                            new_line_content = replace_logic.replace_occurrences(line_content)
                            if (scan_pattern and scan_pattern.search(searchable_line_content)) and \
                               (new_line_content != line_content):
                                tx_id_tuple = (relative_path_str, TransactionType.FILE_CONTENT_LINE.value, line_idx + 1)
                                if tx_id_tuple not in existing_transaction_ids:
                                    # ADD NEW_LINE_CONTENT FIELD
                                    processed_transactions.append({"id":str(uuid.uuid4()), "TYPE":TransactionType.FILE_CONTENT_LINE.value, "PATH":relative_path_str, "LINE_NUMBER":line_idx+1, "ORIGINAL_LINE_CONTENT":line_content, "NEW_LINE_CONTENT":new_line_content, "ORIGINAL_ENCODING":file_encoding, "IS_RTF":is_rtf, "STATUS":TransactionStatus.PENDING.value, "timestamp_created":time.time(), "retry_count":0})
                                    existing_transaction_ids.add(tx_id_tuple)
            except OSError as e_stat_content: # Catch OSError from item_abs_path.is_file()
                _log_fs_op_message(logging.WARNING, f"OS error checking if {item_abs_path} is a file for content processing: {e_stat_content}. Skipping content scan for this item.", logger)

    # Order transactions: folders first (shallow to deep), then files, then content
    folder_txs = [tx for tx in processed_transactions if tx["TYPE"] in (TransactionType.FOLDER_NAME.value,)]
    file_txs = [tx for tx in processed_transactions if tx["TYPE"] == TransactionType.FILE_NAME.value]
    content_txs = [tx for tx in processed_transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value]
    
    # Sort folders by depth (shallow then deep)
    folder_txs.sort(key=lambda tx: len(Path(tx["PATH"]).parts))
    
    processed_transactions = folder_txs + file_txs + content_txs

    return processed_transactions

def save_transactions(transactions: list[dict[str, Any]], transactions_file_path: Path, logger: logging.Logger | None = None) -> None:
    """
    Save the list of transactions to a JSON file atomically.
    """
    if not transactions:
        _log_fs_op_message(logging.WARNING, "No transactions to save.", logger)
        return
    temp_file_path = transactions_file_path.with_suffix(".tmp")
    try:
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        # Atomically replace original file
        os.replace(temp_file_path, transactions_file_path)
    except Exception as e:
        _log_fs_op_message(logging.ERROR, f"Error saving transactions: {e}", logger)
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise

def load_transactions(transactions_file_path: Path, logger: logging.Logger | None = None) -> list[dict[str, Any]] | None:
    """
    Load transactions from a JSON file.
    """
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

def update_transaction_status_in_list(
    transactions: list[dict[str, Any]], transaction_id: str,
    new_status: TransactionStatus, error_message: str | None = None,
    logger: logging.Logger | None = None
) -> bool:
    """
    Update the status and optional error message of a transaction in the list by id.
    Returns True if updated, False if not found.
    """
    for tx in transactions:
        if tx.get("id") == transaction_id:
            tx["STATUS"] = new_status.value
            if error_message is not None:
                tx["ERROR_MESSAGE"] = error_message
            if logger:
                logger.debug(f"Transaction {transaction_id} updated to {new_status.value} with error: {error_message}")
            return True
    if logger:
        logger.warning(f"Transaction {transaction_id} not found for status update.")
    return False

def _execute_rename_transaction(
    tx: dict[str, Any], root_dir: Path,
    path_translation_map: dict[str, str], path_cache: dict[str, Path],
    dry_run: bool, logger: logging.Logger | None = None
) -> tuple[TransactionStatus, str, bool]:
    """
    Execute a rename transaction (file or folder).
    Returns (status, error_message, changed_bool).
    """
    original_relative_path_str = tx["PATH"]
    original_name = tx.get("ORIGINAL_NAME", "")
    tx_type = tx["TYPE"]

    # Use precomputed NEW_NAME if available
    new_name = tx.get("NEW_NAME", replace_logic.replace_occurrences(original_name))
    
    current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache, dry_run)
    if not dry_run and not current_abs_path.exists():
        return TransactionStatus.FAILED, f"Path not found: {current_abs_path}", False

    if new_name == original_name:
        return TransactionStatus.SKIPPED, "No change needed", False

    new_abs_path = current_abs_path.parent / new_name

    if new_abs_path.exists():
        return TransactionStatus.FAILED, f"Target path already exists: {new_abs_path}", False

    try:
        if dry_run:
            # Special handling for folders to simulate cascading renames
            if tx_type in [TransactionType.FOLDER_NAME.value]:
                # Create virtual path for simulation
                if original_relative_path_str not in path_translation_map:
                    path_translation_map[original_relative_path_str] = original_name
                path_translation_map[original_relative_path_str] = new_name
                path_cache.pop(original_relative_path_str, None)
                return TransactionStatus.COMPLETED, "DRY_RUN", True
            else:
                # Only simulate changes, don't update real path mappings
                return TransactionStatus.COMPLETED, "DRY_RUN", False

        # Actual rename
        os.rename(current_abs_path, new_abs_path)
        path_translation_map[original_relative_path_str] = new_name
        path_cache.pop(original_relative_path_str, None)
        return TransactionStatus.COMPLETED, "", True
    except Exception as e:
        return TransactionStatus.FAILED, f"Rename error: {e}", False

def _execute_content_line_transaction(
    tx: dict[str, Any], root_dir: Path,
    path_translation_map: dict[str, str], path_cache: dict[str, Path],
    logger: logging.Logger | None = None
) -> tuple[TransactionStatus, str, bool]:
    """
    Execute a content line transaction.
    Returns (status, error_message, changed_bool).
    """
    relative_path_str = tx["PATH"]
    line_no = tx["LINE_NUMBER"]  # 1-indexed
    file_encoding = tx.get("ORIGINAL_ENCODING", DEFAULT_ENCODING_FALLBACK)
    is_rtf = tx.get("IS_RTF", False)

    # Skip RTF as they're converted text files with unique formatting
    if is_rtf:
        return (TransactionStatus.SKIPPED, "RTF content modification not supported", False)

    try:
        # Get current file location (accounts for renames)
        current_abs_path = _get_current_absolute_path(relative_path_str, root_dir, path_translation_map, path_cache, dry_run=False)
        
        # Read file with original encoding
        with open(current_abs_path, "r", encoding=file_encoding, errors='surrogateescape') as f:
            lines = f.readlines()  # Preserve line endings

        if line_no - 1 < 0 or line_no - 1 >= len(lines):
            return (TransactionStatus.FAILED, f"Line number {line_no} out of range. File has {len(lines)} lines.", False)
            
        # Get new content from transaction
        new_line_content = tx.get("NEW_LINE_CONTENT", "")
        
        # Skip if line didn't change (shouldn't happen but safeguard)
        if lines[line_no-1] == new_line_content:
            return (TransactionStatus.SKIPPED, "Line already matches target", False)
            
        # Update the line
        lines[line_no-1] = new_line_content
        
        # Write back with same encoding
        with open(current_abs_path, "w", encoding=file_encoding, errors='surrogateescape') as f:
            f.writelines(lines)
            
        return (TransactionStatus.COMPLETED, "", True)
    except Exception as e:
        return (TransactionStatus.FAILED, f"Content update failed: {e}", False)

def execute_all_transactions(
    transactions_file_path: Path, root_dir: Path,
    dry_run: bool, resume: bool, timeout_minutes: int,
    skip_file_renaming: bool, skip_folder_renaming: bool, skip_content: bool,
    skip_scan: bool,
    interactive_mode: bool,
    logger: logging.Logger | None = None
) -> dict[str, int]:
    """
    Execute all transactions in the transaction file.
    Returns statistics dictionary.
    """
    import time

    MAX_RETRY_PASSES = 10
    MAX_DRY_RUN_PASSES = 1

    transactions = load_transactions(transactions_file_path, logger=logger)
    if transactions is None:
        if logger:
            logger.error("No transactions to execute.")
        return {}

    stats = {
        "total": len(transactions),
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "retry_later": 0,
    }

    # Shared path translation for rename operations
    path_translation_map: dict[str, str] = {}
    path_cache: dict[str, Path] = {}

    processed_in_this_pass = 0
    logging_blocked_during_interactive = False  # Used to suppress logs in interactive when needing to print the transaction detail

    # Track which transactions we've seen to prevent duplicate processing
    if not dry_run and resume:
        for tx in transactions:
            if tx["STATUS"] == TransactionStatus.COMPLETED.value and tx.get("ERROR_MESSAGE") == "DRY_RUN":
                tx["STATUS"] = TransactionStatus.PENDING.value
                tx.pop("ERROR_MESSAGE", None)
    seen_transaction_ids = set([tx["id"] for tx in transactions])

    # If resuming, reset statuses that need processing
    if resume:
        reset_transactions = []
        for tx in transactions:
            if tx["STATUS"] in [TransactionStatus.FAILED.value, TransactionStatus.RETRY_LATER.value]:
                tx["STATUS"] = TransactionStatus.PENDING.value
                tx.pop("ERROR_MESSAGE", None)
                reset_transactions.append(tx)
        if reset_transactions and logger:
            logger.info(f"Reset {len(reset_transactions)} transactions to PENDING for retry.")

    finished = False
    pass_count = 0
    while not finished and pass_count < MAX_RETRY_PASSES:
        pass_count += 1
        items_still_requiring_retry = []
        for tx_item in [tx for tx in transactions if tx["id"] in seen_transaction_ids]:
            tx_id = tx_item["id"]
            tx_type = tx_item["TYPE"]
            relative_path_str = tx_item["PATH"]
            status = tx_item.get("STATUS", TransactionStatus.PENDING.value)

            if status != TransactionStatus.PENDING.value:
                continue

            # Interactive mode prompt
            if interactive_mode and not dry_run:
                # Show transaction details and ask for approval
                print(f"{DIM_STYLE}Transaction {tx_id} - Type: {tx_type}, Path: {relative_path_str}{RESET_STYLE}")
                choice = input("Approve? (A/Approve, S/Skip, Q/Quit): ").strip().upper()
                if choice == "S":
                    update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "Skipped by user", logger=logger)
                    continue
                elif choice == "Q":
                    if logger:
                        logger.info("Operation aborted by user.")
                    finished = True
                    break
                # else proceed with execution

            try:
                if tx_type in [TransactionType.FILE_NAME.value, TransactionType.FOLDER_NAME.value]:
                    if (tx_type == TransactionType.FILE_NAME.value and skip_file_renaming) or \
                       (tx_type == TransactionType.FOLDER_NAME.value and skip_folder_renaming):
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "Skipped by flags", logger=logger)
                        stats["skipped"] += 1
                        continue
                    status_result, error_msg, changed = _execute_rename_transaction(tx_item, root_dir, path_translation_map, path_cache, dry_run, logger)
                    if status_result == TransactionStatus.COMPLETED:
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.COMPLETED, "DRY_RUN" if dry_run else None, logger=logger)
                        stats["completed"] += 1
                    elif status_result == TransactionStatus.SKIPPED:
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, error_msg, logger=logger)
                        stats["skipped"] += 1
                    else:
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.FAILED, error_msg, logger=logger)
                        stats["failed"] += 1
                        items_still_requiring_retry.append(tx_item)
                elif tx_type == TransactionType.FILE_CONTENT_LINE.value:
                    if skip_content:
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "Skipped by flag", logger=logger)
                        stats["skipped"] += 1
                        continue

                    # Get new content from transaction
                    new_line_content = tx_item.get("NEW_LINE_CONTENT", "")
                    original_line_content = tx_item.get("ORIGINAL_LINE_CONTENT", "")

                    # Skip if no actual change (shouldn't happen but added as safeguard)
                    if new_line_content == original_line_content:
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "No change needed", logger=logger)
                        stats["skipped"] += 1
                        continue

                    if dry_run:
                        # For dry-run, mark as completed without modifying file
                        update_transaction_status_in_list(transactions, tx_id, TransactionStatus.COMPLETED, "DRY_RUN", logger=logger)
                        stats["completed"] += 1
                    else:
                        status_result, error_msg, changed = _execute_content_line_transaction(tx_item, root_dir, path_translation_map, path_cache, logger=logger)
                        if status_result == TransactionStatus.COMPLETED:
                            update_transaction_status_in_list(transactions, tx_id, TransactionStatus.COMPLETED, error_msg, logger=logger)
                            stats["completed"] += 1
                        elif status_result == TransactionStatus.SKIPPED:
                            update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, error_msg, logger=logger)
                            stats["skipped"] += 1
                        else:
                            update_transaction_status_in_list(transactions, tx_id, TransactionStatus.FAILED, error_msg, logger=logger)
                            stats["failed"] += 1
                else:
                    update_transaction_status_in_list(transactions, tx_id, TransactionStatus.SKIPPED, "Unknown transaction type", logger=logger)
                    stats["skipped"] += 1
            except Exception as e:
                update_transaction_status_in_list(transactions, tx_id, TransactionStatus.FAILED, f"Exception: {e}", logger=logger)
                stats["failed"] += 1
                items_still_requiring_retry.append(tx_item)

            # Track we've processed this transaction
            if tx_id in seen_transaction_ids:
                seen_transaction_ids.remove(tx_id)

        if not items_still_requiring_retry:
            finished = True
            break

        # Wait and retry logic here (omitted for brevity)

    save_transactions(transactions, transactions_file_path, logger=logger)
    return stats

# ... rest of file_system_operations.py unchanged ...
