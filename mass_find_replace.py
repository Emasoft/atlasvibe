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

# Prefect integration
try:
    from prefect import task, flow, get_run_logger
    import logging # Standard library logging
    
    # Define get_prefect_logger_outside_flow using standard logging,
    # but namespaced in a way that's common for Prefect utility logging.
    def get_prefect_logger_outside_flow(name: Optional[str] = None) -> Any:
        logger_name = "prefect.mass_find_replace" # Default namespace
        if name:
            logger_name = f"prefect.{name}" # Allow specific sub-namespacing
        return logging.getLogger(logger_name)

except ImportError:
    print("Prefect library not found or core components missing. Please install it to run this script: pip install prefect")
    # Fallback logger if prefect is not available, for basic script operation outside a flow
    import logging as std_logging
    def get_prefect_logger_outside_flow(name: Optional[str] = None) -> Any:
        return std_logging.getLogger(name or "mass_find_replace_fallback")
    # Define dummy decorators if prefect is not installed, so script can be parsed
    def task(fn: Callable[..., Any]) -> Callable[..., Any]: return fn 
    def flow(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]: 
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn
        return decorator
    # Provide a dummy get_run_logger if prefect is not available
    def get_run_logger() -> Any: 
        return get_prefect_logger_outside_flow("mass_find_replace_fallback_run_logger")


# Chardet integration for encoding detection
try:
    import chardet 
except ImportError:
    print("chardet library not found. Please install it for robust encoding detection: pip install chardet")
    chardet: Optional[types.ModuleType] = None


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

def get_file_encoding(file_path: Path, logger: Any, sample_size: int = 10240) -> Optional[str]:
    """Detects file encoding using chardet, with fallback."""
    if not chardet:
        logger.debug(f"chardet library not available. Using default fallback encoding '{DEFAULT_ENCODING_FALLBACK}' for {file_path}.")
        return DEFAULT_ENCODING_FALLBACK

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size) 
        if not raw_data:
            return DEFAULT_ENCODING_FALLBACK 
        
        detected = chardet.detect(raw_data)
        encoding: Optional[str] = detected.get('encoding')
        confidence: float = detected.get('confidence', 0.0)

        if encoding and confidence and confidence > 0.7: 
            logger.debug(f"Detected encoding for {file_path}: {encoding} (confidence: {confidence:.2f})")
            norm_encoding = encoding.lower()
            if norm_encoding == 'ascii': 
                return 'ascii'
            if 'utf-8' in norm_encoding or 'utf8' in norm_encoding: 
                return 'utf-8'
            try:
                b"test".decode(encoding) 
                return encoding 
            except LookupError:
                logger.warning(f"Encoding '{encoding}' detected by chardet for {file_path} is not recognized by Python. Falling back to default.")
                return DEFAULT_ENCODING_FALLBACK 
        else:
            logger.warning(f"Low confidence ({confidence:.2f}) or no encoding detected for {file_path} (detected: {encoding}). Falling back to UTF-8 attempt.")
            try:
                raw_data.decode('utf-8') 
                logger.debug(f"Successfully decoded sample of {file_path} with UTF-8 as fallback.")
                return 'utf-8'
            except UnicodeDecodeError:
                logger.warning(f"Could not decode sample of {file_path} with UTF-8. Using system default (None) as last resort.")
                return None 
    except Exception as e:
        logger.error(f"Error detecting encoding for {file_path}: {e}. Using system default (None).")
        return None 

