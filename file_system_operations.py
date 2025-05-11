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
from typing import List, Tuple, Optional, Dict, Any, Iterator, cast, Callable, Union
from enum import Enum
import chardet

from replace_logic import replace_flojoy_occurrences # Import the replacement function

# --- Custom Exception ---
class SandboxViolationError(Exception):
    """Custom exception for operations attempting to escape the sandbox."""
    pass

# --- Constants & Enums ---
DEFAULT_ENCODING_FALLBACK = 'utf-8'
TRANSACTION_FILE_BACKUP_EXT = ".bak"

class TransactionType(str, Enum):
    FILE_NAME = "FILE_NAME"
    FOLDER_NAME = "FOLDER_NAME"
    FILE_CONTENT_LINE = "FILE_CONTENT_LINE"

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED" # Added for cases where no change is made or item not found

# --- Helper Functions ---

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
                return None
    except Exception:
        return None

def is_likely_binary_file(file_path: Path, sample_size: int = 1024) -> bool:
    """Heuristic to check if a file is likely binary."""
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)
        if not sample:
            return False
        if b'\x00' in sample:
            return True
        text_chars = set(range(32, 127)) | {ord('\n'), ord('\r'), ord('\t')}
        non_text_count = sum(1 for byte in sample if byte not in text_chars)
        if len(sample) > 0 and (non_text_count / len(sample)) > 0.3:
            return True
        return False
    except Exception:
        return False

def _walk_for_scan(root_dir: Path, excluded_dirs: List[str]) -> Iterator[Path]:
    """Yields paths for scanning, respecting exclusions."""
    abs_excluded_dirs = [root_dir.joinpath(d).resolve(strict=False) for d in excluded_dirs]
    for item_path in root_dir.rglob("*"):
        is_excluded = False
        try:
            resolved_item_path = item_path.resolve(strict=False)
            for excluded_dir in abs_excluded_dirs:
                if resolved_item_path == excluded_dir or excluded_dir in resolved_item_path.parents:
                    is_excluded = True
                    break
        except (ValueError, OSError):
            item_path_str = str(item_path)
            if any(item_path_str.startswith(str(ex_dir)) for ex_dir in abs_excluded_dirs):
                 is_excluded = True
        if is_excluded:
            continue
        yield item_path

def _get_current_absolute_path(
    original_relative_path_str: str,
    root_dir: Path,
    path_translation_map: Dict[str, str], # original_rel_path -> new_relative_path
    cache: Dict[str, Path] # original_rel_path -> current_absolute_path
) -> Path:
    if original_relative_path_str in cache:
        return cache[original_relative_path_str]

    if original_relative_path_str == ".":
        cache["."] = root_dir
        return root_dir

    original_path_obj = Path(original_relative_path_str)
    original_parent_rel_str = str(original_path_obj.parent)
    item_original_name = original_path_obj.name

    current_parent_abs_path = _get_current_absolute_path(
        original_parent_rel_str, root_dir, path_translation_map, cache
    )

    current_item_name = item_original_name
    if original_relative_path_str in path_translation_map:
        new_relative_path_of_this_item = Path(path_translation_map[original_relative_path_str])
        current_item_name = new_relative_path_of_this_item.name
    
    current_abs_path = current_parent_abs_path / current_item_name
    
    cache[original_relative_path_str] = current_abs_path
    return current_abs_path

