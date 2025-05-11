#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import os
import shutil
import argparse
import re
import json
import uuid
import tempfile
import filecmp # For comparing JSON files
from pathlib import Path
from typing import List, Tuple, Optional, Callable, Iterator, Dict, Any, cast
import types # For ModuleType
import sys # For sys.exit

# Prefect integration
from prefect import task, flow # Script will fail here if prefect is not installed

# Chardet integration for encoding detection
import chardet # Script will fail here if chardet is not installed


# --- Constants ---
TRANSACTION_FILE_NAME = "planned_transactions.json"
VALIDATION_TRANSACTION_FILE_NAME = "planned_transactions_validation.json" # For dual scan
TRANSACTION_FILE_BACKUP_EXT = ".bak"
SELF_TEST_TRANSACTION_FILE_NAME = "self_test_planned_transactions.json"
SELF_TEST_VALIDATION_FILE_NAME = "self_test_planned_transactions_validation.json"

STATUS_PENDING = "PENDING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED" 
DEFAULT_ENCODING_FALLBACK = 'utf-8'

# --- Core Helper Functions (Shared Logic) ---

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

def _get_case_preserved_replacement(matched_text: str, base_find: str, base_replace: str) -> str:
    """Handles case-preserving replacement, with special logic for flojoy->atlasvibe."""
    if base_find.lower() == 'flojoy' and base_replace.lower() == 'atlasvibe':
        if matched_text == 'flojoy': 
            return 'atlasvibe'
        if matched_text == 'Flojoy': 
            return 'Atlasvibe'
        if matched_text == 'FLOJOY': 
            return 'ATLASVIBE'
        if matched_text == 'FloJoy': 
            return 'AtlasVibe' 
        if matched_text == 'floJoy': 
            return 'atlasVibe' 
        # This fallback might be too simplistic if matched_text has mixed casing not covered above
        # but for re.sub(r'flojoy', replace_func, text, flags=re.IGNORECASE), matched_text will be one of the above.
        return base_replace.lower() 
    
    # Generic case preservation (less critical if specific flojoy->atlasvibe is primary use)
    if matched_text.islower(): 
        return base_replace.lower()
    if matched_text.isupper(): 
        return base_replace.upper()
    if matched_text.istitle(): 
        return base_replace.title()
    if matched_text and base_replace: # Ensure neither is empty
        if matched_text[0].isupper() and not base_replace[0].isupper():
            return base_replace[0].upper() + base_replace[1:]
        if matched_text[0].islower() and not base_replace[0].islower(): # Ensure base_replace is not empty
            return base_replace[0].lower() + base_replace[1:]
    return base_replace 

def perform_text_replacement(text: str, find_pattern: str, replace_pattern: str, is_regex: bool, case_sensitive: bool) -> str:
    """Performs text replacement, calling case-preservation logic if applicable."""
    if (not is_regex and 
        not case_sensitive and 
        find_pattern.lower() == 'flojoy' and 
        replace_pattern.lower() == 'atlasvibe'):
        # This regex ensures that "flojoy" (case-insensitive) is found.
        # The replace_func then handles the specific casing for "atlasvibe".
        def replace_func(match_obj: re.Match[str]) -> str:
            return _get_case_preserved_replacement(match_obj.group(0), 'flojoy', 'atlasvibe')
        return re.sub(r'flojoy', replace_func, text, flags=re.IGNORECASE)
    else:
        flags = 0 if case_sensitive else re.IGNORECASE
        if is_regex:
            return re.sub(find_pattern, replace_pattern, text, flags=flags)
        else: 
            # For non-regex, non-special-case, we still want to replace all occurrences.
            # re.sub is more robust for this than str.replace() if case-insensitivity is needed.
            if not case_sensitive:
                return re.sub(re.escape(find_pattern), replace_pattern, text, flags=re.IGNORECASE)
            else:
                # Simple string replacement if case-sensitive and not regex
                return text.replace(find_pattern, replace_pattern)

def _text_contains_pattern(text_to_search: str, find_pattern: str, is_regex: bool, case_sensitive: bool) -> bool:
    """Helper to check if text contains the find_pattern with given options."""
    if is_regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        return bool(re.search(find_pattern, text_to_search, flags))
    else: 
        # For the special "flojoy" find, it's always case-insensitive for detection
        if find_pattern.lower() == 'flojoy' and not case_sensitive and not is_regex:
             return 'flojoy' in text_to_search.lower()
        if case_sensitive:
            return find_pattern in text_to_search
        else: 
            return find_pattern.lower() in text_to_search.lower()

def _walk_for_scan(root_dir: Path, excluded_dirs: List[str]) -> Iterator[Path]:
    """Yields paths for scanning, respecting exclusions."""
    abs_excluded_dirs = [root_dir.joinpath(d).resolve(strict=False) for d in excluded_dirs]
    for item_path in root_dir.rglob("*"):
        is_excluded = False
        try:
            resolved_item_path = item_path.resolve(strict=False) 
            for excluded_dir in abs_excluded_dirs:
                # Check if item_path is the excluded_dir itself or is inside it
                if resolved_item_path == excluded_dir or excluded_dir in resolved_item_path.parents:
                    is_excluded = True
                    break
        except (ValueError, OSError): 
            # Fallback for paths that might cause issues with resolve() or is_relative_to()
            # e.g. broken symlinks, or very long paths on some OS.
            item_path_str = str(item_path) 
            if any(item_path_str.startswith(str(ex_dir)) for ex_dir in abs_excluded_dirs):
                 is_excluded = True
        if is_excluded:
            continue
        yield item_path

def _get_current_absolute_path(
    original_relative_path_str: str, 
    root_dir: Path, 
    path_translation_map: Dict[str, str],
    cache: Dict[str, Path] 
) -> Path:
    """
    Recursively determines the current absolute path of an item,
    considering parent renames recorded in the path_translation_map.
    path_translation_map stores: original_relative_path_str -> new_relative_path_str.
    Cache is used for memoization.
    """
    if original_relative_path_str in cache:
        return cache[original_relative_path_str]

    # Base case: if the original path is ".", it refers to the root_dir
    if original_relative_path_str == ".":
        # The root of the relative path structure is the main root_dir.
        # It cannot be "renamed" in the context of path_translation_map keys,
        # as keys are relative paths *under* root_dir.
        cache[original_relative_path_str] = root_dir
        return root_dir

    # If the path itself was directly renamed, its entry in path_translation_map is authoritative
    # for its new relative path.
    if original_relative_path_str in path_translation_map:
        # The value in path_translation_map is the new relative path *for this specific item*
        # This new relative path is already "final" as it was determined when this item was renamed.
        current_item_rel_path_str = path_translation_map[original_relative_path_str]
        res = root_dir / current_item_rel_path_str
        cache[original_relative_path_str] = res
        return res

    # If not directly in map, it's either a child of some (potentially renamed) directory,
    # or it's an item that was never part of any rename operation (e.g. file in a non-renamed dir).
    original_path_obj = Path(original_relative_path_str)
    original_parent_rel_str = str(original_path_obj.parent)
    item_name = original_path_obj.name

    # Recursively find the current absolute path of the parent directory.
    current_parent_abs_path = _get_current_absolute_path(
        original_parent_rel_str, root_dir, path_translation_map, cache
    )
    
    # The item's name itself (relative to its parent) hasn't changed *by this lookup*.
    # If the item *is* to be renamed, that's a separate transaction for original_relative_path_str.
    # Here, we are just finding its current location based on parent renames.
    res = current_parent_abs_path / item_name
    cache[original_relative_path_str] = res
    return res