def is_likely_binary_file(file_path: Path, logger: Any, sample_size: int = 1024) -> bool:
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
    except Exception as e:
        if logger: 
            logger.error(f"Could not read sample from {file_path} for binary check: {e}")
        else: 
            print(f"Error: Could not read sample from {file_path} for binary check: {e}")
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
        # Removed logger call that was here for debugging unmatched variants
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
    logger: Any = get_run_logger()
    logger.info(f"Phase 1 (Scan ID: {scan_id}): Scanning project for occurrences...")
    transactions: List[Dict[str, Any]] = []
    abs_excluded_files = [root_dir.joinpath(f).resolve(strict=False) for f in excluded_files]

    path_candidates_for_rename = sorted(
        list(_walk_for_scan(root_dir, excluded_dirs)), key=lambda p: len(p.parts), reverse=True
    )

    for item_path in path_candidates_for_rename:
        try:
            relative_path_str = str(item_path.relative_to(root_dir))
        except ValueError: 
            logger.warning(f"Could not get relative path for {item_path} to {root_dir}. Skipping name scan.")
            continue
        original_name = item_path.name
        
        if item_path.is_file() and item_path.resolve(strict=False) in abs_excluded_files:
            logger.debug(f"Skipping excluded file for name scan: {relative_path_str}")
            continue

        if item_path.is_file() and file_extensions:
            if not item_path.suffix or item_path.suffix.lower() not in [ext.lower() for ext in file_extensions]:
                logger.debug(f"Skipping file (name scan) due to extension filter: {relative_path_str}")
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
            logger.warning(f"Could not get relative path for {item_path} to {root_dir}. Skipping content scan.")
            continue

        if item_path.resolve(strict=False) in abs_excluded_files:
            logger.debug(f"Skipping excluded file for content scan: {relative_path_str}")
            continue
        if file_extensions and (not item_path.suffix or item_path.suffix.lower() not in [ext.lower() for ext in file_extensions]):
            logger.debug(f"Skipping file (content scan) due to extension filter: {relative_path_str}")
            continue
        
        if not process_binary_files and is_likely_binary_file(item_path, logger):
            logger.info(f"Skipping likely binary file for content scan: {relative_path_str}")
            continue

        original_encoding = get_file_encoding(item_path, logger)
        current_encoding_to_try = original_encoding or DEFAULT_ENCODING_FALLBACK 

        try:
            # Read as bytes first to allow decoding with surrogateescape
            file_content_bytes = item_path.read_bytes()
            file_content_str = file_content_bytes.decode(current_encoding_to_try, errors='surrogateescape')
            
            if _text_contains_pattern(file_content_str, find_pattern, is_regex, case_sensitive):
                transactions.append({
                    "id": str(uuid.uuid4()), "OCCURRENCE_TYPE": "STRING_IN_FILE", 
                    "PATH": relative_path_str, "NEW_PATH_COMPONENT": None,
                    "LINE_NUMBER": 0, 
                    "ORIGINAL_LINE_CONTENT": None, # Kept for schema, but not used for whole-file
                    "PROPOSED_LINE_CONTENT": None, # Kept for schema, but not used for whole-file
                    "ORIGINAL_ENCODING": original_encoding, 
                    "FIND_PATTERN": find_pattern, "REPLACE_PATTERN": replace_pattern,
                    "IS_REGEX": is_regex, "CASE_SENSITIVE": case_sensitive, "STATUS": STATUS_PENDING
                })
        except Exception as e: 
            logger.error(f"Error scanning content of {relative_path_str} (tried encoding: {current_encoding_to_try}): {e}")
            
    logger.info(f"Phase 1 (Scan ID: {scan_id}): Scan complete. Found {len(transactions)} potential transactions.")
    return transactions

# --- Phase 2: Compile JSON Task & Compare ---

@task
def compile_transactions_json_task(transactions: List[Dict[str, Any]], output_dir: Path, filename: str) -> Path:
    logger: Any = get_run_logger()
    logger.info(f"Phase 2: Compiling transactions to JSON ({filename})...")
    
    def sort_key(t: Dict[str, Any]) -> Tuple[int, int, str, int]: 
        path_depth = t["PATH"].count(os.sep)
        type_order = {"FOLDERNAME": 0, "FILENAME": 1, "STRING_IN_FILE": 2}
        # For FOLDERNAME and FILENAME, sort by path_depth (shallowest first)
        # For STRING_IN_FILE, sort by path_depth (shallowest first), then line number
        return (type_order[t["OCCURRENCE_TYPE"]], path_depth, t["PATH"], t.get("LINE_NUMBER", 0))

    transactions.sort(key=sort_key)
    
    json_file_path = output_dir / filename
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=4)
        logger.info(f"Phase 2: Successfully compiled {len(transactions)} transactions to {json_file_path}")
    except Exception as e:
        logger.error(f"Phase 2: Failed to write transactions JSON to {json_file_path}: {e}")
        raise
    return json_file_path

