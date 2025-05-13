# file_system_operations.py
# -*- coding: utf-8 -*-
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
import time # For retry delay

from replace_logic import replace_occurrences 

# --- Custom Exception ---
class SandboxViolationError(Exception):
    """Custom exception for operations attempting to escape the sandbox."""
    pass

class MockableRetriableError(OSError): # Custom error for testing retries
    """A custom OSError subclass that can be specifically caught for retries in tests."""
    pass

# --- Constants & Enums ---
DEFAULT_ENCODING_FALLBACK = 'utf-8'
TRANSACTION_FILE_BACKUP_EXT = ".bak"
MAX_RENAME_RETRIES = 1 
RETRY_DELAY_SECONDS = 0.1 
SELF_TEST_ERROR_FILE_BASENAME = "error_file_flojoy.txt" # For simulating errors

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


def get_file_encoding(file_path: Path, sample_size: int = 10240) -> Optional[str]:
    """Detects file encoding using chardet."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
        if not raw_data:
            return DEFAULT_ENCODING_FALLBACK 
        detected = chardet.detect(raw_data)
        encoding: Optional[str] = detected.get('encoding')
        confidence: float = detected.get('confidence', 0.0)

        if encoding and confidence and confidence > 0.7:
            norm_encoding = encoding.lower()
            if norm_encoding == 'ascii':
                return 'ascii'
            if 'utf-8' in norm_encoding or 'utf8' in norm_encoding:
                return 'utf-8'
            try:
                b"test".decode(encoding)
                return encoding
            except LookupError:
                return DEFAULT_ENCODING_FALLBACK 
        else:
            try:
                raw_data.decode('utf-8')
                return 'utf-8'
            except UnicodeDecodeError:
                return DEFAULT_ENCODING_FALLBACK 
    except Exception: 
        return DEFAULT_ENCODING_FALLBACK 

def is_likely_binary_file(file_path: Path, sample_size: int = 1024) -> bool:
    """Heuristic to check if a file is likely binary."""
    try:
        # Important: Check if it's a symlink first. If so, check the target.
        # However, for binary detection, we should operate on what open() would operate on.
        # If it's a broken symlink, open() will fail.
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)
        if not sample:
            return False
        if b'\x00' in sample:
            return True
        text_chars = bytes(range(32, 127)) + b'\n\r\t\f\v' 
        non_text_count = sum(1 for byte in sample if byte not in text_chars)
        if len(sample) > 0 and (non_text_count / len(sample)) > 0.3:
            return True
        return False
    except Exception:
        return True 

def _walk_for_scan(root_dir: Path, excluded_dirs: List[str]) -> Iterator[Path]:
    """
    Yields paths for scanning, respecting exclusions.
    By default, Path.rglob does not follow symlinks for directory traversal.
    """
    abs_excluded_dirs = [root_dir.joinpath(d).resolve(strict=False) for d in excluded_dirs]
    for item_path in root_dir.rglob("*"): # rglob itself does not follow symlinks into dirs
        is_excluded = False
        try:
            resolved_item_path = item_path.resolve(strict=False) # Resolves symlinks for comparison
            for excluded_dir in abs_excluded_dirs:
                # Check if the resolved path is the excluded dir or within an excluded dir
                if resolved_item_path == excluded_dir or excluded_dir in resolved_item_path.parents:
                    is_excluded = True
                    break
        except (ValueError, OSError, FileNotFoundError): 
            # Fallback for paths that might be problematic to resolve (e.g., very long, broken symlinks)
            item_path_str = str(item_path)
            if any(item_path_str.startswith(str(ex_dir)) for ex_dir in abs_excluded_dirs):
                 is_excluded = True
        
        if is_excluded:
            # If a directory is excluded, rglob would have already skipped its contents.
            # This primarily handles cases where an excluded item is directly yielded by rglob.
            continue 
        yield item_path

def _get_current_absolute_path(
    original_relative_path_str: str,
    root_dir: Path,
    path_translation_map: Dict[str, str], 
    cache: Dict[str, Path] 
) -> Path:
    if original_relative_path_str == ".": 
        cache["."] = root_dir
        return root_dir

    original_path_obj = Path(original_relative_path_str)
    if original_path_obj.parent == Path('.'):
        original_parent_rel_str = "."
    else:
        original_parent_rel_str = str(original_path_obj.parent)

    item_original_name = original_path_obj.name

    current_parent_abs_path = _get_current_absolute_path(
        original_parent_rel_str, root_dir, path_translation_map, cache
    )

    current_item_name = path_translation_map.get(original_relative_path_str, item_original_name)
    current_abs_path = current_parent_abs_path / current_item_name
    cache[original_relative_path_str] = current_abs_path
    return current_abs_path

def scan_directory_for_occurrences(
    root_dir: Path,
    excluded_dirs: List[str],
    excluded_files: List[str],
    file_extensions: Optional[List[str]],
    resume_from_transactions: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:

    processed_transactions: List[Dict[str, Any]]
    existing_transaction_ids: Set[Tuple[str, str, int]] = set()

    if resume_from_transactions is not None:
        processed_transactions = list(resume_from_transactions) 
        for tx in processed_transactions:
            tx_type = tx.get("TYPE")
            tx_path = tx.get("PATH")
            tx_line = tx.get("LINE_NUMBER", 0) 
            if tx_type is not None and tx_path is not None:
                existing_transaction_ids.add((tx_path, tx_type, tx_line))
            else:
                 print(f"Warning: Skipping invalid transaction during resume: {tx}")
    else:
        processed_transactions = []

    abs_excluded_files = [root_dir.joinpath(f).resolve(strict=False) for f in excluded_files]
    normalized_extensions = {ext.lower() for ext in file_extensions} if file_extensions else None
    all_items_for_scan = list(_walk_for_scan(root_dir, excluded_dirs))
    sorted_items = sorted(all_items_for_scan, key=str)

    for item_path in sorted_items:
        try:
            relative_path_str = str(item_path.relative_to(root_dir)).replace("\\", "/")
        except ValueError:
            print(f"Warning: Could not get relative path for {item_path}. Skipping.")
            continue

        original_name = item_path.name

        try:
            # For exclusion, we need to check the resolved path if it's a symlink
            # However, item_path itself is what rglob yields (the link, not target for dirs)
            path_to_check_exclusion = item_path.resolve(strict=False) if item_path.is_symlink() else item_path
            if path_to_check_exclusion in abs_excluded_files:
                continue
        except (OSError, FileNotFoundError): # Handle broken symlinks or other resolution issues
             item_path_str = str(item_path)
             if any(str(ex_file) == item_path_str for ex_file in abs_excluded_files): # Check original path string
                  continue
        
        # Process name of the item (file, dir, or symlink itself)
        if replace_occurrences(original_name) != original_name: 
            # Use lstat to determine type without following symlinks for this decision
            # item_path.is_dir() / is_file() would follow symlinks.
            # For transaction type, we care about what the item *is* in the listing, not what it points to.
            is_dir = item_path.is_dir() and not item_path.is_symlink() # True directory
            is_file = item_path.is_file() and not item_path.is_symlink() # True file
            # Symlinks themselves are neither is_dir() nor is_file() in a strict sense if we use lstat-like checks.
            # However, for naming, they act like files.
            
            tx_type_val = TransactionType.FOLDER_NAME.value if is_dir else TransactionType.FILE_NAME.value
            
            current_tx_id_tuple = (relative_path_str, tx_type_val, 0) 

            if current_tx_id_tuple not in existing_transaction_ids:
                processed_transactions.append({
                    "id": str(uuid.uuid4()), "TYPE": tx_type_val, "PATH": relative_path_str,
                    "ORIGINAL_NAME": original_name, "LINE_NUMBER": 0,
                    "ORIGINAL_LINE_CONTENT": None, "PROPOSED_LINE_CONTENT": None, 
                    "ORIGINAL_ENCODING": None, "STATUS": TransactionStatus.PENDING.value,
                    "ERROR_MESSAGE": None
                })
                existing_transaction_ids.add(current_tx_id_tuple)

        # Content processing: only for actual files, not symlinks to files, and not directories.
        if item_path.is_file() and not item_path.is_symlink():
            if is_likely_binary_file(item_path): # This will open the actual file
                continue
            if normalized_extensions and item_path.suffix.lower() not in normalized_extensions:
                continue

            file_encoding = get_file_encoding(item_path) 
            try:
                with open(item_path, 'r', encoding=file_encoding, errors='surrogateescape', newline=None) as f:
                    for line_num_0_indexed, line_content in enumerate(f):
                        if replace_occurrences(line_content) != line_content: 
                            line_number_1_indexed = line_num_0_indexed + 1
                            current_tx_id_tuple = (relative_path_str, TransactionType.FILE_CONTENT_LINE.value, line_number_1_indexed)

                            if current_tx_id_tuple not in existing_transaction_ids:
                                processed_transactions.append({
                                    "id": str(uuid.uuid4()), "TYPE": TransactionType.FILE_CONTENT_LINE.value,
                                    "PATH": relative_path_str, "ORIGINAL_NAME": None, 
                                    "LINE_NUMBER": line_number_1_indexed, "ORIGINAL_LINE_CONTENT": line_content, 
                                    "PROPOSED_LINE_CONTENT": None, "ORIGINAL_ENCODING": file_encoding,
                                    "STATUS": TransactionStatus.PENDING.value, "ERROR_MESSAGE": None
                                })
                                existing_transaction_ids.add(current_tx_id_tuple)
            except UnicodeDecodeError as ude:
                 print(f"Warning: UnicodeDecodeError reading {item_path} with encoding {file_encoding} (using errors='surrogateescape'). Skipping content scan. Error: {ude}")
            except Exception as e:
                print(f"Warning: Could not read/process content of file {item_path} with encoding {file_encoding}: {e}")
                pass 
    return processed_transactions

def load_transactions(json_file_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Loads transactions, trying backup if primary fails."""
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    paths_to_try = [json_file_path, backup_path]
    loaded_data = None
    for path in paths_to_try:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                if isinstance(loaded_data, list):
                    print(f"Successfully loaded transactions from {path}")
                    return cast(List[Dict[str, Any]], loaded_data)
                else:
                    print(f"Warning: Invalid format in {path}. Expected a list.")
                    loaded_data = None 
            except json.JSONDecodeError as jde:
                print(f"Warning: Failed to decode JSON from {path}: {jde}")
            except Exception as e:
                print(f"Warning: Failed to load transactions from {path}: {e}")
    if loaded_data is None:
         print(f"Error: Could not load valid transactions from {json_file_path} or its backup.")
    return None