# --- Scan Logic ---
def scan_directory_for_occurrences(
    root_dir: Path,
    excluded_dirs: List[str],
    excluded_files: List[str],
    file_extensions: Optional[List[str]] 
) -> List[Dict[str, Any]]:
    transactions: List[Dict[str, Any]] = []
    find_target_lower = "flojoy" 
    abs_excluded_files = [root_dir.joinpath(f).resolve(strict=False) for f in excluded_files]

    all_items_for_scan = list(_walk_for_scan(root_dir, excluded_dirs))
    
    sorted_items = sorted(all_items_for_scan, key=lambda p: len(p.parts), reverse=True)

    for item_path in sorted_items:
        try:
            relative_path_str = str(item_path.relative_to(root_dir))
        except ValueError:
            continue 
        
        original_name = item_path.name

        if item_path.resolve(strict=False) in abs_excluded_files:
            continue

        if find_target_lower in original_name.lower():
            tx_type = TransactionType.FOLDER_NAME if item_path.is_dir() else TransactionType.FILE_NAME
            transactions.append({
                "id": str(uuid.uuid4()),
                "TYPE": tx_type.value,
                "PATH": relative_path_str, 
                "ORIGINAL_NAME": original_name,
                "LINE_NUMBER": 0,
                "ORIGINAL_LINE_CONTENT": None,
                "PROPOSED_LINE_CONTENT": None,
                "ORIGINAL_ENCODING": None,
                "STATUS": TransactionStatus.PENDING.value
            })

        if item_path.is_file():
            if is_likely_binary_file(item_path):
                continue
            if file_extensions and (not item_path.suffix or item_path.suffix.lower() not in [ext.lower() for ext in file_extensions]):
                continue
            
            file_encoding = get_file_encoding(item_path) or DEFAULT_ENCODING_FALLBACK
            try:
                with open(item_path, 'r', encoding=file_encoding, errors='surrogateescape', newline='') as f:
                    lines = f.readlines()
                
                for line_num_0_indexed, line_content in enumerate(lines):
                    if find_target_lower in line_content.lower():
                        transactions.append({
                            "id": str(uuid.uuid4()),
                            "TYPE": TransactionType.FILE_CONTENT_LINE.value,
                            "PATH": relative_path_str, 
                            "ORIGINAL_NAME": None,
                            "LINE_NUMBER": line_num_0_indexed + 1, 
                            "ORIGINAL_LINE_CONTENT": line_content, 
                            "PROPOSED_LINE_CONTENT": None, 
                            "ORIGINAL_ENCODING": file_encoding,
                            "STATUS": TransactionStatus.PENDING.value
                        })
            except Exception as e:
                print(f"Warning: Could not read/process content of file {item_path}: {e}")
                pass
    return transactions

# --- Transaction File Management ---
def load_transactions(json_file_path: Path) -> Optional[List[Dict[str, Any]]]:
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    paths_to_try = [json_file_path, backup_path]
    for path in paths_to_try:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    print(f"Loading transactions from: {path}")
                    return cast(List[Dict[str, Any]], json.load(f))
            except Exception as e:
                print(f"Warning: Failed to load transactions from {path}: {e}")
    return None

def save_transactions(transactions: List[Dict[str, Any]], json_file_path: Path) -> None:
    if json_file_path.exists():
        backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
        try:
            shutil.copy2(json_file_path, backup_path)
        except Exception as e:
            print(f"Warning: Could not create backup of {json_file_path}: {e}")
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
    error_message: Optional[str] = None
) -> bool:
    updated = False
    for tx in transactions:
        if tx['id'] == transaction_id:
            tx['STATUS'] = new_status.value
            if error_message:
                tx['ERROR_MESSAGE'] = error_message
            else:
                tx.pop('ERROR_MESSAGE', None)
            updated = True
            break
    return updated

# --- Execution Logic ---

def _ensure_within_sandbox(path_to_check: Path, sandbox_root: Path, operation_desc: str):
    """Checks if a path is within the sandbox_root. Raises SandboxViolationError if not."""
    resolved_path = path_to_check.resolve()
    resolved_sandbox_root = sandbox_root.resolve()
    if not resolved_path.is_relative_to(resolved_sandbox_root) and resolved_path != resolved_sandbox_root :
        raise SandboxViolationError(
            f"Operation '{operation_desc}' on path '{resolved_path}' is outside the sandbox '{resolved_sandbox_root}'."
        )