@task
def compare_transaction_files_task(file1_path: Path, file2_path: Path) -> bool:
    logger: Any = get_run_logger()
    logger.info(f"Comparing transaction files: {file1_path.name} and {file2_path.name}")
    if not file1_path.exists() or not file2_path.exists():
        logger.error("One or both transaction files do not exist for comparison.")
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
            logger.info("Transaction files are identical (excluding IDs and status). Scan is deterministic.")
            return True
        else:
            logger.error("Transaction files differ! Scan may not be deterministic or there's an issue.")
            diff_count = 0
            if len(comp_data1) != len(comp_data2):
                logger.error(f"Different number of transactions: {len(comp_data1)} vs {len(comp_data2)}")
                diff_count = abs(len(comp_data1) - len(comp_data2))
            else:
                for i, (tx1, tx2) in enumerate(zip(comp_data1, comp_data2)):
                    if tx1 != tx2:
                        logger.warning(f"Difference at transaction index {i}:")
                        logger.warning(f"File1 TX: {tx1}")
                        logger.warning(f"File2 TX: {tx2}")
                        diff_count +=1
                        if diff_count > 5 : 
                            logger.warning("More differences exist...")
                            break
            raise ValueError("Scan determinism check failed: Transaction plans differ.")
            
    except Exception as e:
        logger.error(f"Error comparing transaction files: {e}")
        raise

# --- Phase 3: Execute Transactions Tasks ---

def _load_transactions_with_fallback(json_file_path: Path, logger: Any) -> Optional[List[Dict[str, Any]]]:
    """Loads transactions from primary JSON, falls back to .bak on error."""
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    try:
        if json_file_path.exists():
            with open(json_file_path, 'r', encoding='utf-8') as f:
                return cast(List[Dict[str, Any]], json.load(f))
        elif backup_path.exists():
            logger.warning(f"Primary transaction file {json_file_path} not found. Attempting to load from backup {backup_path}.")
            with open(backup_path, 'r', encoding='utf-8') as f:
                return cast(List[Dict[str, Any]], json.load(f))
        else:
            logger.error(f"Neither primary transaction file nor backup found for {json_file_path.name}.")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {json_file_path}: {e}")
        if backup_path.exists():
            logger.warning(f"Attempting to load from backup {backup_path} due to primary file corruption.")
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    return cast(List[Dict[str, Any]], json.load(f))
            except Exception as backup_e:
                logger.error(f"Error loading from backup file {backup_path} as well: {backup_e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load transaction file {json_file_path}: {e}")
        return None


def _update_transaction_status_in_json(json_file_path: Path, transaction_id: str, new_status: str, error_message: Optional[str] = None) -> None:
    """Updates status, creating a backup first."""
    logger: Any = get_run_logger()
    backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
    
    if not json_file_path.exists():
        logger.error(f"Cannot update status: Primary transaction file {json_file_path} does not exist.")
        if backup_path.exists():
            logger.warning(f"Primary file missing, but backup {backup_path} exists. This indicates a previous failure.")
        return

    try:
        if json_file_path.exists(): 
            shutil.copy2(json_file_path, backup_path) 
            logger.debug(f"Created backup: {backup_path}")
    except Exception as e:
        logger.error(f"Failed to create backup of {json_file_path}: {e}. Aborting status update for safety.")
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
                logger.debug(f"Updated status for tx_id {transaction_id} to {new_status} in {json_file_path.name}")
            else:
                logger.warning(f"Transaction ID {transaction_id} not found in {json_file_path.name} for status update.")
    except Exception as e:
        logger.error(f"Critical error updating transaction status in {json_file_path} for ID {transaction_id}: {e}")
        logger.warning(f"Attempting to restore {json_file_path} from backup {backup_path} due to update failure.")
        try:
            shutil.copy2(backup_path, json_file_path)
            logger.info(f"Restored {json_file_path} from backup.")
        except Exception as restore_e:
            logger.error(f"Failed to restore {json_file_path} from backup: {restore_e}. JSON file might be corrupt.")