def save_transactions(transactions: List[Dict[str, Any]], json_file_path: Path) -> None:
    """Saves transactions, creating a backup first."""
    if json_file_path.exists():
        backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
        try:
            shutil.copy2(json_file_path, backup_path)
        except Exception as e:
            print(f"Warning: Could not create backup of {json_file_path} to {backup_path}: {e}")
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=4) 
    except Exception as e:
        print(f"Error: Could not save transactions to {json_file_path}: {e}")
        raise 

def update_transaction_status_in_list(
    transactions: List[Dict[str, Any]],
    transaction_id: str,
    new_status: TransactionStatus,
    error_message: Optional[str] = None,
    proposed_content: Optional[str] = None 
) -> bool:
    """Updates the status and optionally error message/proposed content of a transaction in the list."""
    updated = False
    for tx_item in transactions:
        if tx_item['id'] == transaction_id:
            tx_item['STATUS'] = new_status.value
            if error_message:
                tx_item['ERROR_MESSAGE'] = error_message
            else:
                if new_status != TransactionStatus.FAILED:
                    tx_item.pop('ERROR_MESSAGE', None)
            if proposed_content is not None and tx_item['TYPE'] == TransactionType.FILE_CONTENT_LINE.value:
                 tx_item['PROPOSED_LINE_CONTENT'] = proposed_content

            updated = True
            break
    return updated

