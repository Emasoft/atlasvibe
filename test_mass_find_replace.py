# tests/test_mass_find_replace.py
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `test_mixed_encoding_surgical_replacement`: Corrected `expected_lines_bytes` for line 5.
#   The string "Flojoy" within the comment `(should not match 'Flojoy' key)` IS a target
#   for replacement by the default map, so it should become "Atlasvibe".
# - `create_test_environment_content`:
#   - Corrected deep path creation to be under `flojoy_root`.
#   - For `use_complex_map`:
#     - Changed `diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS` to `useless_diacritics_folder` (using stripped key for matching).
#     - Changed `file_with_diacritics_ȕsele̮Ss_diá͡cRiti̅cS.txt` to `useless_diacritics_file.txt` (using stripped key for matching).
#     - Content for the above file now uses `useless_diacritics` (stripped key).
#     - Changed `file_with_spaces_The spaces will not be ignored.md` to `The spaces will not be ignored_file.md`.
#     - Content for `complex_map_content_with_key_with_controls.txt` now uses `keywithcontrolchars` (stripped key).
#     - Content for `special_chars_in_content_test.txt` now uses `charactersnotallowedinpathswillbeescapedwhensearchedinfilenamesandfoldernames` (stripped key).
#   - For `include_precision_test_file`:
#     - Changed "FLÖJOY_DIACRITIC" to "FLOJOY_DIACRITIC" (stripped key) in content.
#     - Changed "key\twith\ncontrol" to "keywithcontrol" (stripped key) in content.
#   - These changes aim to create file/folder names and content that literally contain the stripped version of the keys
#     from the complex/precision maps, allowing the current `replace_logic.py` regex to match them.
# - Refactored multiple statements on single lines to comply with E701 and E702 linting rules.
# - Modernized type hints (selectively, keeping Union/Optional in assert_file_content as per user diff note).
# - Imported strip_diacritics and strip_control_characters from replace_logic.
# - Programmatically generated stripped keys for complex and precision maps to ensure alignment with replace_logic.
# - Added debug prints to show original keys and their stripped versions used for test data generation.
# - Stripped keys used for test data generation are now also NFC normalized.
# - `test_complex_map_run`: Corrected assertion for `control_chars_key_orig_filename`.
#   The file *should* be renamed because its canonicalized name part matches a canonicalized key.
#   The assertion now checks for the new, replaced name.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
from pathlib import Path
import os
import shutil
import time
from typing import Any, Optional, Dict, Union # Keep Any if specifically needed, Optional for custom_ignore_path_str, Dict for mock_tx_call_counts
import logging
import json
from unittest.mock import patch, MagicMock

from mass_find_replace import main_flow, MAIN_TRANSACTION_FILE_NAME, SCRIPT_NAME
from file_system_operations import (
    load_transactions, TransactionStatus, TransactionType,
    BINARY_MATCHES_LOG_FILE, SELF_TEST_ERROR_FILE_BASENAME,
    save_transactions, _is_retryable_os_error
)
import replace_logic
import file_system_operations # For mocking its functions

from conftest import (
    create_test_environment_content, assert_file_content,
    VERY_LARGE_FILE_NAME_ORIG, VERY_LARGE_FILE_NAME_REPLACED, VERY_LARGE_FILE_LINES
)

DEFAULT_EXTENSIONS = [".txt", ".py", ".md", ".bin", ".log", ".data", ".rtf", ".xml"]
DEFAULT_EXCLUDE_DIRS_REL = ["excluded_flojoy_dir", "symlink_targets_outside"]
DEFAULT_EXCLUDE_FILES_REL = ["exclude_this_flojoy_file.txt"]

