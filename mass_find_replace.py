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
task_real = None
flow_real = None
task_dummy = None
flow_dummy = None

try:
    from prefect import task as _task_real_import, flow as _flow_real_import

    # Canary test for the @flow decorator
    @_flow_real_import
    def _canary_flow_for_init():
        pass
    # If the above definition didn't raise an error, assign the real ones
    task = _task_real_import
    flow = _flow_real_import
except (ImportError, TypeError):
    def _task_dummy_impl(fn: Callable[..., Any]) -> Callable[..., Any]: return fn
    def _flow_dummy_impl(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]: return fn
        return decorator
    task = _task_dummy_impl
    flow = _flow_dummy_impl

# Ensure task and flow are always defined, even if try-except had an issue.
if task is None:
    def _task_final_fallback(fn: Callable[..., Any]) -> Callable[..., Any]: return fn
    task = _task_final_fallback
if flow is None:
    def _flow_final_fallback(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]: return fn
        return decorator
    flow = _flow_final_fallback


# Chardet integration for encoding detection
CHARDET_AVAILABLE = False
try:
    import chardet
    CHARDET_AVAILABLE = True 
except ImportError:
    print("ERROR: chardet library not found. This script requires chardet for robust encoding detection.")
    print("Please install it by running: pip install chardet")
    sys.exit(1)


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
DEFAULT_ENCODING_FALLBACK = 'utf-8' # Should ideally not be used if chardet is mandatory

# --- Core Helper Functions (Shared Logic) ---

def get_file_encoding(file_path: Path, sample_size: int = 10240) -> Optional[str]:
    """Detects file encoding using chardet."""
    # Assumes chardet is available due to check at script start
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size) 
        if not raw_data:
            # Fallback for empty files, though chardet might handle this.
            # Consider if empty files should have a specific encoding or be skipped.
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
                # Validate if Python can actually use this encoding
                b"test".decode(encoding) 
                return encoding 
            except LookupError:
                # If chardet suggests an encoding Python doesn't know, fallback or error
                # For now, falling back to UTF-8 as a last resort before None
                return DEFAULT_ENCODING_FALLBACK 
        else:
            # Low confidence or no encoding detected, try UTF-8 as a common default
            try:
                raw_data.decode('utf-8') 
                return 'utf-8'
            except UnicodeDecodeError:
                # If UTF-8 fails, we can't reliably determine encoding
                return None 
    except Exception:
        # Broad exception for any file I/O or chardet internal errors
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
        return base_replace.lower() 
    
    if matched_text.islower(): 
        return base_replace.lower()
    if matched_text.isupper(): 
        return base_replace.upper()
    if matched_text.istitle(): 
        return base_replace.title()
    if matched_text and base_replace: 
        if matched_text[0].isupper() and not base_replace[0].isupper():
            return base_replace[0].upper() + base_replace[1:]
        if matched_text[0].islower() and not base_replace[0].islower():
            return base_replace[0].lower() + base_replace[1:]
    return base_replace 

def perform_text_replacement(text: str, find_pattern: str, replace_pattern: str, is_regex: bool, case_sensitive: bool) -> str:
    """Performs text replacement, calling case-preservation logic if applicable."""
    if (not is_regex and 
        not case_sensitive and 
        find_pattern.lower() == 'flojoy' and 
        replace_pattern.lower() == 'atlasvibe'):
        def replace_func(match_obj: re.Match[str]) -> str:
            return _get_case_preserved_replacement(match_obj.group(0), 'flojoy', 'atlasvibe')
        return re.sub(r'flojoy', replace_func, text, flags=re.IGNORECASE)
    else:
        flags = 0 if case_sensitive else re.IGNORECASE
        if is_regex:
            return re.sub(find_pattern, replace_pattern, text, flags=flags)
        else: 
            if not case_sensitive:
                return re.sub(re.escape(find_pattern), replace_pattern, text, flags=re.IGNORECASE)
            else:
                return text.replace(find_pattern, replace_pattern)

def _text_contains_pattern(text_to_search: str, find_pattern: str, is_regex: bool, case_sensitive: bool) -> bool:
    """Helper to check if text contains the find_pattern with given options."""
    if is_regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        return bool(re.search(find_pattern, text_to_search, flags))
    else: 
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
                if resolved_item_path == excluded_dir or resolved_item_path.is_relative_to(excluded_dir):
                    is_excluded = True
                    break
        except (ValueError, OSError): 
            item_path_str = str(item_path) 
            if any(item_path_str.startswith(str(ex_dir)) for ex_dir in abs_excluded_dirs):
                 is_excluded = True
        if is_excluded:
            continue
        yield item_path