def _ensure_within_sandbox(path_to_check: Path, sandbox_root: Path, operation_desc: str):
    """Checks if a path is within the sandbox_root. Raises SandboxViolationError if not."""
    try:
        resolved_path = path_to_check.resolve()
        resolved_sandbox_root = sandbox_root.resolve()
        if not resolved_path.is_relative_to(resolved_sandbox_root) and resolved_path != resolved_sandbox_root :
            raise SandboxViolationError(
                f"Operation '{operation_desc}' on path '{resolved_path}' is outside the sandbox '{resolved_sandbox_root}'."
            )
    except (OSError, FileNotFoundError) as e:
         raise SandboxViolationError(
             f"Could not resolve path '{path_to_check}' for sandbox check during operation '{operation_desc}'. Error: {e}"
         ) from e


def _execute_rename_transaction(
    tx_item: Dict[str, Any],
    root_dir: Path,
    path_translation_map: Dict[str, str],
    path_cache: Dict[str, Path],
    dry_run: bool
) -> Tuple[TransactionStatus, Optional[str]]:
    """Executes a single file or folder rename transaction."""
    original_relative_path_str = tx_item["PATH"]
    original_name = tx_item["ORIGINAL_NAME"]

    try:
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)
    except FileNotFoundError:
         return TransactionStatus.SKIPPED, f"Parent path for '{original_relative_path_str}' not found (likely due to prior failed rename or path resolution issue)."
    except Exception as e:
         return TransactionStatus.FAILED, f"Error resolving current path for '{original_relative_path_str}': {e}"

    # For symlinks, current_abs_path is the link itself. os.rename works on the link.
    # We must ensure the link exists, not necessarily its target for the rename op itself.
    if not current_abs_path.exists() and not current_abs_path.is_symlink(): # For symlinks, exists() checks target. lexists() checks link.
        if not os.path.lexists(current_abs_path): # Check if link itself is missing
            potential_new_name = replace_occurrences(original_name) 
            potential_new_path = current_abs_path.with_name(potential_new_name)
            if os.path.lexists(potential_new_path): # Check if new link name exists
                return TransactionStatus.SKIPPED, f"Original link '{current_abs_path}' not found, but target link name '{potential_new_path}' exists (already processed?)."
            else:
                return TransactionStatus.SKIPPED, f"Original link '{current_abs_path}' not found and target link name does not exist either."

    new_name = replace_occurrences(original_name) 
    if new_name == original_name:
        return TransactionStatus.SKIPPED, "Name unchanged after replacement."

    new_abs_path = current_abs_path.with_name(new_name)

    if not dry_run and original_name == SELF_TEST_ERROR_FILE_BASENAME:
        print(f"INFO: Simulating rename failure for self-test file: {original_name}")
        return TransactionStatus.FAILED, "Simulated permission error for self-test"

    if dry_run:
        print(f"[DRY RUN] Would rename '{current_abs_path}' to '{new_abs_path}'")
        path_translation_map[original_relative_path_str] = new_name
        path_cache[original_relative_path_str] = new_abs_path
        return TransactionStatus.COMPLETED, "DRY_RUN"

    for attempt in range(MAX_RENAME_RETRIES + 1):
        try:
            _ensure_within_sandbox(current_abs_path, root_dir, f"rename source for {original_name}")
            _ensure_within_sandbox(new_abs_path, root_dir, f"rename destination for {new_name}")

            if os.path.lexists(new_abs_path): # Use lstat to check if new link name exists
                 try:
                     # If current_abs_path is a symlink, resolve() follows it.
                     # We need to compare if the new_abs_path would overwrite a *different* existing file/dir/link.
                     # This logic might need refinement if new_abs_path could be a dir and current_abs_path a file or vice-versa.
                     # For now, simple check: if new_abs_path exists and isn't the same inode as current_abs_path (if not a symlink)
                     if not current_abs_path.is_symlink() and not new_abs_path.is_symlink():
                         if not current_abs_path.resolve().samefile(new_abs_path.resolve()): 
                             return TransactionStatus.SKIPPED, f"Target path '{new_abs_path}' already exists and is a different item."
                     # If new_abs_path exists and is a symlink, it's complex. For now, assume skip if exists.
                     elif os.path.lexists(new_abs_path) and not (current_abs_path.is_symlink() and os.readlink(current_abs_path) == os.readlink(new_abs_path)):
                          return TransactionStatus.SKIPPED, f"Target symlink path '{new_abs_path}' already exists and points to a different target or is a different type of item."

                 except FileNotFoundError: # Can happen if current_abs_path is a broken symlink
                      pass 
                 except OSError as ose:
                      return TransactionStatus.FAILED, f"Error checking if paths are same file: {ose}"

            os.rename(current_abs_path, new_abs_path) # os.rename renames the symlink itself, not the target
            path_translation_map[original_relative_path_str] = new_name
            path_cache[original_relative_path_str] = new_abs_path 
            return TransactionStatus.COMPLETED, None 
        except MockableRetriableError as mre: 
            if attempt < MAX_RENAME_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue 
            else: 
                return TransactionStatus.FAILED, f"Retriable error persisted after {MAX_RENAME_RETRIES + 1} attempts: {mre}"
        except SandboxViolationError as sve:
            return TransactionStatus.FAILED, f"SandboxViolation: {sve}"
        except OSError as e: 
            if attempt < MAX_RENAME_RETRIES:
                 print(f"Warning: Rename attempt {attempt + 1} failed: {e}. Retrying...")
                 time.sleep(RETRY_DELAY_SECONDS)
                 continue
            else:
                 return TransactionStatus.FAILED, f"Failed after {MAX_RENAME_RETRIES + 1} attempts: {e}"
        except Exception as e: 
             return TransactionStatus.FAILED, f"Unexpected error during rename: {e}"
    return TransactionStatus.FAILED, "Unknown error after rename attempts."