def _execute_rename_transaction(
    tx: Dict[str, Any],
    root_dir: Path, # This is the sandbox root during self-test
    path_translation_map: Dict[str, str],
    path_cache: Dict[str, Path],
    dry_run: bool
) -> Tuple[TransactionStatus, Optional[str]]:
    original_relative_path_str = tx["PATH"]
    original_name = tx["ORIGINAL_NAME"]
    
    current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)

    if "deep_flojoy_file" in original_name or "deep_atlasvibe_file" in original_name : 
        print(f"DEBUG_RENAME: Processing transaction for: {original_name}")
        print(f"DEBUG_RENAME: Original relative path: {original_relative_path_str}")
        print(f"DEBUG_RENAME: Current absolute path resolved to: {current_abs_path}")
        print(f"DEBUG_RENAME: Does current_abs_path exist? {current_abs_path.exists()}")

    if not current_abs_path.exists():
        return TransactionStatus.SKIPPED, f"Original path '{current_abs_path}' not found."

    new_name = replace_flojoy_occurrences(original_name)
    if new_name == original_name:
        return TransactionStatus.SKIPPED, "Name unchanged after replacement."

    new_abs_path = current_abs_path.with_name(new_name)
    
    if "deep_flojoy_file" in original_name or "deep_atlasvibe_file" in new_name:
        print(f"DEBUG_RENAME: Proposed new name: {new_name}")
        print(f"DEBUG_RENAME: Proposed new absolute path: {new_abs_path}")

    if dry_run:
        print(f"[DRY RUN] Would rename '{current_abs_path}' to '{new_abs_path}'")
        path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
        path_cache[original_relative_path_str] = new_abs_path
        return TransactionStatus.COMPLETED, "DRY_RUN"
    
    try:
        # Sandbox check before actual operation
        _ensure_within_sandbox(current_abs_path, root_dir, f"rename_source for {original_name}")
        _ensure_within_sandbox(new_abs_path, root_dir, f"rename_destination for {new_name}")

        if new_abs_path.exists() and not current_abs_path.resolve().samefile(new_abs_path.resolve()):
            return TransactionStatus.SKIPPED, f"Target path '{new_abs_path}' already exists."

        os.rename(current_abs_path, new_abs_path)
        path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
        path_cache[original_relative_path_str] = new_abs_path
        return TransactionStatus.COMPLETED, None
    except SandboxViolationError as sve:
        return TransactionStatus.FAILED, f"SandboxViolation: {sve}"
    except Exception as e:
        return TransactionStatus.FAILED, str(e)

def _execute_content_line_transaction(
    tx: Dict[str, Any],
    root_dir: Path, # This is the sandbox root during self-test
    path_translation_map: Dict[str, str],
    path_cache: Dict[str, Path],
    dry_run: bool
) -> Tuple[TransactionStatus, Optional[str]]:
    original_relative_path_str = tx["PATH"]
    line_number_1_indexed = tx["LINE_NUMBER"]
    original_line_content = tx["ORIGINAL_LINE_CONTENT"] 
    file_encoding = tx["ORIGINAL_ENCODING"] or DEFAULT_ENCODING_FALLBACK

    current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)

    if not current_abs_path.is_file():
        return TransactionStatus.SKIPPED, f"File '{current_abs_path}' not found or not a file."

    if is_likely_binary_file(current_abs_path):
        return TransactionStatus.SKIPPED, f"File '{current_abs_path}' identified as binary during execution; content modification skipped."

    new_line_content = replace_flojoy_occurrences(original_line_content)
    
    tx["PROPOSED_LINE_CONTENT"] = new_line_content 

    if new_line_content == original_line_content:
        return TransactionStatus.SKIPPED, "Line content unchanged after replacement."

    if dry_run:
        print(f"[DRY RUN] File '{current_abs_path}', line {line_number_1_indexed}:")
        print(f"[DRY RUN]   Original: {repr(original_line_content)}")
        print(f"[DRY RUN]   Proposed: {repr(new_line_content)}")
        return TransactionStatus.COMPLETED, "DRY_RUN"

    try:
        # Sandbox check before actual operation
        _ensure_within_sandbox(current_abs_path, root_dir, f"file_content_write for {current_abs_path.name}")

        with open(current_abs_path, 'r', encoding=file_encoding, errors='surrogateescape', newline='') as f:
            lines = f.readlines()
        
        if not (0 <= line_number_1_indexed - 1 < len(lines)):
            return TransactionStatus.FAILED, f"Line number {line_number_1_indexed} out of bounds for file {current_abs_path} (len: {len(lines)})."

        if lines[line_number_1_indexed - 1] != original_line_content:
             return TransactionStatus.FAILED, f"Original content of line {line_number_1_indexed} in {current_abs_path} has changed since scan."

        lines[line_number_1_indexed - 1] = new_line_content
        
        with open(current_abs_path, 'wb') as f:
            for line in lines:
                f.write(line.encode(file_encoding, errors='surrogateescape'))
        
        return TransactionStatus.COMPLETED, None
    except SandboxViolationError as sve:
        return TransactionStatus.FAILED, f"SandboxViolation: {sve}"
    except Exception as e:
        return TransactionStatus.FAILED, str(e)