def _get_current_absolute_path(original_relative_path_str: str, root_dir: Path, path_translation_map: Dict[str, str]) -> Path:
    """
    Determines the current absolute path of an item, considering parent renames
    recorded in the path_translation_map.
    path_translation_map stores: original_relative_path_str -> new_relative_path_str
    """
    current_path_to_check_str = original_relative_path_str
    temp_original_rel_path = Path(original_relative_path_str)
    
    for i in range(len(temp_original_rel_path.parts), -1, -1):
        ancestor_original_rel_str = str(Path(*temp_original_rel_path.parts[:i])) if i > 0 else ""
        if ancestor_original_rel_str == ".": 
            ancestor_original_rel_str = ""

        if ancestor_original_rel_str in path_translation_map:
            translated_ancestor_rel_str = path_translation_map[ancestor_original_rel_str]
            if ancestor_original_rel_str:
                segment_after_ancestor = temp_original_rel_path.relative_to(Path(ancestor_original_rel_str))
            else: 
                segment_after_ancestor = temp_original_rel_path
            current_path_to_check_str = str(Path(translated_ancestor_rel_str) / segment_after_ancestor)
            break
            
    return root_dir.joinpath(current_path_to_check_str)

# --- Phase 1: Scan & Collect Tasks ---

@task
def scan_and_collect_occurrences_task(
    root_dir: Path, find_pattern: str, replace_pattern: str, is_regex: bool, case_sensitive: bool,
    excluded_dirs: List[str], excluded_files: List[str], file_extensions: Optional[List[str]],
    process_binary_files: bool, scan_id: str 
) -> List[Dict[str, Any]]:
    transactions: List[Dict[str, Any]] = []
    abs_excluded_files = [root_dir.joinpath(f).resolve(strict=False) for f in excluded_files]

    path_candidates_for_rename = sorted(
        list(_walk_for_scan(root_dir, excluded_dirs)), key=lambda p: len(p.parts), reverse=True
    )

    for item_path in path_candidates_for_rename:
        try:
            relative_path_str = str(item_path.relative_to(root_dir))
        except ValueError: 
            continue
        original_name = item_path.name
        
        if item_path.is_file() and item_path.resolve(strict=False) in abs_excluded_files:
            continue

        if item_path.is_file() and file_extensions:
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
                    "LINE_NUMBER": 0, "ORIGINAL_LINE_CONTENT": None, "PROPOSED_LINE_CONTENT": None,
                    "FIND_PATTERN": find_pattern, "REPLACE_PATTERN": replace_pattern,
                    "IS_REGEX": is_regex, "CASE_SENSITIVE": case_sensitive, "STATUS": STATUS_PENDING
                })

    for item_path in _walk_for_scan(root_dir, excluded_dirs):
        if not item_path.is_file(): 
            continue
        
        try:
            relative_path_str = str(item_path.relative_to(root_dir))
        except ValueError:
            continue

        if item_path.resolve(strict=False) in abs_excluded_files:
            continue
        if file_extensions and (not item_path.suffix or item_path.suffix.lower() not in [ext.lower() for ext in file_extensions]):
            continue
        
        if not process_binary_files and is_likely_binary_file(item_path):
            continue

        original_encoding = get_file_encoding(item_path)
        current_encoding_to_try = original_encoding or DEFAULT_ENCODING_FALLBACK 

        try:
            file_content_bytes = item_path.read_bytes()
            file_content_str = file_content_bytes.decode(current_encoding_to_try, errors='surrogateescape')
            
            if _text_contains_pattern(file_content_str, find_pattern, is_regex, case_sensitive):
                transactions.append({
                    "id": str(uuid.uuid4()), "OCCURRENCE_TYPE": "STRING_IN_FILE", 
                    "PATH": relative_path_str, "NEW_PATH_COMPONENT": None,
                    "LINE_NUMBER": 0, 
                    "ORIGINAL_LINE_CONTENT": None, 
                    "PROPOSED_LINE_CONTENT": None, 
                    "ORIGINAL_ENCODING": original_encoding, 
                    "FIND_PATTERN": find_pattern, "REPLACE_PATTERN": replace_pattern,
                    "IS_REGEX": is_regex, "CASE_SENSITIVE": case_sensitive, "STATUS": STATUS_PENDING
                })
        except Exception: 
            pass # Silently skip files that cannot be processed
            
    return transactions

# --- Phase 2: Compile JSON Task & Compare ---