# --- Phase 1: Scan & Collect Tasks ---

@task
def scan_and_collect_occurrences_task(
    root_dir: Path, find_pattern: str, replace_pattern: str, is_regex: bool, case_sensitive: bool,
    excluded_dirs: List[str], excluded_files: List[str], file_extensions: Optional[List[str]],
    process_binary_files: bool, scan_id: str 
) -> List[Dict[str, Any]]:
    transactions: List[Dict[str, Any]] = []
    abs_excluded_files = [root_dir.joinpath(f).resolve(strict=False) for f in excluded_files]

    # Collect all items first to allow sorting for rename processing (deepest first for names)
    # This sorting is primarily for deterministic collection of rename transactions.
    # The critical sort for execution order is in compile_transactions_json_task.
    all_items_for_scan = list(_walk_for_scan(root_dir, excluded_dirs))
    
    # Process path name changes (sorted by depth, deepest first)
    # This helps in scenarios where a parent dir rename might affect child path strings if not handled.
    # However, _get_current_absolute_path is the main guard during execution.
    path_candidates_for_rename = sorted(
        all_items_for_scan, key=lambda p: len(p.parts), reverse=True
    )

    for item_path in path_candidates_for_rename:
        try:
            relative_path_str = str(item_path.relative_to(root_dir))
        except ValueError: 
            # This can happen if item_path is not under root_dir, though _walk_for_scan should prevent it.
            continue # Skip if path is not relative to root_dir
        original_name = item_path.name
        
        # File-specific exclusions and extension checks
        if item_path.is_file():
            if item_path.resolve(strict=False) in abs_excluded_files:
                continue
            if file_extensions:
                # Ensure suffix exists and is in the list (case-insensitive)
                if not item_path.suffix or item_path.suffix.lower() not in [ext.lower() for ext in file_extensions]:
                    continue
        
        if _text_contains_pattern(original_name, find_pattern, is_regex, case_sensitive):
            proposed_new_name = perform_text_replacement(
                original_name, find_pattern, replace_pattern, is_regex, case_sensitive
            )
            if proposed_new_name != original_name:
                occurrence_type = "FOLDERNAME" if item_path.is_dir() else "FILENAME"
                transactions.append({
                    "id": str(uuid.uuid4()), "OCCURRENCE_TYPE": occurrence_type,
                    "PATH": relative_path_str, "NEW_PATH_COMPONENT": proposed_new_name,
                    "LINE_NUMBER": 0, # Not applicable for name changes
                    "ORIGINAL_LINE_CONTENT": None, # Not applicable
                    "PROPOSED_LINE_CONTENT": None, # Not applicable
                    "FIND_PATTERN": find_pattern, "REPLACE_PATTERN": replace_pattern,
                    "IS_REGEX": is_regex, "CASE_SENSITIVE": case_sensitive, "STATUS": STATUS_PENDING
                })

    # Process content changes (iterate through all items again, could optimize later if needed)
    for item_path in all_items_for_scan: # Using the already filtered list
        if not item_path.is_file(): 
            continue # Content changes only apply to files
        
        try:
            relative_path_str = str(item_path.relative_to(root_dir))
        except ValueError:
            continue

        # Exclusions and extension checks (repeated for clarity, could be part of a single loop)
        if item_path.resolve(strict=False) in abs_excluded_files:
            continue
        if file_extensions and (not item_path.suffix or item_path.suffix.lower() not in [ext.lower() for ext in file_extensions]):
            continue
        
        if not process_binary_files and is_likely_binary_file(item_path):
            continue

        original_encoding = get_file_encoding(item_path)
        # If encoding is None (undetermined), fallback to UTF-8 for decode attempt.
        # `surrogateescape` will handle bytes that don't fit.
        current_encoding_to_try = original_encoding or DEFAULT_ENCODING_FALLBACK 

        try:
            file_content_bytes = item_path.read_bytes()
            # Decode with surrogateescape to preserve non-decodable bytes
            file_content_str = file_content_bytes.decode(current_encoding_to_try, errors='surrogateescape')
            
            if _text_contains_pattern(file_content_str, find_pattern, is_regex, case_sensitive):
                # For content, we don't pre-calculate line-by-line changes here,
                # just mark the file for processing. The actual replacement happens in execute_content_transactions_task.
                transactions.append({
                    "id": str(uuid.uuid4()), "OCCURRENCE_TYPE": "STRING_IN_FILE", 
                    "PATH": relative_path_str, "NEW_PATH_COMPONENT": None, # Not applicable
                    "LINE_NUMBER": 0, # Placeholder, actual line numbers not stored in this phase
                    "ORIGINAL_LINE_CONTENT": None, # Placeholder
                    "PROPOSED_LINE_CONTENT": None, # Placeholder
                    "ORIGINAL_ENCODING": original_encoding, # Store detected encoding
                    "FIND_PATTERN": find_pattern, "REPLACE_PATTERN": replace_pattern,
                    "IS_REGEX": is_regex, "CASE_SENSITIVE": case_sensitive, "STATUS": STATUS_PENDING
                })
        except Exception: 
            # Log this? For now, silently skip files that cause errors during read/decode.
            # This could be due to permissions, or very unusual file issues.
            pass 
            
    return transactions

# --- Phase 2: Compile JSON Task & Compare ---

@task
def compile_transactions_json_task(transactions: List[Dict[str, Any]], output_dir: Path, filename: str) -> Path:
    def sort_key(t: Dict[str, Any]) -> Tuple[Any, ...]:
        path_depth = t["PATH"].count(os.sep)
        type_order_map = {"FOLDERNAME": 0, "FILENAME": 1, "STRING_IN_FILE": 2}
        occurrence_type = t["OCCURRENCE_TYPE"]
        
        if occurrence_type in ["FOLDERNAME", "FILENAME"]:
            # Sort renames by type, then by descending depth (deepest first), then by path string
            return (type_order_map[occurrence_type], -path_depth, t["PATH"])
        else: # STRING_IN_FILE
            # Sort content changes by path (ascending depth), then by path string. Line number isn't used for sorting here.
            return (type_order_map[occurrence_type], path_depth, t["PATH"])

    transactions.sort(key=sort_key)
    
    json_file_path = output_dir / filename
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=4)
    except Exception as e: # Catch more specific IO/JSON errors if possible
        # Consider logging the error or raising a more specific custom exception
        raise
    return json_file_path

