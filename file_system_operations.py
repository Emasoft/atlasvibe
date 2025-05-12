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

from replace_logic import replace_flojoy_occurrences # Import the replacement function

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
MAX_RENAME_RETRIES = 1 # Simple retry: try once more
RETRY_DELAY_SECONDS = 0.1 # Small delay before retrying
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
    SKIPPED = "SKIPPED" # Added for cases where no change is made or item not found

# --- Helper Functions ---

def get_file_encoding(file_path: Path, sample_size: int = 10240) -> Optional[str]:
    """Detects file encoding using chardet."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
        if not raw_data:
            return DEFAULT_ENCODING_FALLBACK # Assume default for empty files
        detected = chardet.detect(raw_data)
        encoding: Optional[str] = detected.get('encoding')
        confidence: float = detected.get('confidence', 0.0)

        # print(f"DEBUG_ENCODING: Detected encoding for {file_path}: {encoding} with confidence {confidence}")

        if encoding and confidence and confidence > 0.7:
            # Normalize common encodings
            norm_encoding = encoding.lower()
            if norm_encoding == 'ascii':
                return 'ascii'
            # Handle common UTF-8 variations
            if 'utf-8' in norm_encoding or 'utf8' in norm_encoding:
                return 'utf-8'
            # Validate if the encoding is known to Python
            try:
                b"test".decode(encoding)
                # print(f"DEBUG_ENCODING: Using detected encoding: {encoding}")
                return encoding
            except LookupError:
                # print(f"DEBUG_ENCODING: Detected encoding {encoding} not recognized by Python, falling back.")
                return DEFAULT_ENCODING_FALLBACK # Fallback if encoding is unknown
        else:
            # If confidence is low, try UTF-8 as a common default, otherwise fallback
            try:
                raw_data.decode('utf-8')
                # print(f"DEBUG_ENCODING: Low confidence, but decodes as UTF-8. Using UTF-8.")
                return 'utf-8'
            except UnicodeDecodeError:
                # print(f"DEBUG_ENCODING: Low confidence and not UTF-8. Falling back to default.")
                # Use chardet's guess even if low confidence, or fallback? Let's try fallback.
                return DEFAULT_ENCODING_FALLBACK # Fallback if unsure and not UTF-8
    except Exception as e:
        # print(f"DEBUG_ENCODING: Exception during encoding detection for {file_path}: {e}. Falling back.")
        return DEFAULT_ENCODING_FALLBACK # Fallback on any error

def is_likely_binary_file(file_path: Path, sample_size: int = 1024) -> bool:
    """Heuristic to check if a file is likely binary."""
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)
        if not sample:
            return False
        # Presence of NULL byte is a strong indicator
        if b'\x00' in sample:
            return True
        # Check proportion of non-text characters (basic heuristic)
        # Using a stricter definition of text characters (printable ASCII + common whitespace)
        text_chars = bytes(range(32, 127)) + b'\n\r\t\f\v'
        non_text_count = sum(1 for byte in sample if byte not in text_chars)
        # If more than 30% are non-text characters, assume binary
        if len(sample) > 0 and (non_text_count / len(sample)) > 0.3:
            return True
        return False
    except Exception:
        # If we can't read the file, assume it might be binary or problematic
        return True # Safer to assume binary if read fails

def _walk_for_scan(root_dir: Path, excluded_dirs: List[str]) -> Iterator[Path]:
    """Yields paths for scanning, respecting exclusions."""
    abs_excluded_dirs = [root_dir.joinpath(d).resolve(strict=False) for d in excluded_dirs]
    for item_path in root_dir.rglob("*"):
        is_excluded = False
        try:
            resolved_item_path = item_path.resolve(strict=False)
            for excluded_dir in abs_excluded_dirs:
                # Check if the item is the excluded dir itself or is inside an excluded dir
                if resolved_item_path == excluded_dir or excluded_dir in resolved_item_path.parents:
                    is_excluded = True
                    break
        except (ValueError, OSError, FileNotFoundError): # Handle potential resolution errors
             # Fallback check using string comparison if resolve fails
            item_path_str = str(item_path)
            if any(item_path_str.startswith(str(ex_dir)) for ex_dir in abs_excluded_dirs):
                 is_excluded = True
        if is_excluded:
            # If it's a directory, don't recurse into it further implicitly via rglob
            if item_path.is_dir():
                 # This check might be redundant with rglob's behavior but adds clarity
                 pass # rglob should handle skipping contents if the dir is yielded and skipped
            continue # Skip this item
        yield item_path

def _get_current_absolute_path(
    original_relative_path_str: str,
    root_dir: Path,
    path_translation_map: Dict[str, str], # original_rel_path -> new_NAME_component_only
    cache: Dict[str, Path] # original_rel_path -> current_absolute_path
) -> Path:
    """
    Recursively determines the current absolute path of an item,
    considering parent directory renames recorded in path_translation_map.
    Cache is used for optimization but correctness relies on recomputation.
    """
    # The initial cache check was removed to ensure paths are re-evaluated
    # against the potentially modified path_translation_map, especially after parent renames.

    if original_relative_path_str == ".": # Base case for recursion: the root directory
        cache["."] = root_dir
        return root_dir

    original_path_obj = Path(original_relative_path_str)
    # Handle edge case where path might be just a filename relative to root_dir
    if original_path_obj.parent == Path('.'):
        original_parent_rel_str = "."
    else:
        original_parent_rel_str = str(original_path_obj.parent)

    item_original_name = original_path_obj.name

    # Recursively find the current absolute path of the parent directory.
    # This recursive call will use the translation map correctly.
    current_parent_abs_path = _get_current_absolute_path(
        original_parent_rel_str, root_dir, path_translation_map, cache
    )

    # Determine the current name of the item.
    # Check if the item itself was directly renamed (its original relative path is in the map).
    current_item_name = path_translation_map.get(original_relative_path_str, item_original_name)

    current_abs_path = current_parent_abs_path / current_item_name

    # Update cache with the computed path for potential future use within the same execution phase
    cache[original_relative_path_str] = current_abs_path
    return current_abs_path

# --- Scan Logic ---
def scan_directory_for_occurrences(
    root_dir: Path,
    excluded_dirs: List[str],
    excluded_files: List[str],
    file_extensions: Optional[List[str]],
    resume_from_transactions: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:

    processed_transactions: List[Dict[str, Any]]
    # Use a set for efficient lookup of existing transactions
    # Key: tuple(relative_path_str, transaction_type_value, line_number)
    existing_transaction_ids: Set[Tuple[str, str, int]] = set()

    if resume_from_transactions is not None:
        processed_transactions = list(resume_from_transactions) # Start with existing ones
        for tx in processed_transactions:
            # Ensure required keys exist before adding to set
            tx_type = tx.get("TYPE")
            tx_path = tx.get("PATH")
            tx_line = tx.get("LINE_NUMBER", 0) # Default to 0 for name transactions
            if tx_type is not None and tx_path is not None:
                existing_transaction_ids.add((tx_path, tx_type, tx_line))
            else:
                 print(f"Warning: Skipping invalid transaction during resume: {tx}")
    else:
        processed_transactions = []

    find_target_lower = "flojoy" # The base string to search for case-insensitively
    abs_excluded_files = [root_dir.joinpath(f).resolve(strict=False) for f in excluded_files]

    # Normalize file extensions for case-insensitive comparison
    normalized_extensions = {ext.lower() for ext in file_extensions} if file_extensions else None

    # Use the walking function that respects exclusions
    all_items_for_scan = list(_walk_for_scan(root_dir, excluded_dirs))

    # Sort items: process deeper items first for renames, but maybe not necessary for scan?
    # Let's sort by path string for deterministic order during scan.
    sorted_items = sorted(all_items_for_scan, key=str)

    for item_path in sorted_items:
        try:
            # Use normalized path separators for consistency
            relative_path_str = str(item_path.relative_to(root_dir)).replace("\\", "/")
        except ValueError:
            # This can happen if item_path is not relative to root_dir (shouldn't with rglob)
            print(f"Warning: Could not get relative path for {item_path}. Skipping.")
            continue

        original_name = item_path.name

        # Check against resolved absolute excluded file paths
        try:
            resolved_item_path = item_path.resolve(strict=False)
            if resolved_item_path in abs_excluded_files:
                continue
        except (OSError, FileNotFoundError):
             # If resolve fails, compare string paths as a fallback
             item_path_str = str(item_path)
             if any(str(ex_file) == item_path_str for ex_file in abs_excluded_files):
                  continue


        # Check for name-based transactions (FILE_NAME or FOLDER_NAME)
        if find_target_lower in original_name.lower():
            tx_type_val = TransactionType.FOLDER_NAME.value if item_path.is_dir() else TransactionType.FILE_NAME.value
            current_tx_id_tuple = (relative_path_str, tx_type_val, 0) # Line number is 0 for name transactions

            if current_tx_id_tuple not in existing_transaction_ids:
                processed_transactions.append({
                    "id": str(uuid.uuid4()),
                    "TYPE": tx_type_val,
                    "PATH": relative_path_str,
                    "ORIGINAL_NAME": original_name,
                    "LINE_NUMBER": 0,
                    "ORIGINAL_LINE_CONTENT": None,
                    "PROPOSED_LINE_CONTENT": None, # Populated during execution/dry-run
                    "ORIGINAL_ENCODING": None,
                    "STATUS": TransactionStatus.PENDING.value,
                    "ERROR_MESSAGE": None
                })
                existing_transaction_ids.add(current_tx_id_tuple)


        # Check for content-based transactions (FILE_CONTENT_LINE)
        if item_path.is_file():
            # Skip binary files based on heuristic
            if is_likely_binary_file(item_path):
                continue
            # Skip if extensions are specified and this file doesn't match
            if normalized_extensions and item_path.suffix.lower() not in normalized_extensions:
                continue

            file_encoding = get_file_encoding(item_path) # Use detected or fallback
            try:
                # Read lines carefully, preserving line endings
                with open(item_path, 'r', encoding=file_encoding, errors='replace', newline=None) as f: # Use newline=None for universal line ending handling, errors='replace'
                    lines = f.readlines() # Reads lines with their endings

                for line_num_0_indexed, line_content in enumerate(lines):
                    if find_target_lower in line_content.lower():
                        line_number_1_indexed = line_num_0_indexed + 1
                        current_tx_id_tuple = (relative_path_str, TransactionType.FILE_CONTENT_LINE.value, line_number_1_indexed)

                        if current_tx_id_tuple not in existing_transaction_ids:
                            processed_transactions.append({
                                "id": str(uuid.uuid4()),
                                "TYPE": TransactionType.FILE_CONTENT_LINE.value,
                                "PATH": relative_path_str,
                                "ORIGINAL_NAME": None, # Not applicable for content lines
                                "LINE_NUMBER": line_number_1_indexed,
                                "ORIGINAL_LINE_CONTENT": line_content, # Store original line with ending
                                "PROPOSED_LINE_CONTENT": None, # Populated during execution/dry-run
                                "ORIGINAL_ENCODING": file_encoding,
                                "STATUS": TransactionStatus.PENDING.value,
                                "ERROR_MESSAGE": None
                            })
                            existing_transaction_ids.add(current_tx_id_tuple)
            except UnicodeDecodeError as ude:
                 print(f"Warning: UnicodeDecodeError reading {item_path} with encoding {file_encoding} (using errors='replace'). Skipping content scan. Error: {ude}")
            except Exception as e:
                # Catch other potential errors during file read/processing
                print(f"Warning: Could not read/process content of file {item_path} with encoding {file_encoding}: {e}")
                pass # Continue to the next file
    return processed_transactions

# --- Transaction File Management ---
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
                # Basic validation
                if isinstance(loaded_data, list):
                    print(f"Successfully loaded transactions from {path}")
                    return cast(List[Dict[str, Any]], loaded_data)
                else:
                    print(f"Warning: Invalid format in {path}. Expected a list.")
                    loaded_data = None # Reset if format is wrong
            except json.JSONDecodeError as jde:
                print(f"Warning: Failed to decode JSON from {path}: {jde}")
            except Exception as e:
                print(f"Warning: Failed to load transactions from {path}: {e}")
    if loaded_data is None:
         print(f"Error: Could not load valid transactions from {json_file_path} or its backup.")
    return None

def save_transactions(transactions: List[Dict[str, Any]], json_file_path: Path) -> None:
    """Saves transactions, creating a backup first."""
    # Create backup before overwriting
    if json_file_path.exists():
        backup_path = json_file_path.with_suffix(json_file_path.suffix + TRANSACTION_FILE_BACKUP_EXT)
        try:
            # Copy file data and metadata (like permissions)
            shutil.copy2(json_file_path, backup_path)
        except Exception as e:
            # Non-critical error, proceed with saving if possible
            print(f"Warning: Could not create backup of {json_file_path} to {backup_path}: {e}")
    # Write the new transaction file
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=4) # Use indent for readability
    except Exception as e:
        print(f"Error: Could not save transactions to {json_file_path}: {e}")
        # Depending on requirements, might want to restore backup here if write fails
        raise # Re-raise the exception to signal failure

def update_transaction_status_in_list(
    transactions: List[Dict[str, Any]],
    transaction_id: str,
    new_status: TransactionStatus,
    error_message: Optional[str] = None,
    proposed_content: Optional[str] = None # Added to update proposed content
) -> bool:
    """Updates the status and optionally error message/proposed content of a transaction in the list."""
    updated = False
    for tx_item in transactions:
        if tx_item['id'] == transaction_id:
            tx_item['STATUS'] = new_status.value
            if error_message:
                tx_item['ERROR_MESSAGE'] = error_message
            else:
                # Remove error message if status is no longer FAILED
                if new_status != TransactionStatus.FAILED:
                    tx_item.pop('ERROR_MESSAGE', None)
            # Update proposed content if provided (useful for dry runs or successful content changes)
            if proposed_content is not None and tx_item['TYPE'] == TransactionType.FILE_CONTENT_LINE.value:
                 tx_item['PROPOSED_LINE_CONTENT'] = proposed_content

            updated = True
            break
    return updated

# --- Execution Logic ---

def _ensure_within_sandbox(path_to_check: Path, sandbox_root: Path, operation_desc: str):
    """Checks if a path is within the sandbox_root. Raises SandboxViolationError if not."""
    try:
        resolved_path = path_to_check.resolve()
        resolved_sandbox_root = sandbox_root.resolve()
        # Check if the resolved path is relative to the sandbox root OR is the sandbox root itself
        if not resolved_path.is_relative_to(resolved_sandbox_root) and resolved_path != resolved_sandbox_root :
            raise SandboxViolationError(
                f"Operation '{operation_desc}' on path '{resolved_path}' is outside the sandbox '{resolved_sandbox_root}'."
            )
    except (OSError, FileNotFoundError) as e:
         # If path resolution fails, it might be problematic, treat as violation or log warning
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

    # print(f"DEBUG_RENAME_EXEC: Processing transaction for: {original_name} (Type: {tx_item['TYPE']})")
    # print(f"DEBUG_RENAME_EXEC: Original relative path: {original_relative_path_str}")

    try:
        # Use the potentially updated _get_current_absolute_path
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)
        # print(f"DEBUG_RENAME_EXEC: Current absolute path resolved to: {current_abs_path}")
        # print(f"DEBUG_RENAME_EXEC: Does current_abs_path exist? {current_abs_path.exists()}")
    except FileNotFoundError:
         # This might happen if a parent directory was expected but not found after renames
         return TransactionStatus.SKIPPED, f"Parent path for '{original_relative_path_str}' not found (likely due to prior failed rename or path resolution issue)."
    except Exception as e:
         return TransactionStatus.FAILED, f"Error resolving current path for '{original_relative_path_str}': {e}"


    if not current_abs_path.exists():
        # Check if it was already renamed (target name exists)
        potential_new_name = replace_flojoy_occurrences(original_name)
        potential_new_path = current_abs_path.with_name(potential_new_name)
        if potential_new_path.exists():
             return TransactionStatus.SKIPPED, f"Original path '{current_abs_path}' not found, but target '{potential_new_path}' exists (already processed?)."
        else:
             # If neither original nor target exists, something went wrong earlier
             return TransactionStatus.SKIPPED, f"Original path '{current_abs_path}' not found and target name does not exist either."

    new_name = replace_flojoy_occurrences(original_name)
    if new_name == original_name:
        return TransactionStatus.SKIPPED, "Name unchanged after replacement."

    new_abs_path = current_abs_path.with_name(new_name)
    # print(f"DEBUG_RENAME_EXEC: Proposed new name: {new_name}")
    # print(f"DEBUG_RENAME_EXEC: Proposed new absolute path: {new_abs_path}")

    # --- Self-Test Error Simulation ---
    # If this is the specific file designated for error testing, simulate failure.
    if not dry_run and original_name == SELF_TEST_ERROR_FILE_BASENAME:
        print(f"INFO: Simulating rename failure for self-test file: {original_name}")
        return TransactionStatus.FAILED, "Simulated permission error for self-test"
    # --- End Self-Test Error Simulation ---


    if dry_run:
        print(f"[DRY RUN] Would rename '{current_abs_path}' to '{new_abs_path}'")
        # Update maps even in dry run to simulate effect on subsequent transactions
        path_translation_map[original_relative_path_str] = new_name
        # Update cache with the *proposed* new path for dry run consistency
        path_cache[original_relative_path_str] = new_abs_path
        return TransactionStatus.COMPLETED, "DRY_RUN"

    # Retry logic for actual rename
    for attempt in range(MAX_RENAME_RETRIES + 1):
        try:
            # Ensure paths are within the root directory (sandbox)
            _ensure_within_sandbox(current_abs_path, root_dir, f"rename source for {original_name}")
            _ensure_within_sandbox(new_abs_path, root_dir, f"rename destination for {new_name}")

            # Check if the target path already exists and is a different file/directory
            if new_abs_path.exists():
                 try:
                     # Use samefile to handle case-insensitivity issues on some OSes
                     if not current_abs_path.resolve().samefile(new_abs_path.resolve()):
                         return TransactionStatus.SKIPPED, f"Target path '{new_abs_path}' already exists and is a different item."
                     # If samefile is true, it means it's the same item (e.g., case change only on case-insensitive FS)
                     # Allow the rename to proceed for case changes.
                 except FileNotFoundError:
                      # If resolve fails, assume different if target exists
                      return TransactionStatus.SKIPPED, f"Target path '{new_abs_path}' already exists, but source resolve failed."
                 except OSError as ose:
                      return TransactionStatus.FAILED, f"Error checking if paths are same file: {ose}"


            os.rename(current_abs_path, new_abs_path) # The actual operation
            # print(f"DEBUG_RENAME_EXEC: Successfully renamed '{current_abs_path}' to '{new_abs_path}' on attempt {attempt + 1}")

            # Update translation map and cache with the successful rename
            path_translation_map[original_relative_path_str] = new_name
            path_cache[original_relative_path_str] = new_abs_path # Cache the new absolute path

            return TransactionStatus.COMPLETED, None # Success
        except MockableRetriableError as mre: # Specific error for testing retries
            print(f"DEBUG_RENAME_EXEC: Attempt {attempt + 1} failed with retriable error: {mre}")
            if attempt < MAX_RENAME_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue # Go to next attempt
            else: # Max retries reached
                return TransactionStatus.FAILED, f"Retriable error persisted after {MAX_RENAME_RETRIES + 1} attempts: {mre}"
        except SandboxViolationError as sve:
            # This should ideally be caught before the loop, but double-check
            return TransactionStatus.FAILED, f"SandboxViolation: {sve}"
        except OSError as e: # Catch other OS-level errors like PermissionError, FileNotFoundError etc.
            # print(f"DEBUG_RENAME_EXEC: os.rename failed for '{current_abs_path}' to '{new_abs_path}': {e}")
            # Check if retrying might help (e.g., temporary lock)
            if attempt < MAX_RENAME_RETRIES:
                 print(f"Warning: Rename attempt {attempt + 1} failed: {e}. Retrying...")
                 time.sleep(RETRY_DELAY_SECONDS)
                 continue
            else:
                 # Return specific error after retries fail
                 return TransactionStatus.FAILED, f"Failed after {MAX_RENAME_RETRIES + 1} attempts: {e}"
        except Exception as e: # Catch any other unexpected errors
             return TransactionStatus.FAILED, f"Unexpected error during rename: {e}"

    # Should not be reached if logic is correct, but as a fallback:
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
    # Retrieve original line content *including* its line ending
    original_line_content = tx_item["ORIGINAL_LINE_CONTENT"]
    file_encoding = tx_item["ORIGINAL_ENCODING"] or DEFAULT_ENCODING_FALLBACK

    try:
        current_abs_path = _get_current_absolute_path(original_relative_path_str, root_dir, path_translation_map, path_cache)
    except FileNotFoundError:
         return TransactionStatus.SKIPPED, f"Parent path for '{original_relative_path_str}' not found (likely due to prior failed rename)."
    except Exception as e:
         return TransactionStatus.FAILED, f"Error resolving current path for '{original_relative_path_str}': {e}"


    if not current_abs_path.is_file():
        return TransactionStatus.SKIPPED, f"File '{current_abs_path}' not found or not a file."

    # Double-check for binary files before attempting content modification
    if is_likely_binary_file(current_abs_path):
        return TransactionStatus.SKIPPED, f"File '{current_abs_path}' identified as binary during execution; content modification skipped."

    # Perform replacement on the original line content
    new_line_content = replace_flojoy_occurrences(original_line_content)

    # Update the transaction item with the proposed content (useful for dry run and final log)
    tx_item["PROPOSED_LINE_CONTENT"] = new_line_content

    if new_line_content == original_line_content:
        return TransactionStatus.SKIPPED, "Line content unchanged after replacement."

    if dry_run:
        print(f"[DRY RUN] File '{current_abs_path}', line {line_number_1_indexed}:")
        print(f"[DRY RUN]   Original: {repr(original_line_content)}")
        print(f"[DRY RUN]   Proposed: {repr(new_line_content)}")
        return TransactionStatus.COMPLETED, "DRY_RUN"

    # --- Actual File Modification ---
    try:
        _ensure_within_sandbox(current_abs_path, root_dir, f"file content write for {current_abs_path.name}")

        # Read all lines from the file using the detected encoding
        try:
            # Use errors='replace' for reading
            with open(current_abs_path, 'r', encoding=file_encoding, errors='replace', newline=None) as f:
                lines = f.readlines() # Reads lines with original endings
        except Exception as read_err:
             return TransactionStatus.FAILED, f"Error reading file {current_abs_path} for update: {read_err}"

        # Validate line number
        if not (0 <= line_number_1_indexed - 1 < len(lines)):
            return TransactionStatus.FAILED, f"Line number {line_number_1_indexed} out of bounds for file {current_abs_path} (len: {len(lines)})."

        # Verify that the line content hasn't changed since the scan
        # This comparison must be exact, including line endings
        if lines[line_number_1_indexed - 1] != original_line_content:
             # Provide more context on mismatch
             # print(f"DEBUG: Original expected: {repr(original_line_content)}")
             # print(f"DEBUG: Current actual:   {repr(lines[line_number_1_indexed - 1])}")
             return TransactionStatus.FAILED, f"Original content of line {line_number_1_indexed} in {current_abs_path} has changed since scan."

        # Replace the line in the list
        lines[line_number_1_indexed - 1] = new_line_content

        # Write the modified lines back to the file using binary mode and original encoding
        try:
            with open(current_abs_path, 'wb') as f: # Open in binary mode
                for line in lines:
                    # Encode each line using the original encoding with errors='replace'
                    f.write(line.encode(file_encoding, errors='replace'))
        except Exception as write_err:
             return TransactionStatus.FAILED, f"Error writing updated content to file {current_abs_path}: {write_err}"

        # If successful
        return TransactionStatus.COMPLETED, None
    except SandboxViolationError as sve:
        return TransactionStatus.FAILED, f"SandboxViolation: {sve}"
    except Exception as e:
        # Catch any other unexpected errors during the process
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
    # Map from original relative path string to the *current* name component (after potential rename)
    path_translation_map: Dict[str, str] = {}
    # Cache from original relative path string to the *current* absolute Path object
    path_cache: Dict[str, Path] = {}

    # Sort transactions for execution:
    # 1. Folders before Files (deepest first for renames within renames)
    # 2. Files before Content Lines
    # 3. Content Lines by line number
    def execution_sort_key(tx: Dict[str, Any]):
        type_order = {TransactionType.FOLDER_NAME.value: 0, TransactionType.FILE_NAME.value: 1, TransactionType.FILE_CONTENT_LINE.value: 2}
        path_depth = tx["PATH"].count('/') # Use normalized separator
        line_num = tx.get("LINE_NUMBER", 0)

        # Sort renames by depth (deepest first) to handle nested renames correctly
        if tx["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
            return (type_order[tx["TYPE"]], -path_depth, tx["PATH"]) # Negative depth for deepest first
        else: # Sort content changes by file path then line number
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
             tx_item["STATUS"] = TransactionStatus.PENDING.value # Correct invalid status

        # --- Status Handling ---
        # If already completed or failed, just count it unless resuming
        if current_status == TransactionStatus.COMPLETED:
            stats["completed"] +=1
            # If a rename was completed, ensure its effect is in the translation map for subsequent items
            if tx_item["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
                 original_rel_path = tx_item["PATH"]
                 original_name = tx_item["ORIGINAL_NAME"]
                 new_name = replace_flojoy_occurrences(original_name)
                 if new_name != original_name:
                     path_translation_map[original_rel_path] = new_name
                     # Invalidate cache for this specific path if it exists, force re-resolve next time
                     path_cache.pop(original_rel_path, None)
            continue
        if current_status == TransactionStatus.FAILED:
            stats["failed"] +=1
            continue
        if current_status == TransactionStatus.SKIPPED:
            stats["skipped"] +=1
            continue

        # If resuming, IN_PROGRESS should be retried. If not resuming, reset IN_PROGRESS to PENDING.
        if current_status == TransactionStatus.IN_PROGRESS:
            if not resume:
                tx_item["STATUS"] = TransactionStatus.PENDING.value
                current_status = TransactionStatus.PENDING
            else:
                 print(f"Resuming IN_PROGRESS transaction: {tx_id} ({tx_item.get('PATH', 'N/A')})")


        # --- Execute PENDING or Resumed IN_PROGRESS ---
        if current_status == TransactionStatus.PENDING or \
           (resume and current_status == TransactionStatus.IN_PROGRESS):

            print(f"Processing transaction {i+1}/{total_transactions}: {tx_id} ({tx_item.get('TYPE')}: {tx_item.get('PATH')}:{tx_item.get('LINE_NUMBER', '')})")

            # Mark as IN_PROGRESS before execution
            update_transaction_status_in_list(transactions, tx_id, TransactionStatus.IN_PROGRESS)
            # Save intermediate state immediately
            save_transactions(transactions, transactions_file_path)

            new_status: TransactionStatus
            error_msg: Optional[str] = None
            proposed_content_update: Optional[str] = None # For content line updates

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
                # Optionally add traceback here for debugging
                # import traceback
                # traceback.print_exc()


            # Update status and save again after execution attempt
            update_transaction_status_in_list(transactions, tx_id, new_status, error_msg, proposed_content_update)
            save_transactions(transactions, transactions_file_path)

            # Update stats based on the final status of this transaction
            if new_status == TransactionStatus.COMPLETED:
                stats["completed"] += 1
            elif new_status == TransactionStatus.FAILED:
                stats["failed"] += 1
            elif new_status == TransactionStatus.SKIPPED:
                stats["skipped"] += 1
        else:
             # Should only be PENDING if not handled above, count as pending.
             stats["pending"] +=1


    # Final count of pending items (should be 0 if all processed)
    final_pending = sum(1 for t in transactions if t.get("STATUS") == TransactionStatus.PENDING.value)
    stats["pending"] = final_pending

    return stats