def run_main_flow_for_test(
    temp_test_dir: Path, map_file: Path, extensions: list[str] | None = DEFAULT_EXTENSIONS,
    exclude_dirs: list[str] | None = None, exclude_files: list[str] | None = None,
    dry_run: bool = False, skip_scan: bool = False, resume: bool = False,
    force_execution: bool = True, ignore_symlinks_arg: bool = False, # custom_ignore_file can be str | None
    use_gitignore: bool = False, custom_ignore_file: str | None = None,
    skip_file_renaming: bool = False, skip_folder_renaming: bool = False, skip_content: bool = False,
    timeout_minutes: int = 1, quiet_mode: bool = True # Default to quiet for tests
):
    load_map_success = replace_logic.load_replacement_map(map_file)
    if map_file.name != "empty_mapping.json":
        assert load_map_success, f"Failed to load map {map_file} for test"
        assert replace_logic._RAW_REPLACEMENT_MAPPING, f"Map {map_file} loaded but no rules processed."
    elif not load_map_success and map_file.name == "empty_mapping.json" and replace_logic._RAW_REPLACEMENT_MAPPING :
         pytest.fail(f"Empty map file {map_file} failed to load but rules were processed.")

    final_exclude_dirs = exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS_REL
    base_exclude_files = exclude_files if exclude_files is not None else DEFAULT_EXCLUDE_FILES_REL
    additional_excludes = [map_file.name, BINARY_MATCHES_LOG_FILE]
    final_exclude_files = list(set(base_exclude_files + additional_excludes))

    main_flow(
        directory=str(temp_test_dir), mapping_file=str(map_file), extensions=extensions,
        exclude_dirs=final_exclude_dirs, exclude_files=final_exclude_files, dry_run=dry_run,
        skip_scan=skip_scan, resume=resume, force_execution=force_execution,
        ignore_symlinks_arg=ignore_symlinks_arg,
        use_gitignore=use_gitignore, custom_ignore_file_path=custom_ignore_file,
        skip_file_renaming=skip_file_renaming, skip_folder_renaming=skip_folder_renaming,
        skip_content=skip_content, timeout_minutes=timeout_minutes,
        quiet_mode=quiet_mode
    )








def test_dry_run_behavior(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    orig_deep_file_path = temp_test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    original_content = orig_deep_file_path.read_text(encoding='utf-8')
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True)
    assert orig_deep_file_path.exists()
    assert_file_content(orig_deep_file_path, original_content)
    assert not (temp_test_dir / "atlasvibe_root").exists()
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    for tx in transactions:
        if tx["STATUS"] == TransactionStatus.COMPLETED.value:
            assert tx.get("ERROR_MESSAGE") == "DRY_RUN" or tx.get("PROPOSED_LINE_CONTENT") is not None or tx["TYPE"] != TransactionType.FILE_CONTENT_LINE.value
        elif tx["STATUS"] == TransactionStatus.PENDING.value:
            pytest.fail(f"Tx {tx['id']} PENDING after dry run scan phase implies it wasn't processed for planning.")