def _execute_content_line_transaction(
    tx_item: Dict[str, Any],
    root_dir: Path,
    path_translation_map: Dict[str, str],
    path_cache: Dict[str, Path],
    dry_run: bool
) -> Tuple[TransactionStatus, Optional[str]]:
    """Executes a single file content line modification transaction."""
    original_relative_path_str = tx_item["PATH"]
    line_number_1_indexed = tx_item["LINE_NUMBER"]
    original_line_content = tx_item["ORIGINAL_LINE_CONTENT"]
    file_encoding = tx_item["ORIGINAL_ENCODING"] or DEFAULT_ENCODING_FALLBACK

    try:
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)
    except FileNotFoundError:
         return TransactionStatus.SKIPPED, f"Parent path for '{original_relative_path_str}' not found (likely due to prior failed rename)."
    except Exception as e:
         return TransactionStatus.FAILED, f"Error resolving current path for '{original_relative_path_str}': {e}"

    # Content modification should only happen on actual files, not symlinks.
    if current_abs_path.is_symlink():
        return TransactionStatus.SKIPPED, f"File '{current_abs_path}' is a symlink; content modification skipped."
    if not current_abs_path.is_file():
        return TransactionStatus.SKIPPED, f"File '{current_abs_path}' not found or not a file."

    if is_likely_binary_file(current_abs_path):
        return TransactionStatus.SKIPPED, f"File '{current_abs_path}' identified as binary during execution; content modification skipped."

    new_line_content = replace_occurrences(original_line_content) 
    tx_item["PROPOSED_LINE_CONTENT"] = new_line_content

    if new_line_content == original_line_content:
        return TransactionStatus.SKIPPED, "Line content unchanged after replacement."

    if dry_run:
        print(f"[DRY RUN] File '{current_abs_path}', line {line_number_1_indexed}:")
        print(f"[DRY RUN]   Original: {repr(original_line_content)}")
        print(f"[DRY RUN]   Proposed: {repr(new_line_content)}")
        return TransactionStatus.COMPLETED, "DRY_RUN"

    try:
        _ensure_within_sandbox(current_abs_path, root_dir, f"file content write for {current_abs_path.name}")
        try:
            with open(current_abs_path, 'r', encoding=file_encoding, errors='surrogateescape', newline=None) as f:
                lines = f.readlines() 
        except Exception as read_err:
             return TransactionStatus.FAILED, f"Error reading file {current_abs_path} for update: {read_err}"

        if not (0 <= line_number_1_indexed - 1 < len(lines)):
            return TransactionStatus.FAILED, f"Line number {line_number_1_indexed} out of bounds for file {current_abs_path} (len: {len(lines)})."
        
        if lines[line_number_1_indexed - 1] != original_line_content:
             return TransactionStatus.FAILED, f"Original content of line {line_number_1_indexed} in {current_abs_path} has changed since scan."

        lines[line_number_1_indexed - 1] = new_line_content

        try:
            with open(current_abs_path, 'wb') as f: 
                for line in lines:
                    f.write(line.encode(file_encoding, errors='surrogateescape'))
        except Exception as write_err:
             return TransactionStatus.FAILED, f"Error writing updated content to file {current_abs_path}: {write_err}"
        return TransactionStatus.COMPLETED, None
    except SandboxViolationError as sve:
        return TransactionStatus.FAILED, f"SandboxViolation: {sve}"
    except Exception as e:
        return TransactionStatus.FAILED, f"Unexpected error during content update for {current_abs_path}: {e}"