@task
def compare_transaction_files_task(file1_path: Path, file2_path: Path) -> bool:
    if not file1_path.exists() or not file2_path.exists():
        raise FileNotFoundError("Transaction file(s) missing for comparison.")

    try:
        with open(file1_path, 'r', encoding='utf-8') as f1, open(file2_path, 'r', encoding='utf-8') as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)
        
        # Normalize transactions for comparison by removing volatile fields (id, status)
        # and sorting them to ensure order doesn't affect comparison.
        def comparable_tx_list(tx_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            # Key for sorting individual transactions before comparing lists
            # Must match the sort_key in compile_transactions_json_task for fields that define uniqueness
            def tx_sort_key(tx: Dict[str, Any]):
                path_depth = tx["PATH"].count(os.sep)
                type_order_map = {"FOLDERNAME": 0, "FILENAME": 1, "STRING_IN_FILE": 2}
                occurrence_type = tx["OCCURRENCE_TYPE"]
                if occurrence_type in ["FOLDERNAME", "FILENAME"]:
                     return (type_order_map[occurrence_type], -path_depth, tx["PATH"])
                else: # STRING_IN_FILE
                     return (type_order_map[occurrence_type], path_depth, tx["PATH"])


            return sorted(
                [{k: v for k, v in tx.items() if k not in ['id', 'STATUS']} for tx in tx_list],
                key=tx_sort_key
            )

        comp_data1 = comparable_tx_list(data1)
        comp_data2 = comparable_tx_list(data2)

        if comp_data1 == comp_data2:
            return True
        else:
            # For debugging, it might be useful to dump the differing lists or use a diff tool.
            # For now, a simple ValueError is raised.
            raise ValueError("Scan determinism check failed: Transaction plans differ between two consecutive scans.")
            
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from transaction files: {e}")
    except Exception as e: # Catch other potential errors
        raise # Re-raise other exceptions

# --- Phase 3: Execute Transactions Tasks ---

def _load_transactions_with_fallback(json_file_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Loads transactions from primary JSON, falls back to .bak on error."""
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    # Try loading primary file first
    if json_file_path.exists():
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                return cast(List[Dict[str, Any]], json.load(f))
        except json.JSONDecodeError: # If primary is corrupt, try backup
            if backup_path.exists():
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f_bak:
                        # Log that backup is being used
                        return cast(List[Dict[str, Any]], json.load(f_bak))
                except Exception: # If backup also fails
                    return None # Indicate failure to load
            return None # Primary corrupt, no backup
        except Exception: # Other errors reading primary
             return None
    # If primary does not exist, try backup
    elif backup_path.exists():
        try:
            with open(backup_path, 'r', encoding='utf-8') as f_bak:
                # Log that backup is being used
                return cast(List[Dict[str, Any]], json.load(f_bak))
        except Exception:
            return None # Backup failed
    return None # Neither file exists


def _update_transaction_status_in_json(json_file_path: Path, transaction_id: str, new_status: str, error_message: Optional[str] = None) -> None:
    """Updates status of a single transaction in the JSON file, creating a backup first."""
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    
    # Ensure primary file exists to update; if not, can't update.
    if not json_file_path.exists():
        # If only backup exists, we can't reliably update status.
        # This situation implies a problem occurred after backup creation.
        return

    try:
        # Create backup before modification
        shutil.copy2(json_file_path, backup_path) 
    except Exception:
        # Log failure to backup? If backup fails, proceeding might be risky.
        # For now, we'll proceed but this is a point of potential data loss if update fails.
        return 

    try:
        with open(json_file_path, 'r+', encoding='utf-8') as f:
            data: List[Dict[str, Any]] = json.load(f)
            updated = False
            for t_item in data:
                if t_item['id'] == transaction_id:
                    t_item['STATUS'] = new_status
                    if error_message: 
                        t_item['ERROR_MESSAGE'] = error_message
                    else: # Remove error message if status is no longer FAILED/SKIPPED
                        t_item.pop('ERROR_MESSAGE', None) 
                    updated = True
                    break
            
            if updated:
                f.seek(0) # Rewind to the beginning of the file
                json.dump(data, f, indent=4)
                f.truncate() # Remove trailing content if new data is shorter
            # else: Transaction ID not found, log this?
    except Exception:
        # Attempt to restore from backup if update fails
        try:
            shutil.copy2(backup_path, json_file_path)
            # Log restoration
        except Exception:
            # Log failure to restore. JSON file might be in an inconsistent state.
            pass


@task 
def execute_rename_transactions_task(
    json_file_path: Path, root_dir: Path, dry_run: bool,
    validation_json_path: Optional[Path] = None # Keep for potential future use, though not strictly used for data now
) -> Dict[str, Any]:
    transactions = _load_transactions_with_fallback(json_file_path)
    if transactions is None:
        # Log error: failed to load transaction file
        return {"completed": 0, "failed": 0, "skipped": 0, "path_translation_map": {}}

    # Filter for rename transactions that are pending
    rename_txs = [
        t for t in transactions 
        if t["OCCURRENCE_TYPE"] in ["FOLDERNAME", "FILENAME"] and t["STATUS"] == STATUS_PENDING
    ]
    
    completed_count, failed_count, skipped_count = 0, 0, 0
    path_translation_map: Dict[str, str] = {} # Tracks original_rel_path -> new_rel_path
    # Cache for _get_current_absolute_path to optimize recursive calls
    path_cache: Dict[str, Path] = {}


    for tx in rename_txs: # Iterate through the pre-sorted list from JSON
        tx_id = tx["id"] # Assume ID is always present
        
        # Basic check for essential keys
        if not all(k in tx for k in ["PATH", "NEW_PATH_COMPONENT"]):
            _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete (missing PATH or NEW_PATH_COMPONENT)")
            failed_count += 1
            continue

        original_relative_path_str = tx["PATH"]
        # Determine current absolute path, considering previous renames in this same execution run
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)
        
        if not current_abs_path.exists():
            _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, f"Original path '{current_abs_path}' not found (possibly moved or deleted manually, or affected by prior unrecorded rename).")
            skipped_count += 1
            continue

        proposed_new_name_component = tx["NEW_PATH_COMPONENT"]
        new_abs_path = current_abs_path.with_name(proposed_new_name_component)

        if dry_run:
            # In dry run, simulate the rename for the translation map
            # The new relative path is based on the new_abs_path, which itself was derived from current_abs_path.
            path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
            # Update cache as if rename happened, so subsequent calls to _get_current_absolute_path see this change
            path_cache[original_relative_path_str] = new_abs_path

            _update_transaction_status_in_json(json_file_path, tx_id, STATUS_COMPLETED + " (DRY_RUN)")
            completed_count += 1
            continue

        # Prevent overwriting if target already exists and is a different inode
        if new_abs_path.exists() and not current_abs_path.resolve().samefile(new_abs_path.resolve()):
            _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, f"Target path '{new_abs_path}' already exists and is a different file/directory.")
            skipped_count += 1
            continue
        
        try:
            # Ensure parent directory of the new path exists (it should, if renaming within same dir)
            # This is more relevant if moving files, but good practice.
            if not new_abs_path.parent.exists(): 
                # This case should ideally not happen if only renaming, implies structural issue or bug.
                os.makedirs(new_abs_path.parent, exist_ok=True) # Create if it doesn't exist
            
            os.rename(current_abs_path, new_abs_path)
            
            # Record the successful rename in the translation map
            # The key is the *original* relative path from the scan.
            # The value is the *new* relative path.
            path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
            # Update cache with the new absolute path for this original relative path
            path_cache[original_relative_path_str] = new_abs_path
            
            _update_transaction_status_in_json(json_file_path, tx_id, STATUS_COMPLETED)
            completed_count += 1
        except Exception as e:
            _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, str(e))
            failed_count += 1

    return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count, "path_translation_map": path_translation_map}


@task 
def execute_content_transactions_task(
    json_file_path: Path, root_dir: Path, dry_run: bool,
    path_translation_map: Dict[str, str], process_binary_files: bool,
    find_pattern: str, replace_pattern: str, is_regex: bool, case_sensitive: bool,
    validation_json_path: Optional[Path] = None # Keep for consistency, not actively used for data
) -> Dict[str, int]:
    transactions = _load_transactions_with_fallback(json_file_path)
    if transactions is None:
        return {"completed": 0, "failed": 0, "skipped": 0}
            
    # Group transactions by original file path to process each file once
    file_to_process_details: Dict[str, Dict[str, Any]] = {} 
    # Cache for _get_current_absolute_path
    path_cache: Dict[str, Path] = {}


    for tx in transactions:
        if tx["OCCURRENCE_TYPE"] == "STRING_IN_FILE" and tx["STATUS"] == STATUS_PENDING:
            tx_id = tx["id"]
            
            if "PATH" not in tx: # Basic validation
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete (missing PATH for content change)")
                continue 

            original_rel_path = tx["PATH"]
            if original_rel_path not in file_to_process_details:
                file_to_process_details[original_rel_path] = {
                    "tx_ids": [], # Store all transaction IDs related to this file
                    "encoding": tx.get("ORIGINAL_ENCODING") # Get encoding from the first transaction for this file
                }
            file_to_process_details[original_rel_path]["tx_ids"].append(tx_id) 
            
    completed_count, failed_count, skipped_count = 0, 0, 0

    for original_relative_path_str, details in file_to_process_details.items():
        tx_ids_for_file = details["tx_ids"] # All tx_ids for this single file
        # Determine current absolute path using the translation map from rename phase
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)

        if not current_abs_path.is_file(): # Check if it's a file and exists
            error_msg = f"File path '{current_abs_path}' not found or not a file (original: '{original_relative_path_str}')."
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, error_msg)
            skipped_count += len(tx_ids_for_file)
            continue

        if not process_binary_files and is_likely_binary_file(current_abs_path):
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, "Skipped binary file as per settings.")
            skipped_count += len(tx_ids_for_file)
            continue
            
        original_encoding = details["encoding"] # Encoding detected during scan
        current_encoding_to_try = original_encoding or DEFAULT_ENCODING_FALLBACK

        if dry_run:
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_COMPLETED + " (DRY_RUN)")
            completed_count += len(tx_ids_for_file)
            continue

        try:
            original_full_bytes = current_abs_path.read_bytes()
            # Decode using detected encoding (or fallback) with surrogateescape
            original_full_content_str = original_full_bytes.decode(current_encoding_to_try, errors='surrogateescape')
            
            modified_full_content_str = perform_text_replacement(
                original_full_content_str, find_pattern, replace_pattern, is_regex, case_sensitive
            )

            if modified_full_content_str != original_full_content_str:
                # Re-encode with the same encoding and error handling
                modified_bytes = modified_full_content_str.encode(current_encoding_to_try, errors='surrogateescape')
                current_abs_path.write_bytes(modified_bytes)
                status_msg = STATUS_COMPLETED
            else: 
                status_msg = STATUS_SKIPPED # No actual change in content
            
            for tx_id in tx_ids_for_file: # Update all related transactions for this file
                _update_transaction_status_in_json(json_file_path, tx_id, status_msg, 
                                                   "No change to file content after replacement." if status_msg == STATUS_SKIPPED else None)
            if status_msg == STATUS_COMPLETED:
                completed_count += len(tx_ids_for_file)
            else:
                skipped_count += len(tx_ids_for_file)

        except Exception as e: 
            error_msg = f"Error processing file content for '{current_abs_path}': {e}"
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, error_msg)
            failed_count += len(tx_ids_for_file)
            
    return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count}


# --- Self-Test Functionality ---
def _create_self_test_environment(base_dir: Path) -> None:
    # Base structure
    (base_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir").mkdir(parents=True)
    (base_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file_mixed_eol.txt").write_text(
        "flojoy line 1\r\nFLOJOY line 2\nFlojoy line 3\r\nFloJoy line 4\nfloJoy line 5\nmyflojoy_project details"
    ) 
    (base_dir / "flojoy_root" / "another_flojoy_file.py").write_text(
        "import flojoy_lib\nclass MyFlojoyClass: pass\nFLOJOY_CONSTANT = 100\n# trailing spaces flojoy  \n"
    )
    # Files for name-only or content-only changes
    (base_dir / "only_name_flojoy.md").write_text("No relevant content here.") # Content should remain unchanged
    (base_dir / "only_content.txt").write_text("Line with flojoy here.\nAnother line with Flojoy.") # Name should remain unchanged
    
    # Multiple occurrences and edge cases
    (base_dir / "multiple_on_line_flojoy.txt").write_text("flojoy flojoy Flojoy FLOJOY floJoy FloJoy")
    (base_dir / "empty_flojoy_file.txt").touch() # Name change, empty content
    (base_dir / "FLOJOY_is_the_name_folder").mkdir()
    (base_dir / "FLOJOY_is_the_name_folder" / "file_in_FLOJOY_folder.txt").write_text("Some flojoy content.")
    
    # Binary and specific encodings
    (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")
    try:
        (base_dir / "latin1_flojoy_content.txt").write_text("café flojoy here\nAnother Flojoy line with accent aigu: é", encoding='latin-1')
        (base_dir / "cp1252_flojoy_content.txt").write_text("Euro € symbol with flojoy.", encoding='cp1252')
        sjis_text = "これはflojoyのテストです。\n次の行もFlojoyです。" 
        (base_dir / "sjis_flojoy_content.txt").write_text(sjis_text, encoding='shift_jis', errors='replace')
        gb18030_text = "你好 flojoy 世界\n这是 Flojoy 的一个例子" 
        (base_dir / "gb18030_flojoy_content.txt").write_text(gb18030_text, encoding='gb18030', errors='replace')
        invalid_utf8_bytes = b"ValidStart_flojoy_" + b"\xff\xfe" + b"_flojoy_ValidEnd" # \xff\xfe are invalid in UTF-8
        (base_dir / "invalid_utf8_flojoy_file.txt").write_bytes(invalid_utf8_bytes)
    except Exception: 
        pass # Silently skip if encodings are not supported on the system for writing

    # Exclusions
    (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in excluded file")
    (base_dir / "no_flojoy_here.log").write_text("This is a log file without the target string.")

    # New test files based on user request
    (base_dir / "edge_case_flojoy_only.txt").write_text("flojoy")
    (base_dir / "edge_case_Flojoy_only.txt").write_text("Flojoy")
    (base_dir / "edge_case_FLOJOY_only.txt").write_text("FLOJOY")
    (base_dir / "edge_case_FloJoy_only.txt").write_text("FloJoy")
    (base_dir / "edge_case_floJoy_only.txt").write_text("floJoy")
    (base_dir / "spacing_around_flojoy.txt").write_text("  flojoy  \nnext flojoy line")
    (base_dir / "no_match_for_flojoy.txt").write_text("fl0j0y platform, no actual target string")
    (base_dir / "eol_flojoy_eol.txt").write_bytes(b"\nflojoy\r\n") # Use bytes for precise EOL

@task 
def _verify_self_test_results_task(temp_dir: Path, process_binary_files: bool) -> bool:
    print("--- Verifying Self-Test Results ---")
    passed_checks, failed_checks = 0, 0

    def check(condition: bool, pass_msg: str, fail_msg: str) -> bool:
        nonlocal passed_checks, failed_checks
        if condition: 
            print(f"PASS: {pass_msg}")
            passed_checks += 1
        else: 
            print(f"FAIL: {fail_msg}")
            failed_checks += 1
        return condition

    # Expected paths after all transformations
    # Note: only_content.txt name should NOT change.
    exp_paths = [
        temp_dir / "atlasvibe_root", 
        temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder",
        temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir",
        temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file_mixed_eol.txt",
        temp_dir / "atlasvibe_root" / "another_atlasvibe_file.py",
        temp_dir / "only_name_atlasvibe.md", 
        temp_dir / "only_content.txt", # Name unchanged
        temp_dir / "binary_atlasvibe_file.bin",
        temp_dir / "latin1_atlasvibe_content.txt", 
        temp_dir / "cp1252_atlasvibe_content.txt",
        temp_dir / "sjis_atlasvibe_content.txt", 
        temp_dir / "gb18030_atlasvibe_content.txt",
        temp_dir / "invalid_utf8_atlasvibe_file.txt", 
        temp_dir / "empty_atlasvibe_file.txt", 
        temp_dir / "ATLASVIBE_is_the_name_folder",
        temp_dir / "ATLASVIBE_is_the_name_folder" / "file_in_ATLASVIBE_folder.txt",
        temp_dir / "multiple_on_line_atlasvibe.txt",
        # New files (names should be changed)
        temp_dir / "edge_case_atlasvibe_only.txt",
        temp_dir / "edge_case_Atlasvibe_only.txt", # Assuming perform_text_replacement handles this for names
        temp_dir / "edge_case_ATLASVIBE_only.txt",
        temp_dir / "edge_case_AtlasVibe_only.txt",
        temp_dir / "edge_case_atlasVibe_only.txt",
        temp_dir / "spacing_around_atlasvibe.txt",
        temp_dir / "no_match_for_atlasvibe.txt", # Name changes if "flojoy" was in it
        temp_dir / "eol_atlasvibe_eol.txt"
    ]
    # Adjust names for new files if original name contained 'flojoy'
    # The script renames files based on 'flojoy' in name, then processes content.
    # So, 'edge_case_flojoy_only.txt' becomes 'edge_case_atlasvibe_only.txt'
    # 'no_match_for_flojoy.txt' becomes 'no_match_for_atlasvibe.txt'
    # 'eol_flojoy_eol.txt' becomes 'eol_atlasvibe_eol.txt'

    for p in exp_paths: 
        check(p.exists(), f"Path '{p.relative_to(temp_dir)}' exists.", f"Path '{p.relative_to(temp_dir)}' MISSING.")
    check(not (temp_dir / "flojoy_root").exists(), "Old 'flojoy_root' removed.", "Old 'flojoy_root' STILL EXISTS.")

    # Content checks (Byte-level for precision)
    def check_file_content_bytes(file_path: Path, expected_bytes: bytes, test_name: str):
        if file_path.is_file():
            actual_bytes = file_path.read_bytes()
            check(actual_bytes == expected_bytes, f"{test_name} content correct (byte-level).",
                  f"{test_name} content INCORRECT. Expected: {expected_bytes!r}, Got: {actual_bytes!r}")
        else:
            check(False, "", f"{test_name} file MISSING for content check.")

    # --- Existing file content checks (adapted to use check_file_content_bytes) ---
    deep_file_path = temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file_mixed_eol.txt"
    expected_deep_text = "atlasvibe line 1\r\nATLASVIBE line 2\nAtlasvibe line 3\r\nAtlasVibe line 4\natlasVibe line 5\nmyatlasvibe_project details"
    check_file_content_bytes(deep_file_path, expected_deep_text.encode('utf-8'), "Mixed EOL")

    multiple_file_path = temp_dir / "multiple_on_line_atlasvibe.txt"
    expected_multiple_text = "atlasvibe atlasvibe Atlasvibe ATLASVIBE atlasVibe AtlasVibe" # No strip, exact match
    check_file_content_bytes(multiple_file_path, expected_multiple_text.encode('utf-8'), "Multiple on line")

    bin_file_path = temp_dir / "binary_atlasvibe_file.bin" # Name already changed
    if bin_file_path.is_file(): # Special handling for binary
        bin_content = bin_file_path.read_bytes()
        original_bin_text_parts = (b"prefix_flojoy_suffix", b"flojoy_data") # These are parts of the original binary content
        replaced_bin_text_parts = (b"prefix_atlasvibe_suffix", b"atlasvibe_data")
        binary_core = b"\x00\x01\x02"
        binary_end = b"\x03\x04"
        expected_after_replace = replaced_bin_text_parts[0] + binary_core + replaced_bin_text_parts[1] + binary_end
        # Original binary file name was binary_flojoy_file.bin, content had flojoy.
        # If process_binary_files is true, content should change.
        # If process_binary_files is false, content should NOT change, even if name changed.
        # The test setup creates "binary_flojoy_file.bin" with "flojoy" in content.
        # It's renamed to "binary_atlasvibe_file.bin".
        # Its content is then processed (or not) based on process_binary_files.
        original_content_for_binary = b"prefix_flojoy_suffix" + binary_core + b"flojoy_data" + binary_end

        if process_binary_files:
            check(bin_content == expected_after_replace, "Binary file content processed as expected.", 
                  f"Binary file content processed INCORRECTLY. Expected: {expected_after_replace!r}, Got: {bin_content!r}")
        else: # Should be original content if not processed
            check(bin_content == original_content_for_binary, "Binary file content UNTOUCHED as expected.", 
                  f"Binary file content MODIFIED when it shouldn't have been. Expected: {original_content_for_binary!r}, Got: {bin_content!r}")
    else:
        check(False, "", "Binary file MISSING for content check.")


    check_file_content_bytes(temp_dir / "latin1_atlasvibe_content.txt", 
                             "café atlasvibe here\nAnother Atlasvibe line with accent aigu: é".encode('latin-1'), "Latin-1")
    check_file_content_bytes(temp_dir / "cp1252_atlasvibe_content.txt", 
                             "Euro € symbol with atlasvibe.".encode('cp1252'), "CP1252")
    check_file_content_bytes(temp_dir / "sjis_atlasvibe_content.txt", 
                             "これはatlasvibeのテストです。\n次の行もAtlasvibeです。".encode('shift_jis', errors='replace'), "Shift-JIS")
    check_file_content_bytes(temp_dir / "gb18030_atlasvibe_content.txt", 
                             "你好 atlasvibe 世界\n这是 Atlasvibe 的一个例子".encode('gb18030', errors='replace'), "GB18030")
    
    invalid_utf8_path = temp_dir / "invalid_utf8_atlasvibe_file.txt" # Name changed
    expected_invalid_bytes = b"ValidStart_atlasvibe_" + b"\xff\xfe" + b"_atlasvibe_ValidEnd"
    check_file_content_bytes(invalid_utf8_path, expected_invalid_bytes, "Invalid UTF-8 sequence preservation")

    # Check content of only_name_atlasvibe.md (name changed, content should be original)
    only_name_md_path = temp_dir / "only_name_atlasvibe.md"
    check_file_content_bytes(only_name_md_path, "No relevant content here.".encode('utf-8'), "Name-only change (content preservation)")

    # Check content of only_content.txt (name did NOT change, content should change)
    only_content_txt_path = temp_dir / "only_content.txt"
    expected_only_content_text = "Line with atlasvibe here.\nAnother line with Atlasvibe."
    check_file_content_bytes(only_content_txt_path, expected_only_content_text.encode('utf-8'), "Content-only change")
    
    # --- New file content checks ---
    check_file_content_bytes(temp_dir / "edge_case_atlasvibe_only.txt", b"atlasvibe", "Edge case flojoy_only")
    check_file_content_bytes(temp_dir / "edge_case_Atlasvibe_only.txt", b"Atlasvibe", "Edge case Flojoy_only")
    check_file_content_bytes(temp_dir / "edge_case_ATLASVIBE_only.txt", b"ATLASVIBE", "Edge case FLOJOY_only")
    check_file_content_bytes(temp_dir / "edge_case_AtlasVibe_only.txt", b"AtlasVibe", "Edge case FloJoy_only")
    check_file_content_bytes(temp_dir / "edge_case_atlasVibe_only.txt", b"atlasVibe", "Edge case floJoy_only")
    
    expected_spacing_text = "  atlasvibe  \nnext atlasvibe line"
    check_file_content_bytes(temp_dir / "spacing_around_atlasvibe.txt", expected_spacing_text.encode('utf-8'), "Spacing around flojoy")
    
    # This file's name changes because "flojoy" is in "no_match_for_flojoy.txt"
    # But its content should remain unchanged.
    no_match_path = temp_dir / "no_match_for_atlasvibe.txt" 
    original_no_match_text = "fl0j0y platform, no actual target string"
    check_file_content_bytes(no_match_path, original_no_match_text.encode('utf-8'), "No match in content")

    check_file_content_bytes(temp_dir / "eol_atlasvibe_eol.txt", b"\natlasvibe\r\n", "EOL flojoy EOL")

    # --- Excluded files (should be untouched) ---
    excluded_file = temp_dir / "exclude_this_flojoy_file.txt" 
    check(excluded_file.is_file(), "Excluded file still exists.", "Excluded file MISSING.")
    if excluded_file.is_file():
        # Content should be original "flojoy content in excluded file"
        check_file_content_bytes(excluded_file, "flojoy content in excluded file".encode('utf-8'), "Excluded file content")
    
    log_file_test = temp_dir / "no_flojoy_here.log" # Name has no "flojoy", content has no "flojoy"
    check(log_file_test.is_file(), ".log file still exists.", ".log file MISSING.")
    if log_file_test.is_file():
        check_file_content_bytes(log_file_test, "This is a log file without the target string.".encode('utf-8'), ".log file content")

    print(f"--- Self-Test Verification Summary: {passed_checks} PASSED, {failed_checks} FAILED ---")
    if failed_checks > 0:
        raise AssertionError(f"Self-test failed with {failed_checks} assertion(s).")
    return True


@flow#(name="Self-Test Find and Replace Flow", log_prints=True) 
def self_test_flow(temp_dir_str: str, dry_run_for_test: bool, process_binary_for_test: bool) -> None:
    temp_dir = Path(temp_dir_str)
    _create_self_test_environment(temp_dir)

    test_find, test_replace = "flojoy", "atlasvibe"
    # Include .log for the no_flojoy_here.log test to ensure it's scanned (but not modified)
    test_extensions = [".txt", ".py", ".md", ".bin", ".log"] 
    test_excluded_dirs: List[str] = [] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt"] 
    test_is_regex, test_case_sensitive = False, False # For the special flojoy->atlasvibe

    transaction_json_path_test = temp_dir / SELF_TEST_TRANSACTION_FILE_NAME
    validation_json_path_test = temp_dir / SELF_TEST_VALIDATION_FILE_NAME

    # Scan 1
    collected_tx1 = scan_and_collect_occurrences_task( 
        root_dir=temp_dir, find_pattern=test_find, replace_pattern=test_replace,
        is_regex=test_is_regex, case_sensitive=test_case_sensitive,
        excluded_dirs=test_excluded_dirs, excluded_files=test_excluded_files,
        file_extensions=test_extensions, process_binary_files=process_binary_for_test, scan_id="SelfTestPrimary"
    )
    compile_transactions_json_task( 
        transactions=collected_tx1, output_dir=temp_dir, filename=transaction_json_path_test.name
    )
    # Scan 2 (for determinism check)
    collected_tx2 = scan_and_collect_occurrences_task( 
        root_dir=temp_dir, find_pattern=test_find, replace_pattern=test_replace,
        is_regex=test_is_regex, case_sensitive=test_case_sensitive,
        excluded_dirs=test_excluded_dirs, excluded_files=test_excluded_files,
        file_extensions=test_extensions, process_binary_files=process_binary_for_test, scan_id="SelfTestValidation"
    )
    compile_transactions_json_task( 
        transactions=collected_tx2, output_dir=temp_dir, filename=validation_json_path_test.name
    )
    # Compare scans
    compare_transaction_files_task(transaction_json_path_test, validation_json_path_test) 

    if not transaction_json_path_test.exists(): 
        # This should not happen if compilation was successful
        print("ERROR: Primary transaction JSON for self-test not found after compilation.")
        return
    
    # Execute renames
    rename_result_obj = execute_rename_transactions_task( 
        json_file_path=transaction_json_path_test, root_dir=temp_dir, dry_run=dry_run_for_test,
        validation_json_path=validation_json_path_test # Pass for consistency, though not strictly used by execute
    )
    # Handle Prefect future if Prefect is running, or direct result if not
    path_map_result: Any = rename_result_obj.result() if hasattr(rename_result_obj, 'result') and callable(rename_result_obj.result) else rename_result_obj
    path_map: Dict[str, str] = path_map_result.get("path_translation_map", {}) if isinstance(path_map_result, dict) else {}
    
    # Execute content changes
    execute_content_transactions_task( 
        json_file_path=transaction_json_path_test, root_dir=temp_dir, dry_run=dry_run_for_test,
        path_translation_map=path_map, process_binary_files=process_binary_for_test,
        find_pattern=test_find, replace_pattern=test_replace, 
        is_regex=test_is_regex, case_sensitive=test_case_sensitive,
        validation_json_path=validation_json_path_test # Pass for consistency
    )
    
    if not dry_run_for_test: 
        _verify_self_test_results_task(temp_dir=temp_dir, process_binary_files=process_binary_for_test) 


# --- Main Prefect Flow ---

@flow(name="Mass Find and Replace Flow - Phased", log_prints=True) 
def find_and_replace_phased_flow(
    directory: str, find_pattern: str, replace_pattern: str, 
    extensions: Optional[List[str]], exclude_dirs: List[str], exclude_files: List[str],
    is_regex: bool, case_sensitive: bool, dry_run: bool,
    skip_scan: bool, process_binary_files: bool, force_execution: bool 
    ) -> None:
    root_dir = Path(directory).resolve(strict=False) # Allow non-existent for some dry-run info? No, better to fail early.
    if not root_dir.is_dir():
        print(f"Error: Root directory '{root_dir}' does not exist or is not a directory.")
        return

    transaction_json_path = root_dir / TRANSACTION_FILE_NAME
    validation_json_path = root_dir / VALIDATION_TRANSACTION_FILE_NAME

    if not dry_run and not force_execution:
        # Confirmation prompt
        print("--- Proposed Operation ---")
        print(f"Root Directory: {root_dir}")
        print(f"Find Pattern: '{find_pattern}' (Regex: {is_regex}, Case-Sensitive: {case_sensitive or (find_pattern.lower() == 'flojoy' and not is_regex)})") # Special case for flojoy
        print(f"Replace Pattern: '{replace_pattern}'")
        print(f"File Extensions: {extensions if extensions else 'All text-like (binary excluded unless specified)'}")
        print(f"Exclude Dirs: {exclude_dirs}")
        print(f"Exclude Files: {exclude_files}")
        print(f"Process Binary Files: {process_binary_files}")
        print("-------------------------")
        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes': 
            print("Operation cancelled by user.")
            return
    
    if not skip_scan:
        print(f"Starting scan phase in '{root_dir}'...")
        # Scan 1
        collected_tx1 = scan_and_collect_occurrences_task( 
            root_dir=root_dir, find_pattern=find_pattern, replace_pattern=replace_pattern,
            is_regex=is_regex, case_sensitive=case_sensitive,
            excluded_dirs=exclude_dirs, excluded_files=exclude_files,
            file_extensions=extensions, process_binary_files=process_binary_files, scan_id="Primary"
        )
        compile_transactions_json_task( 
            transactions=collected_tx1, output_dir=root_dir, filename=TRANSACTION_FILE_NAME
        )
        print(f"Primary transaction plan saved to '{transaction_json_path}'")
        
        # Scan 2 (for determinism check)
        collected_tx2 = scan_and_collect_occurrences_task( 
            root_dir=root_dir, find_pattern=find_pattern, replace_pattern=replace_pattern,
            is_regex=is_regex, case_sensitive=case_sensitive,
            excluded_dirs=exclude_dirs, excluded_files=exclude_files,
            file_extensions=extensions, process_binary_files=process_binary_files, scan_id="Validation"
        )
        compile_transactions_json_task( 
            transactions=collected_tx2, output_dir=root_dir, filename=VALIDATION_TRANSACTION_FILE_NAME
        )
        print(f"Validation transaction plan saved to '{validation_json_path}'")
        
        try:
            compare_transaction_files_task(transaction_json_path, validation_json_path) 
            print("Scan determinism check PASSED: Transaction plans are consistent.")
        except ValueError as e:
            print(f"Scan determinism check FAILED: {e}")
            print("Aborting due to inconsistent scan results. Please review the transaction files.")
            return 
        except FileNotFoundError as e:
            print(f"Error: Missing transaction files for comparison: {e}")
            return

    elif not transaction_json_path.exists() or not validation_json_path.exists():
        print(f"Error: --skip-scan was used, but '{transaction_json_path}' or '{validation_json_path}' not found.")
        return
    else:
        print(f"Skipping scan phase. Using existing transaction files: '{transaction_json_path}' and '{validation_json_path}'.")

    print("Starting execution phase...")
    # Execute renames
    rename_result_obj = execute_rename_transactions_task( 
        json_file_path=transaction_json_path, root_dir=root_dir, dry_run=dry_run,
        validation_json_path=validation_json_path 
    )
    path_map_result: Any = rename_result_obj.result() if hasattr(rename_result_obj, 'result') and callable(rename_result_obj.result) else rename_result_obj
    path_map: Dict[str, str] = path_map_result.get("path_translation_map", {}) if isinstance(path_map_result, dict) else {}
    rename_stats = {k: v for k, v in path_map_result.items() if k != "path_translation_map"}
    print(f"Rename transactions summary: {rename_stats}")
    
    # Execute content changes
    content_stats_obj = execute_content_transactions_task( 
        json_file_path=transaction_json_path, root_dir=root_dir, dry_run=dry_run,
        path_translation_map=path_map, process_binary_files=process_binary_files,
        find_pattern=find_pattern, replace_pattern=replace_pattern, 
        is_regex=is_regex, case_sensitive=case_sensitive,
        validation_json_path=validation_json_path
    )
    content_stats: Any = content_stats_obj.result() if hasattr(content_stats_obj, 'result') and callable(content_stats_obj.result) else content_stats_obj
    print(f"Content transactions summary: {content_stats}")

    if dry_run:
        print("Dry run complete. No actual changes were made.")
        print(f"Review '{transaction_json_path}' for planned changes.")
    else:
        print("Execution phase complete. Changes have been applied.")
        print(f"Review '{transaction_json_path}' for a log of applied changes and their statuses.")

# --- Main Execution ---
def main() -> None:
    script_path_obj = Path(__file__).resolve(strict=False) # Get script path early

    epilog_text = """
Usage Examples:

1. Default (replace 'flojoy' with 'atlasvibe' in current dir, case-preserving, excluding .git):
   python mass_find_replace.py

2. Specific find/replace in './my_project', only .py and .md files, case-sensitive:
   python mass_find_replace.py ./my_project "OldText" "NewText" --extensions .py .md --case-sensitive

3. Regex replace, excluding '.venv' and 'build' dirs, dry run:
   python mass_find_replace.py . "version_(\\d+)" "version_v\\1" --is-regex --exclude-dirs .git .venv build --dry-run

4. Use an existing transaction file (skip scan), force execution:
   python mass_find_replace.py ./my_project "flojoy" "atlasvibe" --skip-scan --force

5. Run self-test (creates temp dir, tests 'flojoy'->'atlasvibe' case preservation):
   python mass_find_replace.py --self-test
   python mass_find_replace.py --self-test --dry-run  (to see what self-test would do)
   python mass_find_replace.py --self-test --process-binary-files (to test binary processing in self-test)

Special 'flojoy' -> 'atlasvibe' case-preserving behavior:
  This is active by default when:
  - find_pattern is 'flojoy' (case-insensitive match)
  - replace_pattern is 'atlasvibe'
  - --is-regex is NOT used
  - --case-sensitive is NOT used (this flag is effectively ignored for the find part of flojoy->atlasvibe)
  It will replace:
    'flojoy' -> 'atlasvibe', 'Flojoy' -> 'Atlasvibe', 'FLOJOY' -> 'ATLASVIBE',
    'FloJoy' -> 'AtlasVibe', 'floJoy' -> 'atlasVibe'
  This applies to file/folder names and content.

IMPORTANT: ALWAYS back up your project before running without --dry-run.
Requires 'prefect' and 'chardet' libraries: pip install prefect chardet
"""
    parser = argparse.ArgumentParser(
        description="Phased find and replace script for files and directories, with Prefect integration and special case-preserving for 'flojoy'->'atlasvibe'.",
        epilog=epilog_text,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("directory", nargs='?', default=".", 
                        help="The root directory to process (default: current directory).")
    parser.add_argument("find_pattern", nargs='?', default="flojoy", 
                        help="The text or regex pattern to find (default: 'flojoy').")
    parser.add_argument("replace_pattern", nargs='?', default="atlasvibe", 
                        help="The text to replace with (default: 'atlasvibe').")
    
    parser.add_argument("--extensions", nargs="+", 
                        help="List of file extensions to process (e.g., .py .txt). Processes all text-like files if not specified, respecting binary detection.")
    parser.add_argument("--exclude-dirs", nargs="+", default=[".git"], 
                        help="Directory names to exclude (default: ['.git']). Add others like .venv, node_modules, build, dist, out, docs as needed.")
    parser.add_argument("--exclude-files", nargs="+", default=[], 
                        help="Specific file paths (relative to root) to exclude from all operations.")
    parser.add_argument("--is-regex", action="store_true", 
                        help="Treat find_pattern as a regular expression.")
    parser.add_argument("--case-sensitive", action="store_true", 
                        help="Perform case-sensitive matching for generic replacements. Ignored if special 'flojoy'->'atlasvibe' logic is active (which is case-insensitive for find).")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Scan and plan changes, but do not execute them. Outputs actions to log and transaction JSON.")
    parser.add_argument("--skip-scan", action="store_true", 
                        help=f"Skip scan and compile phase; use existing '{TRANSACTION_FILE_NAME}' and '{VALIDATION_TRANSACTION_FILE_NAME}'.")
    parser.add_argument("--process-binary-files", action="store_true", 
                        help="Attempt content replacement in files detected as binary. Use with extreme caution as this can corrupt files.")
    parser.add_argument("--force", "--yes", "-y", action="store_true", 
                        help="Force execution without confirmation prompt (if not in dry-run mode).")
    parser.add_argument("--self-test", "--self-check", action="store_true", 
                        help="Run a predefined self-test in a temporary directory to verify script logic. Other arguments are ignored except --dry-run and --process-binary-files.")

    args = parser.parse_args()

    # --- Self-Test Execution ---
    if args.self_test or args.self_check:
        print("Running self-test...")
        with tempfile.TemporaryDirectory(prefix="mass_replace_self_test_") as tmpdir_str:
            tmpdir_path = Path(tmpdir_str)
            try:
                self_test_flow(
                    temp_dir_str=str(tmpdir_path), 
                    dry_run_for_test=args.dry_run, 
                    process_binary_for_test=args.process_binary_files
                )
                if not args.dry_run: # Verification only happens if not a dry run self-test
                     print("Self-test PASSED.")
                else:
                     print("Self-test dry run complete. Review transaction files in temp dir if needed (usually auto-deleted).")
            except AssertionError as e:
                print(f"Self-test FAILED: {e}")
                sys.exit(1) # Exit with error code if self-test fails
            except Exception as e:
                print(f"Self-test ERRORED: {e}")
                sys.exit(1)
        return # Exit after self-test

    # --- Regular Operation ---
    # Add default transaction log files to exclusions for main operations
    # This should happen *after* self-test argument parsing.
    default_log_files_to_exclude = [
        TRANSACTION_FILE_NAME, 
        VALIDATION_TRANSACTION_FILE_NAME,
        TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT,
        VALIDATION_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT
    ]
    for log_file in default_log_files_to_exclude:
        if log_file not in args.exclude_files:
            args.exclude_files.append(log_file)

    # Robust script self-exclusion (if script is in target directory)
    try:
        # Only attempt self-exclusion if a directory is provided and exists
        if args.directory and Path(args.directory).exists(): 
            target_dir_resolved = Path(args.directory).resolve(strict=True) 
            if script_path_obj.is_file(): # Ensure script_path_obj is a file
                script_resolved = script_path_obj.resolve(strict=True)
                # Check if script is directly in target_dir or a sub-directory
                if script_resolved.parent == target_dir_resolved: 
                    if script_path_obj.name not in args.exclude_files:
                        args.exclude_files.append(script_path_obj.name)
                elif target_dir_resolved in script_resolved.parents: # script is in a sub-folder of target_dir
                    try:
                        script_relative_to_target = str(script_resolved.relative_to(target_dir_resolved))
                        if script_relative_to_target not in args.exclude_files:
                            args.exclude_files.append(script_relative_to_target)
                    except ValueError: # Should not happen if target_dir_resolved is an ancestor
                        pass
    except FileNotFoundError: 
         pass # Silently skip if target dir not found during self-exclusion setup
    except Exception: # Catch any other error during self-exclusion setup
        pass 

    # Proceed with the main flow
    find_and_replace_phased_flow(
        directory=args.directory, find_pattern=args.find_pattern, replace_pattern=args.replace_pattern,
        extensions=args.extensions, exclude_dirs=args.exclude_dirs, exclude_files=args.exclude_files,
        is_regex=args.is_regex, case_sensitive=args.case_sensitive, dry_run=args.dry_run,
        skip_scan=args.skip_scan, process_binary_files=args.process_binary_files,
        force_execution=args.force
    )

if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"Critical dependency missing: {e}")
        print("Please install required libraries, e.g., 'pip install prefect chardet'")
        sys.exit(1)
    except Exception as e: # Catch-all for unexpected errors in main
        print(f"An unexpected error occurred: {e}")
        # Consider logging traceback here for debugging
        sys.exit(1)