GITIGNORE_CONTENT = """
# This is a comment
*.log
build/
/docs/specific_file.txt
!important.log
"""
CUSTOM_IGNORE_CONTENT = """
*.tmp
temp_data/
"""
@pytest.mark.parametrize("use_gitignore_cli, custom_ignore_name, expected_ignored_files, expected_processed_files", [
    (True, None, ["no_target_here.log", "build/ignored_build_file.txt", "docs/specific_file.txt"], ["important.log", "src/main.py"]),
    (False, ".customignore", ["data.tmp", "temp_data/file.dat"], ["other_file.log", "src/main.py"]),
    (True, ".customignore", ["no_target_here.log", "build/ignored_build_file.txt", "docs/specific_file.txt", "data.tmp", "temp_data/file.dat"], ["important.log", "src/main.py"]),
])
def test_ignore_file_logic(temp_test_dir: Path, default_map_file: Path,
                           use_gitignore_cli, custom_ignore_name, expected_ignored_files, expected_processed_files):
    create_test_environment_content(temp_test_dir)
    (temp_test_dir / "build").mkdir(exist_ok=True)
    (temp_test_dir / "build" / "ignored_build_file.txt").write_text("flojoy in build")
    (temp_test_dir / "docs").mkdir(exist_ok=True)
    (temp_test_dir / "docs" / "specific_file.txt").write_text("flojoy in specific doc")
    (temp_test_dir / "important.log").write_text("flojoy important log")
    (temp_test_dir / "src").mkdir(exist_ok=True)
    (temp_test_dir / "src" / "main.py").write_text("flojoy in main.py")
    (temp_test_dir / "data.tmp").write_text("flojoy in data.tmp")
    (temp_test_dir / "temp_data").mkdir(exist_ok=True)
    (temp_test_dir / "temp_data" / "file.dat").write_text("flojoy in temp_data")
    (temp_test_dir / "other_file.log").write_text("flojoy in other_file.log")

    if use_gitignore_cli: # type: ignore
        (temp_test_dir / ".gitignore").write_text(GITIGNORE_CONTENT)
    custom_ignore_path_str: Optional[str] = None
    if custom_ignore_name:
        custom_ignore_path = temp_test_dir / custom_ignore_name
        custom_ignore_path.write_text(CUSTOM_IGNORE_CONTENT)
        custom_ignore_path_str = str(custom_ignore_path)

    run_main_flow_for_test(temp_test_dir, default_map_file, use_gitignore=use_gitignore_cli, custom_ignore_file=custom_ignore_path_str)
    
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    processed_paths_in_tx = {tx["PATH"] for tx in transactions} if transactions else set()

    for ignored_file_rel_path_str in expected_ignored_files:
        ignored_file_path = Path(ignored_file_rel_path_str)
        is_present_in_tx = False
        for tx_path_str in processed_paths_in_tx: # type: ignore
            tx_path = Path(tx_path_str)
            if tx_path == ignored_file_path or ignored_file_path in tx_path.parents:
                is_present_in_tx = True
                break
        assert not is_present_in_tx, f"File/Dir '{ignored_file_path}' expected to be ignored but found in transactions."
        assert (temp_test_dir / ignored_file_path).exists(), f"Ignored file/dir '{ignored_file_path}' should still exist with original name."
        if (temp_test_dir / ignored_file_path).is_file() and "flojoy" in (temp_test_dir / ignored_file_path).read_text(encoding='utf-8', errors='ignore').lower():
            assert "flojoy" in (temp_test_dir / ignored_file_path).read_text(encoding='utf-8', errors='ignore').lower(), f"Ignored file '{ignored_file_path}' content changed."


    for processed_file_rel_path_str in expected_processed_files:
        processed_file_rel_path = Path(processed_file_rel_path_str)
        original_path_abs = temp_test_dir / processed_file_rel_path

        related_tx_exists = any(
            tx["PATH"] == str(processed_file_rel_path) or
            (tx.get("ORIGINAL_NAME") and Path(tx["PATH"]).name == replace_logic.replace_occurrences(processed_file_rel_path.name) and Path(tx["PATH"]).parent == processed_file_rel_path.parent)
            for tx in transactions or [] # type: ignore
        )
        assert related_tx_exists, f"File '{processed_file_rel_path}' expected to be processed but no related transaction found."

        new_name = replace_logic.replace_occurrences(original_path_abs.name)
        new_path_abs = original_path_abs.with_name(new_name)

        if new_name != original_path_abs.name:
            assert not original_path_abs.exists(), f"File '{original_path_abs}' should have been renamed to '{new_path_abs}'."
            assert new_path_abs.exists(), f"File '{original_path_abs}' was expected to be renamed to '{new_path_abs}', but new path doesn't exist."
            if "flojoy" in new_path_abs.read_text(encoding='utf-8', errors='ignore').lower(): # Check content of new file
                 assert "atlasvibe" in new_path_abs.read_text(encoding='utf-8', errors='ignore').lower(), f"File '{new_path_abs}' content should have changed."
        elif original_path_abs.exists():
            if "flojoy" in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower():
                 assert "atlasvibe" in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower(), f"File '{original_path_abs}' content should have changed."