def execute_all_transactions(
    transactions_file_path: Path,
    root_dir: Path,
    dry_run: bool,
    resume: bool
) -> Dict[str, int]:
    """Loads, sorts, and executes all pending/in-progress transactions."""
    transactions = load_transactions(transactions_file_path)
    if not transactions:
        print(f"Error: Could not load transactions from {transactions_file_path} or its backup.")
        return {"completed": 0, "failed": 0, "skipped": 0, "pending": 0}

    stats = {"completed": 0, "failed": 0, "skipped": 0, "pending": 0}
    path_translation_map: Dict[str, str] = {}
    path_cache: Dict[str, Path] = {}

    def execution_sort_key(tx: Dict[str, Any]):
        type_order = {TransactionType.FOLDER_NAME.value: 0, TransactionType.FILE_NAME.value: 1, TransactionType.FILE_CONTENT_LINE.value: 2}
        path_depth = tx["PATH"].count('/') 
        line_num = tx.get("LINE_NUMBER", 0)
        if tx["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
            return (type_order[tx["TYPE"]], -path_depth, tx["PATH"]) 
        else: 
            return (type_order[tx["TYPE"]], tx["PATH"], line_num)

    transactions.sort(key=execution_sort_key)

    total_transactions = len(transactions)
    for i, tx_item in enumerate(transactions):
        tx_id = tx_item.get("id")
        if not tx_id:
            print(f"Warning: Skipping transaction at index {i} due to missing 'id'.")
            continue

        current_status_str = tx_item.get("STATUS", TransactionStatus.PENDING.value)
        try:
            current_status = TransactionStatus(current_status_str)
        except ValueError:
             print(f"Warning: Invalid status '{current_status_str}' for tx {tx_id}. Treating as PENDING.")
             current_status = TransactionStatus.PENDING
             tx_item["STATUS"] = TransactionStatus.PENDING.value 

        if current_status == TransactionStatus.COMPLETED:
            stats["completed"] +=1
            if tx_item["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
                 original_rel_path = tx_item["PATH"]
                 original_name = tx_item["ORIGINAL_NAME"]
                 new_name = replace_occurrences(original_name) 
                 if new_name != original_name:
                     path_translation_map[original_rel_path] = new_name
                     path_cache.pop(original_rel_path, None)
            continue
        if current_status == TransactionStatus.FAILED:
            if not resume: 
                stats["failed"] +=1
                continue
            else: 
                print(f"Resuming FAILED transaction: {tx_id} ({tx_item.get('PATH', 'N/A')})")
                current_status = TransactionStatus.PENDING 
        
        if current_status == TransactionStatus.SKIPPED:
            stats["skipped"] +=1
            continue

        if current_status == TransactionStatus.IN_PROGRESS:
            if not resume: 
                tx_item["STATUS"] = TransactionStatus.PENDING.value
                current_status = TransactionStatus.PENDING
            else: 
                 print(f"Resuming IN_PROGRESS transaction: {tx_id} ({tx_item.get('PATH', 'N/A')})")

        if current_status == TransactionStatus.PENDING or \
           (resume and current_status == TransactionStatus.IN_PROGRESS): 

            print(f"Processing transaction {i+1}/{total_transactions}: {tx_id} ({tx_item.get('TYPE')}: {tx_item.get('PATH')}:{tx_item.get('LINE_NUMBER', '')})")
            update_transaction_status_in_list(transactions, tx_id, TransactionStatus.IN_PROGRESS)
            save_transactions(transactions, transactions_file_path) 

            new_status: TransactionStatus
            error_msg: Optional[str] = None
            proposed_content_update: Optional[str] = None 

            try:
                if tx_item["TYPE"] == TransactionType.FOLDER_NAME.value or tx_item["TYPE"] == TransactionType.FILE_NAME.value:
                    new_status, error_msg = _execute_rename_transaction(tx_item, root_dir, path_translation_map, path_cache, dry_run)
                elif tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
                    new_status, error_msg = _execute_content_line_transaction(tx_item, root_dir, path_translation_map, path_cache, dry_run)
                    if new_status == TransactionStatus.COMPLETED:
                         proposed_content_update = tx_item.get("PROPOSED_LINE_CONTENT")
                else:
                    new_status, error_msg = TransactionStatus.FAILED, f"Unknown transaction type: {tx_item['TYPE']}"
            except SandboxViolationError as sve:
                new_status = TransactionStatus.FAILED
                error_msg = f"CRITICAL SANDBOX VIOLATION: {sve}"
                print(error_msg)
            except Exception as e:
                new_status = TransactionStatus.FAILED
                error_msg = f"Unexpected error during transaction execution: {e}"
                print(error_msg)

            update_transaction_status_in_list(transactions, tx_id, new_status, error_msg, proposed_content_update)
            save_transactions(transactions, transactions_file_path) 
            
            if new_status == TransactionStatus.COMPLETED:
                stats["completed"] += 1
            elif new_status == TransactionStatus.FAILED:
                stats["failed"] += 1
            elif new_status == TransactionStatus.SKIPPED:
                stats["skipped"] += 1
        else: 
             stats["pending"] +=1

    final_pending = sum(1 for t in transactions if t.get("STATUS") == TransactionStatus.PENDING.value)
    stats["pending"] = final_pending
    return stats