@task 
def execute_rename_transactions_task(
    json_file_path: Path, root_dir: Path, dry_run: bool,
    validation_json_path: Optional[Path] = None 
) -> Dict[str, Any]:
    logger: Any = get_run_logger()
    logger.info("Phase 3a: Executing RENAME transactions...")
    
    transactions = _load_transactions_with_fallback(json_file_path, logger)
    if transactions is None:
        return {"completed": 0, "failed": 0, "skipped": 0, "path_translation_map": {}}

    validation_tx_map_by_id: Dict[str, Dict[str, Any]] = {}
    if validation_json_path and validation_json_path.exists():
        try:
            with open(validation_json_path, 'r', encoding='utf-8') as vf: 
                validation_data = json.load(vf)
            validation_tx_map_by_id = {tx_val['id']: tx_val for tx_val in validation_data}
        except Exception as e: 
            logger.warning(f"Could not load validation transaction file {validation_json_path}: {e}")

    rename_txs = [t for t in transactions if t["OCCURRENCE_TYPE"] in ["FOLDERNAME", "FILENAME"] and t["STATUS"] == STATUS_PENDING]
    completed_count, failed_count, skipped_count = 0, 0, 0
    path_translation_map: Dict[str, str] = {} 

    for tx_from_primary in rename_txs:
        tx_id = tx_from_primary.get("id")
        tx = tx_from_primary
        if not all(k in tx_from_primary for k in ["PATH", "NEW_PATH_COMPONENT"]) and tx_id and validation_tx_map_by_id:
            logger.warning(f"Transaction {tx_id} from primary JSON seems incomplete. Trying to use validation data.")
            pristine_tx = validation_tx_map_by_id.get(tx_id)
            if pristine_tx and all(k in pristine_tx for k in ["PATH", "NEW_PATH_COMPONENT"]): 
                tx = pristine_tx
            else:
                logger.error(f"Cannot process transaction {tx_id}: incomplete in primary and not found/incomplete in validation JSON.")
                if tx_id: 
                    _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete")
                failed_count += 1
                continue
        elif not all(k in tx_from_primary for k in ["PATH", "NEW_PATH_COMPONENT"]):
             logger.error(f"Cannot process transaction (ID: {tx_id if tx_id else 'Unknown'}): critical keys missing.")
             if tx_id: 
                 _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete")
             failed_count += 1
             continue

        original_relative_path_str = tx["PATH"]
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map)
        
        if not current_abs_path.exists():
            logger.warning(f"Skipping rename: Path {current_abs_path} (derived from {original_relative_path_str}) does not exist.")
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_SKIPPED, "Original path not found")
            skipped_count += 1
            continue

        proposed_new_name_component = tx["NEW_PATH_COMPONENT"]
        new_abs_path = current_abs_path.with_name(proposed_new_name_component)

        if dry_run:
            logger.info(f"[DRY RUN] Would rename: {current_abs_path} -> {new_abs_path}")
            path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_COMPLETED + " (DRY_RUN)")
            completed_count += 1
            continue

        if new_abs_path.exists() and current_abs_path.resolve(strict=False) != new_abs_path.resolve(strict=False):
            logger.warning(f"Target path '{new_abs_path}' already exists. Skipping rename of '{current_abs_path}'.")
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_SKIPPED, "Target path already exists")
            skipped_count += 1
            continue
        
        try:
            if not new_abs_path.parent.exists(): 
                os.makedirs(new_abs_path.parent, exist_ok=True)
            os.rename(current_abs_path, new_abs_path)
            logger.info(f"Renamed: {current_abs_path} -> {new_abs_path}")
            path_translation_map[original_relative_path_str] = str(new_abs_path.relative_to(root_dir))
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_COMPLETED)
            completed_count += 1
        except Exception as e:
            logger.error(f"Error renaming {current_abs_path} to {new_abs_path}: {e}")
            _update_transaction_status_in_json(json_file_path, tx["id"], STATUS_FAILED, str(e))
            failed_count += 1

    logger.info(f"Phase 3a: Rename execution. Completed: {completed_count}, Failed: {failed_count}, Skipped: {skipped_count}")
    return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count, "path_translation_map": path_translation_map}