@task
def compile_transactions_json_task(transactions: List[Dict[str, Any]], output_dir: Path, filename: str) -> Path:
    def sort_key(t: Dict[str, Any]) -> Tuple[int, int, str, int]: 
        path_depth = t["PATH"].count(os.sep)
        type_order = {"FOLDERNAME": 0, "FILENAME": 1, "STRING_IN_FILE": 2}
        return (type_order[t["OCCURRENCE_TYPE"]], path_depth, t["PATH"], t.get("LINE_NUMBER", 0))

    transactions.sort(key=sort_key)
    
    json_file_path = output_dir / filename
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=4)
    except Exception as e:
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
        
        def comparable_tx(tx_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return sorted([ {k: v for k, v in tx.items() if k not in ['id', 'STATUS']} for tx in tx_list ], 
                          key=lambda x: (x['OCCURRENCE_TYPE'], x['PATH'], x.get('LINE_NUMBER', 0), x.get('ORIGINAL_LINE_CONTENT', '')))

        comp_data1 = comparable_tx(data1)
        comp_data2 = comparable_tx(data2)

        if comp_data1 == comp_data2:
            return True
        else:
            raise ValueError("Scan determinism check failed: Transaction plans differ.")
            
    except Exception as e:
        raise

# --- Phase 3: Execute Transactions Tasks ---

def _load_transactions_with_fallback(json_file_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Loads transactions from primary JSON, falls back to .bak on error."""
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    try:
        if json_file_path.exists():
            with open(json_file_path, 'r', encoding='utf-8') as f:
                return cast(List[Dict[str, Any]], json.load(f))
        elif backup_path.exists():
            with open(backup_path, 'r', encoding='utf-8') as f:
                return cast(List[Dict[str, Any]], json.load(f))
        else:
            return None
    except json.JSONDecodeError:
        if backup_path.exists():
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    return cast(List[Dict[str, Any]], json.load(f))
            except Exception:
                pass
        return None
    except Exception:
        return None


def _update_transaction_status_in_json(json_file_path: Path, transaction_id: str, new_status: str, error_message: Optional[str] = None) -> None:
    """Updates status, creating a backup first."""
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    
    if not json_file_path.exists():
        if backup_path.exists():
            pass # Primary file missing, but backup exists.
        return

    try:
        if json_file_path.exists(): 
            shutil.copy2(json_file_path, backup_path) 
    except Exception:
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
                    else: 
                        t_item.pop('ERROR_MESSAGE', None) 
                    updated = True
                    break
            if updated:
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
            else:
                pass # Transaction ID not found
    except Exception:
        try:
            shutil.copy2(backup_path, json_file_path)
        except Exception:
            pass # Failed to restore


@task 
def execute_rename_transactions_task(
    json_file_path: Path, root_dir: Path, dry_run: bool,
    validation_json_path: Optional[Path] = None 
) -> Dict[str, Any]:
    transactions = _load_transactions_with_fallback(json_file_path)
    if transactions is None:
        return {"completed": 0, "failed": 0, "skipped": 0, "path_translation_map": {}}

    validation_tx_map_by_id: Dict[str, Dict[str, Any]] = {}
    if validation_json_path and validation_json_path.exists():
        try:
            with open(validation_json_path, 'r', encoding='utf-8') as vf: 
                validation_data = json.load(vf)
            validation_tx_map_by_id = {tx_val['id']: tx_val for tx_val in validation_data}
        except Exception: 
            pass

    rename_txs = [t for t in transactions if t["OCCURRENCE_TYPE"] in ["FOLDERNAME", "FILENAME"] and t["STATUS"] == STATUS_PENDING]
    completed_count, failed_count, skipped_count = 0, 0, 0
    path_translation_map: Dict[str, str] = {} 

    for tx_from_primary in rename_txs:
        tx_id = tx_from_primary.get("id")
        tx = tx_from_primary
        if not all(k in tx_from_primary for k in ["PATH", "NEW_PATH_COMPONENT"]) and tx_id and validation_tx_map_by_id:
            pristine_tx = validation_tx_map_by_id.get(tx_id)
            if pristine_tx and all(k in pristine_tx for k in ["PATH", "NEW_PATH_COMPONENT"]): 
                tx = pristine_tx
            else:
                if tx_id: 
                    _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete")
                failed_count += 1
                continue
        elif not all(k in tx_from_primary for k in ["PATH", "NEW_PATH_COMPONENT"]):
             if tx_id: 
                 _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete")
             failed_count += 1
             continue

        original_relative_path_str = tx["PATH"]
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map)
        
        if not current_abs_path.exists():
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_SKIPPED, "Original path not found")
            skipped_count += 1
            continue

        proposed_new_name_component = tx["NEW_PATH_COMPONENT"]
        new_abs_path = current_abs_path.with_name(proposed_new_name_component)

        if dry_run:
            path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_COMPLETED + " (DRY_RUN)")
            completed_count += 1
            continue

        if new_abs_path.exists() and current_abs_path.resolve(strict=False) != new_abs_path.resolve(strict=False):
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_SKIPPED, "Target path already exists")
            skipped_count += 1
            continue
        
        try:
            if not new_abs_path.parent.exists(): 
                os.makedirs(new_abs_path.parent, exist_ok=True)
            os.rename(current_abs_path, new_abs_path)
            path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_COMPLETED)
            completed_count += 1
        except Exception as e:
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_FAILED, str(e))
            failed_count += 1

    return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count, "path_translation_map": path_translation_map}


@task 
def execute_content_transactions_task(
    json_file_path: Path, root_dir: Path, dry_run: bool,
    path_translation_map: Dict[str, str], process_binary_files: bool,
    find_pattern: str, replace_pattern: str, is_regex: bool, case_sensitive: bool,
    validation_json_path: Optional[Path] = None 
) -> Dict[str, int]:
    transactions = _load_transactions_with_fallback(json_file_path)
    if transactions is None:
        return {"completed": 0, "failed": 0, "skipped": 0}

    validation_tx_map_by_id: Dict[str, Dict[str, Any]] = {}
    if validation_json_path and validation_json_path.exists():
        try:
            with open(validation_json_path, 'r', encoding='utf-8') as vf: 
                validation_data = json.load(vf)
            validation_tx_map_by_id = {tx_val['id']: tx_val for tx_val in validation_data}
        except Exception: 
            pass
            
    file_to_process_details: Dict[str, Dict[str, Any]] = {} 

    for tx_from_primary in transactions:
        if tx_from_primary["OCCURRENCE_TYPE"] == "STRING_IN_FILE" and tx_from_primary["STATUS"] == STATUS_PENDING:
            tx_id = tx_from_primary.get("id")
            tx_data_to_use = tx_from_primary
            if not all(k in tx_from_primary for k in ["PATH"]) and tx_id and validation_tx_map_by_id: 
                pristine_tx = validation_tx_map_by_id.get(tx_id)
                if pristine_tx and all(k in pristine_tx for k in ["PATH"]): 
                    tx_data_to_use = pristine_tx
                else:
                    if tx_id: 
                        _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete")
                    continue 
            elif not all(k in tx_from_primary for k in ["PATH"]):
                 if tx_id: 
                     _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete")
                 continue

            original_rel_path = tx_data_to_use["PATH"]
            if original_rel_path not in file_to_process_details:
                file_to_process_details[original_rel_path] = {
                    "tx_ids": [], "encoding": tx_data_to_use.get("ORIGINAL_ENCODING")
                }
            file_to_process_details[original_rel_path]["tx_ids"].append(tx_id) 
            
    completed_count, failed_count, skipped_count = 0, 0, 0

    for original_relative_path_str, details in file_to_process_details.items():
        tx_ids_for_file = details["tx_ids"]
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map)

        if not current_abs_path.is_file(): 
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, "File path not found or not a file after renames")
            skipped_count += len(tx_ids_for_file)
            continue

        if not process_binary_files and is_likely_binary_file(current_abs_path):
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, "Skipped binary file")
            skipped_count += len(tx_ids_for_file)
            continue
            
        original_encoding = details["encoding"]
        current_encoding_to_try = original_encoding or DEFAULT_ENCODING_FALLBACK

        if dry_run:
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_COMPLETED + " (DRY_RUN)")
            completed_count += len(tx_ids_for_file)
            continue

        try:
            original_full_bytes = current_abs_path.read_bytes()
            original_full_content_str = original_full_bytes.decode(current_encoding_to_try, errors='surrogateescape')
            
            modified_full_content_str = perform_text_replacement(
                original_full_content_str, find_pattern, replace_pattern, is_regex, case_sensitive
            )

            if modified_full_content_str != original_full_content_str:
                modified_bytes = modified_full_content_str.encode(current_encoding_to_try, errors='surrogateescape')
                current_abs_path.write_bytes(modified_bytes)
                for tx_id in tx_ids_for_file: 
                    _update_transaction_status_in_json(json_file_path, tx_id, STATUS_COMPLETED)
                completed_count += len(tx_ids_for_file)
            else: 
                for tx_id in tx_ids_for_file: 
                    _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, "No change to file content")
                skipped_count += len(tx_ids_for_file)
        except Exception as e: 
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, str(e))
            failed_count += len(tx_ids_for_file)
            
    return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count}


# --- Self-Test Functionality ---
def _create_self_test_environment(base_dir: Path) -> None:
    (base_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir").mkdir(parents=True)
    (base_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file_mixed_eol.txt").write_text(
        "flojoy line 1\r\nFLOJOY line 2\nFlojoy line 3\r\nFloJoy line 4\nfloJoy line 5\nmyflojoy_project details"
    ) 
    (base_dir / "flojoy_root" / "another_flojoy_file.py").write_text(
        "import flojoy_lib\nclass MyFlojoyClass: pass\nFLOJOY_CONSTANT = 100\n# trailing spaces flojoy  \n"
    )
    (base_dir / "only_name_flojoy.md").write_text("No relevant content.")
    (base_dir / "only_content.txt").write_text("Line with flojoy here.\nAnother line with Flojoy.")
    (base_dir / "multiple_on_line_flojoy.txt").write_text("flojoy flojoy Flojoy FLOJOY floJoy FloJoy")
    (base_dir / "empty_flojoy_file.txt").touch()
    (base_dir / "FLOJOY_is_the_name_folder").mkdir()
    (base_dir / "FLOJOY_is_the_name_folder" / "file_in_FLOJOY_folder.txt").write_text("Some flojoy content.")
    (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")
    try:
        (base_dir / "latin1_flojoy_content.txt").write_text("café flojoy here\nAnother Flojoy line with accent aigu: é", encoding='latin-1')
        (base_dir / "cp1252_flojoy_content.txt").write_text("Euro € symbol with flojoy.", encoding='cp1252')
        sjis_text = "これはflojoyのテストです。\n次の行もFlojoyです。" 
        (base_dir / "sjis_flojoy_content.txt").write_text(sjis_text, encoding='shift_jis', errors='replace')
        gb18030_text = "你好 flojoy 世界\n这是 Flojoy 的一个例子" 
        (base_dir / "gb18030_flojoy_content.txt").write_text(gb18030_text, encoding='gb18030', errors='replace')
        invalid_utf8_bytes = b"ValidStart_flojoy_" + b"\xff\xfe" + b"_flojoy_ValidEnd" 
        (base_dir / "invalid_utf8_flojoy_file.txt").write_bytes(invalid_utf8_bytes)

    except Exception: 
        pass # Silently skip if encodings are not supported on the system
    (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in excluded file")
    (base_dir / "no_flojoy_here.log").write_text("This is a log file without the target string.") 

@task 
def _verify_self_test_results_task(temp_dir: Path, process_binary_files: bool, chardet_was_available: bool) -> bool:
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

    exp_paths = [
        temp_dir / "atlasvibe_root", temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder",
        temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir",
        temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file_mixed_eol.txt",
        temp_dir / "atlasvibe_root" / "another_atlasvibe_file.py",
        temp_dir / "only_name_atlasvibe.md", temp_dir / "binary_atlasvibe_file.bin",
        temp_dir / "latin1_atlasvibe_content.txt", temp_dir / "cp1252_atlasvibe_content.txt",
        temp_dir / "sjis_atlasvibe_content.txt", temp_dir / "gb18030_atlasvibe_content.txt",
        temp_dir / "invalid_utf8_atlasvibe_file.txt", 
        temp_dir / "empty_atlasvibe_file.txt", temp_dir / "ATLASVIBE_is_the_name_folder",
        temp_dir / "ATLASVIBE_is_the_name_folder" / "file_in_ATLASVIBE_folder.txt",
        temp_dir / "multiple_on_line_atlasvibe.txt"
    ]
    for p in exp_paths: 
        check(p.exists(), f"Path '{p.relative_to(temp_dir)}' exists.", f"Path '{p.relative_to(temp_dir)}' MISSING.")
    check(not (temp_dir / "flojoy_root").exists(), "Old 'flojoy_root' removed.", "Old 'flojoy_root' STILL EXISTS.")

    deep_file = temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file_mixed_eol.txt"
    if deep_file.is_file():
        raw_content_bytes = deep_file.read_bytes() 
        expected_text_content = "atlasvibe line 1\r\nATLASVIBE line 2\nAtlasvibe line 3\r\nAtlasVibe line 4\natlasVibe line 5\nmyatlasvibe_project details"
        expected_raw_bytes = expected_text_content.encode('utf-8') 
        check(raw_content_bytes == expected_raw_bytes, "Mixed EOL file content and EOLs preserved.", 
              f"Mixed EOL file content/EOLs NOT preserved. Expected: {expected_raw_bytes!r}, Got: {raw_content_bytes!r}")

    multiple_file = temp_dir / "multiple_on_line_atlasvibe.txt"
    if multiple_file.is_file():
        content = multiple_file.read_text(encoding='utf-8')
        expected_content = "atlasvibe atlasvibe Atlasvibe ATLASVIBE atlasVibe AtlasVibe"
        check(content.strip() == expected_content, "Multiple occurrences on one line handled.", f"Multiple on line INCORRECT: '{content.strip()}'")

    bin_file = temp_dir / "binary_atlasvibe_file.bin"
    if bin_file.is_file():
        bin_content = bin_file.read_bytes()
        original_bin_text_parts = (b"prefix_flojoy_suffix", b"flojoy_data")
        replaced_bin_text_parts = (b"prefix_atlasvibe_suffix", b"atlasvibe_data")
        binary_core = b"\x00\x01\x02"
        binary_end = b"\x03\x04"
        expected_after_replace = replaced_bin_text_parts[0] + binary_core + replaced_bin_text_parts[1] + binary_end
        expected_if_untouched = original_bin_text_parts[0] + binary_core + original_bin_text_parts[1] + binary_end
        if process_binary_files:
            check(bin_content == expected_after_replace, "Binary file content processed.", f"Binary file content processed INCORRECTLY. Got: {bin_content!r}")
        else:
            check(bin_content == expected_if_untouched, "Binary file content UNTOUCHED.", f"Binary file content MODIFIED. Got: {bin_content!r}")

    latin1_file = temp_dir / "latin1_atlasvibe_content.txt"
    if latin1_file.is_file():
        try:
            content = latin1_file.read_text(encoding='latin-1') 
            check("café atlasvibe here" in content and "Another Atlasvibe line with accent aigu: é" in content, 
                  "Latin-1 file content correct and encoding preserved.", 
                  f"Latin-1 file content/encoding INCORRECT. Content: {content[:100]}...")
        except Exception as e: 
            check(False, "", f"Could not read/verify latin-1 file: {e}")
    else: 
        check(False, "", "Renamed latin-1 file MISSING.")
    
    cp1252_file = temp_dir / "cp1252_atlasvibe_content.txt"
    if cp1252_file.is_file():
        try:
            content = cp1252_file.read_text(encoding='cp1252')
            check("Euro € symbol with atlasvibe." in content, "CP1252 file content correct and encoding preserved.", f"CP1252 file content/encoding INCORRECT: {content}")
        except Exception as e: 
            check(False, "", f"Could not read/verify cp1252 file: {e}")
    else: 
        check(False, "", "Renamed cp1252 file MISSING.")

    sjis_file_renamed = temp_dir / "sjis_atlasvibe_content.txt"
    if sjis_file_renamed.is_file():
        try:
            content = sjis_file_renamed.read_text(encoding='shift_jis', errors='replace')
            if chardet_was_available:
                expected_sjis_text = "これはatlasvibeのテストです。\n次の行もAtlasvibeです。"
                check(content == expected_sjis_text, "Shift-JIS file content correct (chardet available).", f"Shift-JIS file content INCORRECT (chardet available). Got: {content!r}")
            else: 
                expected_sjis_text_no_chardet = "これはflojoyのテストです。\n次の行もFlojoyです。"
                check(content == expected_sjis_text_no_chardet, "Shift-JIS file content unchanged as expected (chardet unavailable).", f"Shift-JIS file content UNEXPECTEDLY CHANGED (chardet unavailable). Got: {content!r}")
        except Exception as e: 
            check(False, "", f"Could not read/verify Shift-JIS file: {e}")
    else: 
        check(False, "", "Renamed Shift-JIS file MISSING.")

    gb18030_file_renamed = temp_dir / "gb18030_atlasvibe_content.txt"
    if gb18030_file_renamed.is_file():
        try:
            content = gb18030_file_renamed.read_text(encoding='gb18030', errors='replace')
            if chardet_was_available:
                expected_gb18030_text = "你好 atlasvibe 世界\n这是 Atlasvibe 的一个例子"
                check(content == expected_gb18030_text, "GB18030 file content correct (chardet available).", f"GB18030 file content INCORRECT (chardet available). Got: {content!r}")
            else: 
                expected_gb18030_text_no_chardet = "你好 flojoy 世界\n这是 Flojoy 的一个例子"
                check(content == expected_gb18030_text_no_chardet, "GB18030 file content unchanged as expected (chardet unavailable).", f"GB18030 file content UNEXPECTEDLY CHANGED (chardet unavailable). Got: {content!r}")
        except Exception as e: 
            check(False, "", f"Could not read/verify GB18030 file: {e}")
    else: 
        check(False, "", "Renamed GB18030 file MISSING.")
    
    invalid_utf8_file = temp_dir / "invalid_utf8_atlasvibe_file.txt" 
    if invalid_utf8_file.is_file():
        expected_bytes_after_replace = b"ValidStart_atlasvibe_" + b"\xff\xfe" + b"_atlasvibe_ValidEnd"
        try:
            content_bytes = invalid_utf8_file.read_bytes()
            check(content_bytes == expected_bytes_after_replace, 
                  "Invalid UTF-8 sequences preserved with surrogateescape.",
                  f"Invalid UTF-8 sequence preservation FAILED. Expected: {expected_bytes_after_replace!r}, Got: {content_bytes!r}")
        except Exception as e:
            check(False, "", f"Could not read/verify invalid_utf8_atlasvibe_file.txt: {e}")
    else:
        check(False, "", "invalid_utf8_atlasvibe_file.txt MISSING.")


    excluded_file = temp_dir / "exclude_this_flojoy_file.txt" 
    check(excluded_file.is_file(), "Excluded file still exists.", "Excluded file MISSING.")
    if excluded_file.is_file():
        check("flojoy content in excluded file" == excluded_file.read_text(), "Excluded file content unchanged.", "Excluded file content CHANGED.")
    
    log_file_test = temp_dir / "no_flojoy_here.log"
    check(log_file_test.is_file(), ".log file still exists.", ".log file MISSING.")
    if log_file_test.is_file():
        check("This is a log file without the target string." == log_file_test.read_text(), ".log file content unchanged.", ".log file content CHANGED.")

    print(f"--- Self-Test Verification Summary: {passed_checks} PASSED, {failed_checks} FAILED ---")
    if failed_checks > 0:
        raise AssertionError(f"Self-test failed with {failed_checks} assertion(s).")
    return True


@flow(name="Self-Test Find and Replace Flow", log_prints=True) 
def self_test_flow(temp_dir_str: str, dry_run_for_test: bool, process_binary_for_test: bool) -> None:
    temp_dir = Path(temp_dir_str)
    _create_self_test_environment(temp_dir)

    test_find, test_replace = "flojoy", "atlasvibe"
    test_extensions = [".txt", ".py", ".md", ".bin"] 
    test_excluded_dirs: List[str] = [] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt"] 
    test_is_regex, test_case_sensitive = False, False

    transaction_json_path_test = temp_dir / SELF_TEST_TRANSACTION_FILE_NAME
    validation_json_path_test = temp_dir / SELF_TEST_VALIDATION_FILE_NAME

    collected_tx1 = scan_and_collect_occurrences_task( 
        root_dir=temp_dir, find_pattern=test_find, replace_pattern=test_replace,
        is_regex=test_is_regex, case_sensitive=test_case_sensitive,
        excluded_dirs=test_excluded_dirs, excluded_files=test_excluded_files,
        file_extensions=test_extensions, process_binary_files=process_binary_for_test, scan_id="SelfTestPrimary"
    )
    compile_transactions_json_task( 
        transactions=collected_tx1, output_dir=temp_dir, filename=transaction_json_path_test.name
    )
    collected_tx2 = scan_and_collect_occurrences_task( 
        root_dir=temp_dir, find_pattern=test_find, replace_pattern=test_replace,
        is_regex=test_is_regex, case_sensitive=test_case_sensitive,
        excluded_dirs=test_excluded_dirs, excluded_files=test_excluded_files,
        file_extensions=test_extensions, process_binary_files=process_binary_for_test, scan_id="SelfTestValidation"
    )
    compile_transactions_json_task( 
        transactions=collected_tx2, output_dir=temp_dir, filename=validation_json_path_test.name
    )
    compare_transaction_files_task(transaction_json_path_test, validation_json_path_test) 

    if not transaction_json_path_test.exists(): 
        return
    
    rename_res = execute_rename_transactions_task( 
        json_file_path=transaction_json_path_test, root_dir=temp_dir, dry_run=dry_run_for_test,
        validation_json_path=validation_json_path_test
    )
    # Prefect tasks might return a future-like object if Prefect is active.
    # For no-op decorators, it's the direct result.
    path_map_result: Any = rename_res.result() if hasattr(rename_res, 'result') and callable(rename_res.result) else rename_res
    path_map: Dict[str, str] = path_map_result.get("path_translation_map", {}) if isinstance(path_map_result, dict) else {}
    
    execute_content_transactions_task( 
        json_file_path=transaction_json_path_test, root_dir=temp_dir, dry_run=dry_run_for_test,
        path_translation_map=path_map, process_binary_files=process_binary_for_test,
        find_pattern=test_find, replace_pattern=test_replace, 
        is_regex=test_is_regex, case_sensitive=test_case_sensitive,
        validation_json_path=validation_json_path_test
    )
    
    if not dry_run_for_test: 
        _verify_self_test_results_task(temp_dir=temp_dir, process_binary_files=process_binary_for_test, chardet_was_available=CHARDET_AVAILABLE) 


# --- Main Prefect Flow ---

@flow(name="Mass Find and Replace Flow - Phased", log_prints=True) 
def find_and_replace_phased_flow(
    directory: str, find_pattern: str, replace_pattern: str, 
    extensions: Optional[List[str]], exclude_dirs: List[str], exclude_files: List[str],
    is_regex: bool, case_sensitive: bool, dry_run: bool,
    skip_scan: bool, process_binary_files: bool, force_execution: bool 
    ) -> None:
    root_dir = Path(directory).resolve(strict=False) 
    transaction_json_path = root_dir / TRANSACTION_FILE_NAME
    validation_json_path = root_dir / VALIDATION_TRANSACTION_FILE_NAME

    if dry_run: 
        pass
    elif not force_execution:
        confirm = input(f"Modifying '{root_dir}'. Find '{find_pattern}', Replace '{replace_pattern}'. Backup? Continue? (yes/no): ")
        if confirm.lower() != 'yes': 
            return
    else: 
        pass # Force execution

    if not skip_scan:
        if not root_dir.is_dir(): 
            return
        collected_tx1 = scan_and_collect_occurrences_task( 
            root_dir=root_dir, find_pattern=find_pattern, replace_pattern=replace_pattern,
            is_regex=is_regex, case_sensitive=case_sensitive,
            excluded_dirs=exclude_dirs, excluded_files=exclude_files,
            file_extensions=extensions, process_binary_files=process_binary_files, scan_id="Primary"
        )
        compile_transactions_json_task( 
            transactions=collected_tx1, output_dir=root_dir, filename=TRANSACTION_FILE_NAME
        )
        collected_tx2 = scan_and_collect_occurrences_task( 
            root_dir=root_dir, find_pattern=find_pattern, replace_pattern=replace_pattern,
            is_regex=is_regex, case_sensitive=case_sensitive,
            excluded_dirs=exclude_dirs, excluded_files=exclude_files,
            file_extensions=extensions, process_binary_files=process_binary_files, scan_id="Validation"
        )
        compile_transactions_json_task( 
            transactions=collected_tx2, output_dir=root_dir, filename=VALIDATION_TRANSACTION_FILE_NAME
        )
        
        try:
            compare_transaction_files_task(transaction_json_path, validation_json_path) 
        except Exception:
            return 
    elif transaction_json_path.exists() and validation_json_path.exists():
        pass # Skipping scan
    else: 
        return

    if not transaction_json_path.exists(): 
        return
        
    rename_res = execute_rename_transactions_task( 
        json_file_path=transaction_json_path, root_dir=root_dir, dry_run=dry_run,
        validation_json_path=validation_json_path 
    )
    path_map_result: Any = rename_res.result() if hasattr(rename_res, 'result') and callable(rename_res.result) else rename_res
    path_map: Dict[str, str] = path_map_result.get("path_translation_map", {}) if isinstance(path_map_result, dict) else {}
    
    execute_content_transactions_task( 
        json_file_path=transaction_json_path, root_dir=root_dir, dry_run=dry_run,
        path_translation_map=path_map, process_binary_files=process_binary_files,
        find_pattern=find_pattern, replace_pattern=replace_pattern, 
        is_regex=is_regex, case_sensitive=case_sensitive,
        validation_json_path=validation_json_path
    )

# --- Main Execution ---
def main() -> None:
    script_path_obj = Path(__file__).resolve(strict=False) 

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

Special 'flojoy' -> 'atlasvibe' case-preserving behavior:
  This is active by default when:
  - find_pattern is 'flojoy' (or variants like 'Flojoy', 'FLOJOY')
  - replace_pattern is 'atlasvibe'
  - --is-regex is NOT used
  - --case-sensitive is NOT used
  It will replace:
    'flojoy' -> 'atlasvibe'
    'Flojoy' -> 'Atlasvibe'
    'FLOJOY' -> 'ATLASVIBE'
    'FloJoy' -> 'AtlasVibe'
    'floJoy' -> 'atlasVibe'
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
                        help="List of file extensions to process (e.g., .py .txt). Processes all text-based files if not specified, respecting binary detection.")
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

    # Add default transaction log files to exclusions for main operations
    if not (args.self_test or args.self_check): 
        default_log_files_to_exclude = [
            TRANSACTION_FILE_NAME, 
            VALIDATION_TRANSACTION_FILE_NAME,
            TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT,
            VALIDATION_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT
        ]
        for log_file in default_log_files_to_exclude:
            if log_file not in args.exclude_files:
                args.exclude_files.append(log_file)


    # Robust script self-exclusion
    try:
        if not (args.self_test or args.self_check) and Path(args.directory).exists(): 
            target_dir_resolved = Path(args.directory).resolve(strict=True) 
            if script_path_obj.is_file(): 
                script_resolved = script_path_obj.resolve(strict=True)
                if script_resolved.parent == target_dir_resolved: 
                    if script_path_obj.name not in args.exclude_files:
                        args.exclude_files.append(script_path_obj.name)
                elif script_resolved.is_relative_to(target_dir_resolved): 
                    script_relative_to_target = str(script_resolved.relative_to(target_dir_resolved))
                    if script_relative_to_target not in args.exclude_files:
                        args.exclude_files.append(script_relative_to_target)
    except FileNotFoundError: 
        if not (args.self_test or args.self_check):
             pass # Silently skip if target dir not found during self-exclusion
    except ValueError: 
        pass 
    except Exception:
        pass # Silently skip other errors during self-exclusion


    if args.self_test or args.self_check:
        with tempfile.TemporaryDirectory(prefix="mass_replace_self_test_") as tmpdir_str:
            tmpdir_path = Path(tmpdir_str)
            self_test_flow(
                temp_dir_str=str(tmpdir_path), 
                dry_run_for_test=args.dry_run, 
                process_binary_for_test=args.process_binary_files
            )
        return

    if not Path(args.directory).is_dir(): 
        return

    find_and_replace_phased_flow(
        directory=args.directory, find_pattern=args.find_pattern, replace_pattern=args.replace_pattern,
        extensions=args.extensions, exclude_dirs=args.exclude_dirs, exclude_files=args.exclude_files,
        is_regex=args.is_regex, case_sensitive=args.case_sensitive, dry_run=args.dry_run,
        skip_scan=args.skip_scan, process_binary_files=args.process_binary_files,
        force_execution=args.force
    )

if __name__ == "__main__":
    main()