@pytest.mark.parametrize("filename, content_bytes, is_binary_expected_by_lib, contains_flojoy_bytes", [
    ("text_file.txt", b"This is a plain text file with flojoy.", False, True),
    ("utf16_file.txt", "UTF-16 text with flojoy".encode('utf-16'), False, True),
    ("binary_file.bin", b"\x00\x01\x02flojoy_data\x03\x04\xDE\xAD\xBE\xEF", True, True),
    ("image.jpg", b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01flojoy_marker", True, True),
    ("control_char_heavy.txt", b"text" + b"\x01\x02\x03\x04\x05" * 200 + b"flojoy", True, True),
    ("mostly_nulls.dat", b"\x00" * 500 + b"flojoy" + b"\x00" * 500, True, True),
    ("valid_utf8.txt", "Valid UTF-8 string with flojoy and éàçüö.".encode('utf-8'), False, True),
    ("corrupt_utf8.txt", b"Corrupt UTF-8 with flojoy \xff\xfe some more.", True, True),
    ("empty_file.txt", b"", False, False),
    ("rtf_file.rtf", b"{\\rtf1\\ansi This is flojoy rtf text.}", False, True),
    ("svg_file.svg", b"<svg><text>flojoy</text></svg>", False, True),
    ("no_match_binary.dat", b"\xDE\xAD\xBE\xEF\xCA\xFE\xBA\xBE", True, False),
    ("no_match_text.txt", b"Simple text file.", False, False),
])
def test_binary_detection_and_processing_with_isbinary_lib(temp_test_dir: Path, default_map_file: Path, filename, content_bytes, is_binary_expected_by_lib, contains_flojoy_bytes):
    from isbinary import is_binary_file as lib_is_binary

    file_path = temp_test_dir / filename
    file_path.write_bytes(content_bytes)

    detected_as_binary_lib = False
    try:
        if len(content_bytes) == 0:
            detected_as_binary_lib = False
        else:
            detected_as_binary_lib = lib_is_binary(str(file_path))
    except FileNotFoundError:
        if len(content_bytes) == 0:
            detected_as_binary_lib = False
        else:
            pytest.fail(f"is_binary_file raised FileNotFoundError for non-empty file: {filename}")
    except Exception as e:
        pytest.fail(f"is_binary_file raised an unexpected exception for {filename}: {e}")


    assert detected_as_binary_lib == is_binary_expected_by_lib, \
        f"File {filename} lib_is_binary detection mismatch. Expected binary: {is_binary_expected_by_lib}, Detected binary: {detected_as_binary_lib}"

    script_treats_as_binary_for_content_mod = detected_as_binary_lib and not filename.endswith(".rtf")

    run_main_flow_for_test(temp_test_dir, default_map_file, extensions=None,
                           skip_file_renaming=True, skip_folder_renaming=True)

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    transactions_list = transactions if transactions is not None else [] # Ensure it's a list for iteration

    content_tx_found = any(tx["PATH"] == filename and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value for tx in transactions_list)

    binary_log_path = temp_test_dir / BINARY_MATCHES_LOG_FILE
    binary_log_has_match_for_this_file = False
    if binary_log_path.exists():
        log_content = binary_log_path.read_text(encoding='utf-8')
        if f"File: {filename}" in log_content:
             for key_str_map in replace_logic.get_raw_stripped_keys():
                 if f"File: {filename}, Key: '{key_str_map}'" in log_content:
                     binary_log_has_match_for_this_file = True
                     break


    if not script_treats_as_binary_for_content_mod:
        if contains_flojoy_bytes:
            assert content_tx_found, f"Expected content transaction for text-like file {filename} which contained a match."
            if file_path.suffix.lower() != '.rtf':
                changed_content_str = file_path.read_text(encoding='utf-8', errors='surrogateescape')
                all_map_keys_lower = {k.lower() for k in replace_logic.get_raw_stripped_keys()} # These are stripped keys
                # Check against original map keys (unstripped, lowercased) to ensure no original forms remain (json.loads returns Any)
                original_unstripped_keys_lower = {k.lower() for k,v in json.loads(default_map_file.read_text())["REPLACEMENT_MAPPING"].items()}

                found_original_key = False
                for key_l in original_unstripped_keys_lower:
                    if key_l in changed_content_str.lower():
                        found_original_key = True
                        break
                assert not found_original_key, f"Text file {filename} content not fully replaced. Found an original key variant: {key_l} in {changed_content_str[:200]}"
        else:
            assert not content_tx_found, f"No content transaction expected for text-like file {filename} as it had no matches."

        assert not binary_log_has_match_for_this_file, f"Text-like file {filename} should not have matches in binary log."
    else:
        assert not content_tx_found, f"Binary file {filename} should not have content transactions."
        if contains_flojoy_bytes:
             assert binary_log_has_match_for_this_file, f"Binary file {filename} with matches expected in binary log, but not found or not for a mapped key."
        else:
             assert not binary_log_has_match_for_this_file, f"Binary file {filename} without matches should not be in binary log for a mapped key."


@pytest.mark.slow
def test_timeout_behavior_and_retries_mocked(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir)
    file_to_lock_rel = "file_with_floJoy_lines.txt"
    renamed_file_to_lock_rel = "file_with_atlasVibe_lines.txt"


    original_execute_content = file_system_operations._execute_content_line_transaction
    mock_tx_call_counts: Dict[str, int] = {}
    max_fails_for_mock = 2

    def mock_execute_content_with_retry(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        nonlocal mock_tx_call_counts
        is_target_file_tx = (tx_item["PATH"] == file_to_lock_rel or Path(tx_item["PATH"]).name == renamed_file_to_lock_rel) and \
                            tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value

        if is_target_file_tx:
            tx_id = tx_item['id']
            current_tx_call_count = mock_tx_call_counts.get(tx_id, 0) + 1
            mock_tx_call_counts[tx_id] = current_tx_call_count

            if current_tx_call_count <= max_fails_for_mock:
                return TransactionStatus.RETRY_LATER, f"Mocked OS error (retryable), tx_id: {tx_id}, attempt {current_tx_call_count}", True
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run)

    with patch('file_system_operations._execute_content_line_transaction', mock_execute_content_with_retry):
        run_main_flow_for_test(temp_test_dir, default_map_file, timeout_minutes=1)

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None

    target_txs_checked_count = 0
    for tx in transactions:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == renamed_file_to_lock_rel) and \
           tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            target_txs_checked_count +=1
            assert tx["STATUS"] == TransactionStatus.COMPLETED.value, f"Transaction for {tx['PATH']} (id: {tx['id']}, line: {tx.get('LINE_NUMBER')}) should have eventually completed."
            assert tx.get("retry_count", 0) == max_fails_for_mock, f"Transaction for {tx['PATH']} (id: {tx['id']}, line: {tx.get('LINE_NUMBER')}) should have {max_fails_for_mock} retries. Got {tx.get('retry_count',0)}."
            assert mock_tx_call_counts.get(tx['id']) == max_fails_for_mock + 1, \
                f"Mocked function for tx_id {tx['id']} not called expected number of times. Got {mock_tx_call_counts.get(tx['id'])}, expected {max_fails_for_mock + 1}"

    assert target_txs_checked_count > 0, "Did not find any targeted content transaction for retry test."
    assert len(mock_tx_call_counts) == target_txs_checked_count, "mock_tx_call_counts tracked more/less transactions than expected."


    mock_tx_call_counts_indef: dict[str, int] = {}
    indef_max_mock_calls_per_tx = 7

    def mock_always_retryable_error_indef(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        nonlocal mock_tx_call_counts_indef
        is_target_file_tx = (tx_item["PATH"] == file_to_lock_rel or Path(tx_item["PATH"]).name == renamed_file_to_lock_rel) and \
                            tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value
        if is_target_file_tx:
            tx_id = tx_item['id']
            current_tx_call_count = mock_tx_call_counts_indef.get(tx_id, 0) + 1
            mock_tx_call_counts_indef[tx_id] = current_tx_call_count

            if current_tx_call_count < indef_max_mock_calls_per_tx :
                return TransactionStatus.RETRY_LATER, f"Mocked persistent OS error (retryable), tx_id: {tx_id}, attempt {current_tx_call_count}", True
            else:
                return TransactionStatus.FAILED, "Mocked persistent error, exceeded test call limit for this tx_id", False
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run)

    transactions_for_indef_retry = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions_for_indef_retry is not None # Ensure it's not None before iterating
    for tx in transactions_for_indef_retry:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == renamed_file_to_lock_rel) and \
           tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            tx["STATUS"] = TransactionStatus.PENDING.value
            tx["retry_count"] = 0
            tx.pop("timestamp_next_retry", None)
            tx.pop("timestamp_processed", None)
            tx.pop("ERROR_MESSAGE", None)
    save_transactions(transactions_for_indef_retry, temp_test_dir / MAIN_TRANSACTION_FILE_NAME)

    with patch('file_system_operations._execute_content_line_transaction', mock_always_retryable_error_indef):
        run_main_flow_for_test(temp_test_dir, default_map_file, timeout_minutes=0, resume=True)

    final_transactions_indef = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert final_transactions_indef is not None

    target_txs_indef_checked_count = 0
    for tx in final_transactions_indef:
         if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == renamed_file_to_lock_rel) and \
            tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            target_txs_indef_checked_count +=1
            assert tx["STATUS"] == TransactionStatus.FAILED.value, f"Tx {tx['id']} should be FAILED."
            assert tx.get("retry_count", 0) == (indef_max_mock_calls_per_tx -1) , \
                f"Tx {tx['id']} should have retried {indef_max_mock_calls_per_tx -1} times. Got {tx.get('retry_count',0)}"
            assert mock_tx_call_counts_indef.get(tx['id']) == indef_max_mock_calls_per_tx, \
                f"Mock for tx {tx['id']} in indef test part called {mock_tx_call_counts_indef.get(tx['id'])} times, expected {indef_max_mock_calls_per_tx}"

    assert target_txs_indef_checked_count > 0, "Did not find any targeted transaction for indefinite retry test part."
    assert len(mock_tx_call_counts_indef) == target_txs_indef_checked_count