@task 
def execute_content_transactions_task(
    json_file_path: Path, root_dir: Path, dry_run: bool,
    path_translation_map: Dict[str, str], process_binary_files: bool,
    find_pattern: str, replace_pattern: str, is_regex: bool, case_sensitive: bool,
    validation_json_path: Optional[Path] = None 
) -> Dict[str, int]:
    logger: Any = get_run_logger()
    logger.info("Phase 3b: Executing STRING_IN_FILE transactions (whole file approach)...")

    transactions = _load_transactions_with_fallback(json_file_path, logger)
    if transactions is None:
        return {"completed": 0, "failed": 0, "skipped": 0}

    validation_tx_map_by_id: Dict[str, Dict[str, Any]] = {}
    if validation_json_path and validation_json_path.exists():
        try:
            with open(validation_json_path, 'r', encoding='utf-8') as vf: 
                validation_data = json.load(vf)
            validation_tx_map_by_id = {tx_val['id']: tx_val for tx_val in validation_data}
        except Exception as e: 
            logger.warning(f"Could not load validation transaction file {validation_json_path} for content task: {e}")
            
    file_to_process_details: Dict[str, Dict[str, Any]] = {} 

    for tx_from_primary in transactions:
        if tx_from_primary["OCCURRENCE_TYPE"] == "STRING_IN_FILE" and tx_from_primary["STATUS"] == STATUS_PENDING:
            tx_id = tx_from_primary.get("id")
            tx_data_to_use = tx_from_primary
            if not all(k in tx_from_primary for k in ["PATH"]) and tx_id and validation_tx_map_by_id: 
                logger.warning(f"Content transaction {tx_id} from primary JSON seems incomplete. Using validation data.")
                pristine_tx = validation_tx_map_by_id.get(tx_id)
                if pristine_tx and all(k in pristine_tx for k in ["PATH"]): 
                    tx_data_to_use = pristine_tx
                else:
                    logger.error(f"Cannot process content transaction {tx_id}: incomplete in primary and validation JSON.")
                    if tx_id: 
                        _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, "Transaction data corrupted/incomplete")
                    continue 
            elif not all(k in tx_from_primary for k in ["PATH"]):
                 logger.error(f"Cannot process content transaction (ID: {tx_id if tx_id else 'Unknown'}): critical keys missing.")
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
            logger.warning(f"Skipping content change for {len(tx_ids_for_file)} occurrences: Path {current_abs_path} (derived from {original_relative_path_str}) not a file or not found.")
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, "File path not found or not a file after renames")
            skipped_count += len(tx_ids_for_file)
            continue

        if not process_binary_files and is_likely_binary_file(current_abs_path, logger):
            logger.info(f"Skipping likely binary file for content change: {current_abs_path}")
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, "Skipped binary file")
            skipped_count += len(tx_ids_for_file)
            continue
            
        original_encoding = details["encoding"]
        current_encoding_to_try = original_encoding or DEFAULT_ENCODING_FALLBACK

        if dry_run:
            logger.info(f"[DRY RUN] Would process content of {current_abs_path} for {len(tx_ids_for_file)} occurrences.")
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
                logger.info(f"Modified content of {current_abs_path} (encoding: {current_encoding_to_try}) for {len(tx_ids_for_file)} occurrences.")
                for tx_id in tx_ids_for_file: 
                    _update_transaction_status_in_json(json_file_path, tx_id, STATUS_COMPLETED)
                completed_count += len(tx_ids_for_file)
            else: 
                logger.info(f"Content of {current_abs_path} did not change after replacement. Marking {len(tx_ids_for_file)} transactions as skipped.")
                for tx_id in tx_ids_for_file: 
                    _update_transaction_status_in_json(json_file_path, tx_id, STATUS_SKIPPED, "No change to file content")
                skipped_count += len(tx_ids_for_file)
        except Exception as e: 
            logger.error(f"Error modifying content of {current_abs_path} (encoding: {current_encoding_to_try}): {e}")
            for tx_id in tx_ids_for_file: 
                _update_transaction_status_in_json(json_file_path, tx_id, STATUS_FAILED, str(e))
            failed_count += len(tx_ids_for_file)
            
    logger.info(f"Phase 3b: Content execution. Completed: {completed_count}, Failed: {failed_count}, Skipped: {skipped_count}")
    return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count}