def execute_all_transactions(
    transactions_file_path: Path,
    root_dir: Path,
    dry_run: bool,
    resume: bool
) -> Dict[str, int]:
    transactions = load_transactions(transactions_file_path)
    if not transactions:
        print(f"Error: Could not load transactions from {transactions_file_path}")
        return {"completed": 0, "failed": 0, "skipped": 0, "pending": 0}

    stats = {"completed": 0, "failed": 0, "skipped": 0, "pending": 0}
    path_translation_map: Dict[str, str] = {} 
    path_cache: Dict[str, Path] = {} 

    def execution_sort_key(tx: Dict[str, Any]):
        type_order = {TransactionType.FOLDER_NAME.value: 0, TransactionType.FILE_NAME.value: 1, TransactionType.FILE_CONTENT_LINE.value: 2}
        path_depth = tx["PATH"].count(os.sep)
        line_num = tx.get("LINE_NUMBER", 0)

        if tx["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
            return (type_order[tx["TYPE"]], -path_depth, tx["PATH"])
        else: 
            return (type_order[tx["TYPE"]], tx["PATH"], line_num)

    transactions.sort(key=execution_sort_key)
    
    for tx in transactions:
        tx_id = tx["id"]
        current_status = TransactionStatus(tx["STATUS"])

        if current_status == TransactionStatus.COMPLETED or current_status == TransactionStatus.FAILED:
            if current_status == TransactionStatus.COMPLETED:
                stats["completed"] +=1
            if current_status == TransactionStatus.FAILED:
                stats["failed"] +=1
            continue 

        if not resume and current_status == TransactionStatus.IN_PROGRESS:
            tx["STATUS"] = TransactionStatus.PENDING.value 
            current_status = TransactionStatus.PENDING
        
        if current_status == TransactionStatus.PENDING or \
           (resume and current_status == TransactionStatus.IN_PROGRESS):
            
            update_transaction_status_in_list(transactions, tx_id, TransactionStatus.IN_PROGRESS)
            save_transactions(transactions, transactions_file_path) 

            new_status: TransactionStatus
            error_msg: Optional[str] = None

            try:
                if tx["TYPE"] == TransactionType.FOLDER_NAME.value or tx["TYPE"] == TransactionType.FILE_NAME.value:
                    new_status, error_msg = _execute_rename_transaction(tx, root_dir, path_translation_map, path_cache, dry_run)
                elif tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
                    new_status, error_msg = _execute_content_line_transaction(tx, root_dir, path_translation_map, path_cache, dry_run)
                else:
                    new_status, error_msg = TransactionStatus.FAILED, f"Unknown transaction type: {tx['TYPE']}"
            except SandboxViolationError as sve: # Catch sandbox violations from execution helpers
                new_status = TransactionStatus.FAILED
                error_msg = f"CRITICAL SANDBOX VIOLATION: {sve}"
                print(error_msg) # Print critical error immediately
                # Optionally, re-raise or handle more drastically to stop all further processing
            except Exception as e: # Catch other unexpected errors during execution logic
                new_status = TransactionStatus.FAILED
                error_msg = f"Unexpected error during transaction execution: {e}"


            update_transaction_status_in_list(transactions, tx_id, new_status, error_msg)
            save_transactions(transactions, transactions_file_path) 

            if new_status == TransactionStatus.COMPLETED:
                stats["completed"] += 1
            elif new_status == TransactionStatus.FAILED:
                stats["failed"] += 1
                print(f"Transaction {tx_id} FAILED: {error_msg}")
            elif new_status == TransactionStatus.SKIPPED:
                stats["skipped"] += 1
        
        elif current_status == TransactionStatus.SKIPPED : 
             stats["skipped"] +=1
        else: 
            stats["pending"] +=1

    final_pending = sum(1 for t in transactions if t["STATUS"] == TransactionStatus.PENDING.value)
    stats["pending"] = final_pending
    
    return stats