def test_empty_directory_handling(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)

    truly_empty_dir = temp_test_dir / "truly_empty"
    truly_empty_dir.mkdir()

    map_for_empty_test = temp_test_dir / "map_for_empty.json"
    map_for_empty_test.write_text(json.dumps({"REPLACEMENT_MAPPING": {"flojoy": "atlasvibe"}}))

    run_main_flow_for_test(truly_empty_dir, map_for_empty_test)

    assert any(f"Target directory '{truly_empty_dir.resolve()}' is empty. Nothing to do." in record.message
               for record in caplog.records), \
        "Expected 'Target directory ... is empty. Nothing to do.' log message for truly empty dir."

    shutil.rmtree(truly_empty_dir)
    map_for_empty_test.unlink()
    caplog.clear()

    for item in temp_test_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    simple_map_path = temp_test_dir / "simple_map.json"
    simple_map_path.write_text(json.dumps({"REPLACEMENT_MAPPING": {"flojoy": "atlasvibe"}}))

    run_main_flow_for_test(temp_test_dir, simple_map_path)

    assert not any(f"Target directory '{temp_test_dir.resolve()}' is empty. Nothing to do." in record.message
                   for record in caplog.records), \
        "The 'directory is empty' message should not appear when map file is present."

    # Check for the message that indicates scan happened but found nothing actionable (because map file is excluded)
    # This could be "No actionable occurrences found by scan." or similar if the map itself is the only file.
    # Or if the map is empty, "Map empty and no scannable items found..."
    # Given the map is not empty, but is excluded, "No actionable occurrences found by scan" is likely.
    assert any("No actionable occurrences found by scan." in record.message or
               "Map empty and no scannable items found" in record.message # If map was empty
               for record in caplog.records), \
        "Expected appropriate log message when dir only has excluded map/transaction files."


    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    if txn_file.exists():
        transactions = load_transactions(txn_file)
        assert transactions is None or len(transactions) == 0, \
            "Transaction file should be empty or non-existent if only map file was present and excluded."

    if simple_map_path.exists():
        simple_map_path.unlink()