# --- Self-Test Functionality ---
def _create_self_test_environment(base_dir: Path, logger: Any) -> None:
    logger.info(f"Creating self-test environment in {base_dir}...")
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

    except Exception as e: 
        logger.warning(f"Could not create non-utf8 test files for self-test: {e}")
    (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in excluded file")
    (base_dir / "no_flojoy_here.log").write_text("This is a log file without the target string.") 
    logger.info("Self-test environment created.")

@task 
def _verify_self_test_results_task(temp_dir: Path, logger: Any, process_binary_files: bool) -> bool:
    logger.info("--- Verifying Self-Test Results ---")
    passed_checks, failed_checks = 0, 0

    def check(condition: bool, pass_msg: str, fail_msg: str) -> bool:
        nonlocal passed_checks, failed_checks
        if condition: 
            logger.info(f"PASS: {pass_msg}")
            passed_checks += 1
        else: 
            logger.error(f"FAIL: {fail_msg}")
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
        # The expected bytes must match the original file's mixed EOLs after replacement
        # This means encoding the string with its mixed EOLs directly.
        expected_raw_bytes = expected_text_content.encode('utf-8') # UTF-8 is the default for this test file
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

    sjis_file = temp_dir / "sjis_atlasvibe_content.txt"
    if sjis_file.is_file():
        try:
            content = sjis_file.read_text(encoding='shift_jis', errors='replace')
            expected_sjis_text = "これはatlasvibeのテストです。\n次の行もAtlasvibeです。" # Corrected "Flojoy" to "Atlasvibe"
            check(content == expected_sjis_text, "Shift-JIS file content correct and encoding preserved.", f"Shift-JIS file content/encoding INCORRECT. Got: {content!r}")
        except Exception as e: 
            check(False, "", f"Could not read/verify Shift-JIS file: {e}")
    else: 
        check(False, "", "Renamed Shift-JIS file MISSING.")

    gb18030_file = temp_dir / "gb18030_atlasvibe_content.txt"
    if gb18030_file.is_file():
        try:
            content = gb18030_file.read_text(encoding='gb18030', errors='replace')
            expected_gb18030_text = "你好 atlasvibe 世界\n这是 Atlasvibe 的一个例子" # Corrected "Flojoy" to "Atlasvibe"
            check(content == expected_gb18030_text, "GB18030 file content correct and encoding preserved.", f"GB18030 file content/encoding INCORRECT. Got: {content!r}")
        except Exception as e: 
            check(False, "", f"Could not read/verify GB18030 file: {e}")
    else: 
        check(False, "", "Renamed GB18030 file MISSING.")
    
    invalid_utf8_file = temp_dir / "invalid_utf8_atlasvibe_file.txt" 
    if invalid_utf8_file.is_file():
        original_invalid_bytes = b"ValidStart_flojoy_" + b"\xff\xfe" + b"_flojoy_ValidEnd"
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

    logger.info(f"--- Self-Test Verification Summary: {passed_checks} PASSED, {failed_checks} FAILED ---")
    if failed_checks > 0:
        raise AssertionError(f"Self-test failed with {failed_checks} assertion(s).")
    return True


@flow(name="Self-Test Find and Replace Flow") 
def self_test_flow(temp_dir_str: str, dry_run_for_test: bool, process_binary_for_test: bool) -> None:
    logger: Any = get_run_logger()
    logger.info("--- Starting Self-Test ---")
    temp_dir = Path(temp_dir_str)
    _create_self_test_environment(temp_dir, logger)

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
        logger.error("Self-test failed: JSON not created.")
        return
    logger.info(f"Self-test plan: {transaction_json_path_test}. Review for planned changes.")
    
    rename_res = execute_rename_transactions_task( 
        json_file_path=transaction_json_path_test, root_dir=temp_dir, dry_run=dry_run_for_test,
        validation_json_path=validation_json_path_test
    )
    path_map_result: Any = rename_res.result() if hasattr(rename_res, 'result') else rename_res 
    path_map: Dict[str, str] = path_map_result.get("path_translation_map", {}) if isinstance(path_map_result, dict) else {}
    
    execute_content_transactions_task( 
        json_file_path=transaction_json_path_test, root_dir=temp_dir, dry_run=dry_run_for_test,
        path_translation_map=path_map, process_binary_files=process_binary_for_test,
        find_pattern=test_find, replace_pattern=test_replace, 
        is_regex=test_is_regex, case_sensitive=test_case_sensitive,
        validation_json_path=validation_json_path_test
    )
    
    if not dry_run_for_test: 
        _verify_self_test_results_task(temp_dir=temp_dir, logger=logger, process_binary_files=process_binary_for_test) 

    logger.info(f"--- Self-Test Completed (in {temp_dir_str}) ---")
    if dry_run_for_test: 
        logger.info("Self-Test was DRY RUN.")


# --- Main Prefect Flow ---

@flow(name="Mass Find and Replace Flow - Phased", log_prints=True) 
def find_and_replace_phased_flow(
    directory: str, find_pattern: str, replace_pattern: str, 
    extensions: Optional[List[str]], exclude_dirs: List[str], exclude_files: List[str],
    is_regex: bool, case_sensitive: bool, dry_run: bool,
    skip_scan: bool, process_binary_files: bool, force_execution: bool 
    ) -> None:
    logger: Any = get_run_logger()
    root_dir = Path(directory).resolve(strict=False) 
    transaction_json_path = root_dir / TRANSACTION_FILE_NAME
    validation_json_path = root_dir / VALIDATION_TRANSACTION_FILE_NAME

    logger.info(f"Starting flow for: {root_dir}. Find: '{find_pattern}', Replace: '{replace_pattern}'. Log: {transaction_json_path}")

    if dry_run: 
        logger.info("DRY RUN MODE ENABLED.")
    elif not force_execution:
        logger.warning("!!! POTENTIALLY DESTRUCTIVE OPERATION !!!")
        confirm = input(f"Modifying '{root_dir}'. Find '{find_pattern}', Replace '{replace_pattern}'. Backup? Continue? (yes/no): ")
        if confirm.lower() != 'yes': 
            logger.info("Operation cancelled.")
            return
        logger.info("User confirmed. Proceeding...")
    else: 
        logger.warning(f"Executing with --force for '{root_dir}'.")
    if not dry_run: 
        logger.warning("CRITICAL: Ensure backup before running without --dry-run.")

    if not skip_scan:
        if not root_dir.is_dir(): 
            logger.error(f"Target directory '{root_dir}' does not exist. Cannot scan.")
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
        except Exception as e:
            logger.error(f"Scan determinism check failed: {e}. Halting execution.")
            return 
    elif transaction_json_path.exists() and validation_json_path.exists():
        logger.info(f"Skipping scan. Using existing transaction files: {transaction_json_path} and {validation_json_path}")
    else: 
        logger.error(f"Skip scan requested, but one or both transaction files ({transaction_json_path.name}, {validation_json_path.name}) not found. Cannot proceed.")
        return

    if not transaction_json_path.exists(): 
        logger.error(f"Cannot execute: Primary transaction file {transaction_json_path} not found.")
        return
        
    logger.info("Starting execution phase.")
    rename_res = execute_rename_transactions_task( 
        json_file_path=transaction_json_path, root_dir=root_dir, dry_run=dry_run,
        validation_json_path=validation_json_path 
    )
    path_map_result: Any = rename_res.result() if hasattr(rename_res, 'result') else rename_res 
    path_map: Dict[str, str] = path_map_result.get("path_translation_map", {}) if isinstance(path_map_result, dict) else {}
    
    execute_content_transactions_task( 
        json_file_path=transaction_json_path, root_dir=root_dir, dry_run=dry_run,
        path_translation_map=path_map, process_binary_files=process_binary_files,
        find_pattern=find_pattern, replace_pattern=replace_pattern, 
        is_regex=is_regex, case_sensitive=case_sensitive,
        validation_json_path=validation_json_path
    )

    logger.info("Flow finished.")
    if dry_run: 
        logger.info("DRY RUN COMPLETED.")
    else: 
        logger.info("EXECUTION COMPLETED.")

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
                        print(f"Info: Automatically excluding this script from modifications: {script_path_obj.name}")
                elif script_resolved.is_relative_to(target_dir_resolved): 
                    script_relative_to_target = str(script_resolved.relative_to(target_dir_resolved))
                    if script_relative_to_target not in args.exclude_files:
                        args.exclude_files.append(script_relative_to_target)
                        print(f"Info: Automatically excluding this script from modifications: {script_relative_to_target}")
    except FileNotFoundError: 
        if not (args.self_test or args.self_check):
             print(f"Warning: Target directory '{args.directory}' not found during self-exclusion check. Ensure it's valid for main operation.")
    except ValueError: 
        pass 
    except Exception as e:
        print(f"Warning: Could not robustly determine if script needs self-exclusion: {e}")


    if args.self_test or args.self_check:
        print("--- Running Self-Test Mode ---")
        with tempfile.TemporaryDirectory(prefix="mass_replace_self_test_") as tmpdir_str:
            tmpdir_path = Path(tmpdir_str)
            print(f"Self-test will run in temporary directory: {tmpdir_path}")
            self_test_flow(
                temp_dir_str=str(tmpdir_path), 
                dry_run_for_test=args.dry_run, 
                process_binary_for_test=args.process_binary_files
            )
        print(f"--- Self-Test Mode Finished (temp dir {tmpdir_str} cleaned up) ---")
        return

    if not Path(args.directory).is_dir(): 
        print(f"Error: Directory '{args.directory}' not found.")
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
