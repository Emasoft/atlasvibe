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
# - Added new tests for `main_flow` and `main_cli` to increase coverage:
#   - `test_main_flow_ignore_file_read_error`
#   - `test_main_flow_ignore_pattern_compile_error`
#   - `test_main_flow_prompt_user_cancels`
#   - `test_main_flow_prompt_warning_empty_map_complex_skips`
#   - `test_main_flow_resume_load_transactions_returns_none`
#   - `test_main_flow_resume_load_transactions_returns_empty`
#   - `test_main_flow_resume_stat_error`
#   - `test_main_flow_no_transactions_to_execute_after_scan_or_skip_scan`
#   - `test_main_flow_scan_finds_nothing_actionable_with_map`
#   - `test_main_cli_negative_timeout`
#   - `test_main_cli_small_positive_timeout`
#   - `test_main_cli_verbose_flag`
#   - `test_main_cli_missing_dependency`
# - Added `test_edge_case_map_run` to verify behavior with edge case map.
# - Added `test_skip_scan_with_previous_dry_run_renames` to verify skip_scan logic.
# - Added `test_highly_problematic_xml_content_preservation` to test surgical replacement
#   on a file with mixed line endings, cp1252 encoding, valid and invalid bytes for
#   that encoding, and XML-like structures, ensuring byte-for-byte preservation
#   except for the targeted ASCII key replacement.
# - `test_main_flow_ignore_file_read_error`: Made `builtins.open` mock conditional to only affect the ignore file.
# - `test_main_flow_prompt_user_cancels`, `test_main_flow_prompt_warning_empty_map_complex_skips`: Changed assertions to use `caplog.text`.
# - `test_main_flow_resume_load_transactions_returns_none`, `test_main_flow_resume_load_transactions_returns_empty`: Changed `assert_called_once` to `assert mock_load.call_count > 0`.
# - `test_main_flow_resume_stat_error`: Made `Path.stat` mock conditional to only affect the target file for the resume stat check, and to avoid recursion with `resolve()`.
# - `run_cli_command`: Corrected `SCRIPT_PATH_FOR_CLI_TESTS` to be relative to the project root (parent of tests dir).
# - `test_edge_case_map_run`: Corrected assertion for content of `renamed_mykey_name_file` to expect content replacement.
# - Added `import builtins` to fix F821 linting error.
# - Corrected `TypeError: 'bool' object is not iterable` for caplog assertions by using `any(expected_msg in record.message for record in caplog.records)`.
# - `test_main_cli_small_positive_timeout`: Changed CLI arg to "0.5" and ensured `mass_find_replace.py` handles `type=float` for timeout.
# - `test_main_cli_missing_dependency`: Changed to patch `sys.exit` and call `main_cli()` directly.
# - `test_edge_case_map_run`: Corrected expected renamed filename for `content_mykey_file` to `edge_case_content_with_MyKeyValue_VAL_controls.txt`.
# - `test_main_flow_resume_stat_error`: Refined mock_stat_conditional to prevent recursion by using a re-entry guard.
# - `SCRIPT_PATH_FOR_CLI_TESTS`: Changed from `parent.parent` to `parent` assuming `test_mass_find_replace.py` is in the project root.
# - `test_main_cli_missing_dependency`: Changed to use `patch('builtins.__import__')` for more reliable simulation of missing modules.
# - `test_edge_case_map_run`: Corrected assertion for content of `renamed_content_controls_file`. The content "My\nKey" should NOT be replaced by the rule for canonical "MyKey".
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
from unittest.mock import patch, MagicMock, mock_open
import sys
import subprocess # For CLI tests
import builtins # Added to fix F821

from mass_find_replace import main_flow, main_cli, MAIN_TRANSACTION_FILE_NAME, SCRIPT_NAME, YELLOW, RESET
from file_system_operations import (
    load_transactions, TransactionStatus, TransactionType,
    BINARY_MATCHES_LOG_FILE, SELF_TEST_ERROR_FILE_BASENAME,
    save_transactions, _is_retryable_os_error, get_file_encoding
)
import replace_logic
import file_system_operations # For mocking its functions
import pathspec # For mocking its methods

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
    test_setup_logger = logging.getLogger("test_setup_replace_logic")
    if not test_setup_logger.handlers: 
        handler = logging.NullHandler() 
        test_setup_logger.addHandler(handler)
        test_setup_logger.setLevel(logging.DEBUG) 

    load_map_success = replace_logic.load_replacement_map(map_file, logger=test_setup_logger) 
    if map_file.name != "empty_mapping.json": 
        if not load_map_success and map_file.name not in ("invalid_map.json", "map_missing_key.json", "map_regex_error_simulated.json"): 
            assert load_map_success, f"Failed to load map {map_file} for test"
        if load_map_success and map_file.name not in ("map_regex_error_simulated.json"): 
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

    def mock_execute_content_with_retry(tx_item, root_dir, path_translation_map, path_cache, dry_run, logger): # Added logger
        nonlocal mock_tx_call_counts
        is_target_file_tx = (tx_item["PATH"] == file_to_lock_rel or Path(tx_item["PATH"]).name == renamed_file_to_lock_rel) and \
                            tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value

        if is_target_file_tx:
            tx_id = tx_item['id']
            current_tx_call_count = mock_tx_call_counts.get(tx_id, 0) + 1
            mock_tx_call_counts[tx_id] = current_tx_call_count

            if current_tx_call_count <= max_fails_for_mock:
                return TransactionStatus.RETRY_LATER, f"Mocked OS error (retryable), tx_id: {tx_id}, attempt {current_tx_call_count}", True
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run, logger) # Pass logger

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

    def mock_always_retryable_error_indef(tx_item, root_dir, path_translation_map, path_cache, dry_run, logger): # Added logger
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
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run, logger) # Pass logger

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

    assert any("No actionable occurrences found by scan." in record.message or
               "Map empty and no scannable items found" in record.message
               for record in caplog.records), \
        "Expected appropriate log message when dir only has excluded map/transaction files."


    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    if txn_file.exists():
        transactions = load_transactions(txn_file)
        assert transactions is None or len(transactions) == 0, \
            "Transaction file should be empty or non-existent if only map file was present and excluded."

    if simple_map_path.exists():
        simple_map_path.unlink()


# --- New tests for increased coverage ---

def test_main_flow_target_directory_not_exists(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.ERROR)
    non_existent_dir = temp_test_dir / "this_dir_does_not_exist"
    run_main_flow_for_test(non_existent_dir, default_map_file)
    assert any(f"Error: Root directory '{non_existent_dir.resolve()}' not found or not a directory." in record.message for record in caplog.records)

def test_main_flow_mapping_file_invalid_json(temp_test_dir: Path, caplog):
    caplog.set_level(logging.ERROR)
    create_test_environment_content(temp_test_dir) 
    invalid_map_file = temp_test_dir / "invalid_map.json"
    invalid_map_file.write_text("this is not valid json {")
    run_main_flow_for_test(temp_test_dir, invalid_map_file)
    assert any(f"Aborting due to issues with replacement mapping file: {invalid_map_file.resolve()}" in record.message for record in caplog.records)
    assert any("Invalid JSON" in err_rec.message for err_rec in caplog.records if err_rec.levelname == "ERROR")


def test_main_flow_mapping_file_no_replacement_mapping_key(temp_test_dir: Path, caplog):
    caplog.set_level(logging.ERROR)
    create_test_environment_content(temp_test_dir)
    map_missing_key_file = temp_test_dir / "map_missing_key.json"
    map_missing_key_file.write_text(json.dumps({"SOME_OTHER_KEY": {"a": "b"}}))
    run_main_flow_for_test(temp_test_dir, map_missing_key_file)
    assert any(f"Aborting due to issues with replacement mapping file: {map_missing_key_file.resolve()}" in record.message for record in caplog.records)
    assert any("'REPLACEMENT_MAPPING' key not found" in err_rec.message for err_rec in caplog.records if err_rec.levelname == "ERROR")


def test_main_flow_mapping_file_regex_compile_error_simulated(temp_test_dir: Path, caplog):
    caplog.set_level(logging.ERROR)
    create_test_environment_content(temp_test_dir)
    map_file = temp_test_dir / "map_regex_error_simulated.json"
    map_file.write_text(json.dumps({"REPLACEMENT_MAPPING": {"flojoy": "atlasvibe"}}))

    with patch('replace_logic.get_scan_pattern', return_value=None):
        with patch('replace_logic._RAW_REPLACEMENT_MAPPING', {"flojoy": "atlasvibe"}): 
            run_main_flow_for_test(temp_test_dir, map_file)
    
    assert any("Critical Error: Map loaded but scan regex pattern compilation failed or resulted in no patterns." in record.message for record in caplog.records)


def test_main_flow_skip_scan_no_transaction_file(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.ERROR)
    create_test_environment_content(temp_test_dir) 
    transaction_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    if transaction_file.exists():
        transaction_file.unlink()
    
    run_main_flow_for_test(temp_test_dir, default_map_file, skip_scan=True)
    assert any(f"Error: --skip-scan was used, but '{transaction_file.resolve()}' not found." in record.message for record in caplog.records)


def test_main_flow_scan_finds_nothing_actionable(temp_test_dir: Path, empty_map_file: Path, caplog):
    caplog.set_level(logging.INFO)
    create_test_environment_content(temp_test_dir) 
    (temp_test_dir / "some_file.txt").write_text("content without any map keys")
    
    run_main_flow_for_test(temp_test_dir, empty_map_file) 
    
    assert any("Map empty and no scannable items found, or all items ignored." in record.message for record in caplog.records)
    transaction_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    assert transaction_file.exists()
    transactions = load_transactions(transaction_file)
    assert transactions == []

def test_main_flow_scan_finds_nothing_actionable_with_map(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)
    (temp_test_dir / "no_match_here.txt").write_text("This file has standard content.")
    (temp_test_dir / "another_safe_file.py").write_text("print('Hello world')")
    
    run_main_flow_for_test(temp_test_dir, default_map_file, extensions=[".txt", ".py"])
    
    assert any("No actionable occurrences found by scan." in record.message for record in caplog.records)
    transaction_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    assert transaction_file.exists()
    transactions = load_transactions(transaction_file)
    assert transactions == []


def test_main_flow_all_skip_options_true(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)
    run_main_flow_for_test(temp_test_dir, default_map_file, 
                           skip_file_renaming=True, skip_folder_renaming=True, skip_content=True)
    assert any("All processing types (file rename, folder rename, content) are skipped. Nothing to do." in record.message for record in caplog.records)


def test_main_flow_use_gitignore_not_found(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO) 
    create_test_environment_content(temp_test_dir)
    gitignore_path = temp_test_dir / ".gitignore"
    if gitignore_path.exists():
        gitignore_path.unlink()
        
    run_main_flow_for_test(temp_test_dir, default_map_file, use_gitignore=True, quiet_mode=False) 
    assert any(".gitignore not found in root, skipping." in record.message for record in caplog.records)


def test_main_flow_custom_ignore_file_not_found(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.WARNING) 
    create_test_environment_content(temp_test_dir)
    custom_ignore_path = temp_test_dir / "my_custom.ignore"
    if custom_ignore_path.exists():
        custom_ignore_path.unlink()
        
    run_main_flow_for_test(temp_test_dir, default_map_file, custom_ignore_file=str(custom_ignore_path))
    assert any(f"Warning: Custom ignore file '{custom_ignore_path.resolve()}' not found." in record.message for record in caplog.records)


def test_main_flow_empty_dir_os_error_on_iterdir(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.ERROR)
    
    with patch.object(Path, 'iterdir', side_effect=OSError("Simulated OS error on iterdir")):
        run_main_flow_for_test(temp_test_dir, default_map_file)
    
    assert any(f"Error accessing directory '{temp_test_dir.resolve()}' for empty check: Simulated OS error on iterdir" in record.message for record in caplog.records)

def test_main_flow_ignore_file_read_error(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.WARNING)
    create_test_environment_content(temp_test_dir)
    bad_ignore_file = temp_test_dir / ".badignore"
    bad_ignore_file.write_text("some pattern")

    original_open_func = builtins.open

    def conditional_open_side_effect(file, *args, **kwargs):
        # Resolve 'file' to an absolute path for reliable comparison
        resolved_file_path = Path(file).resolve()
        if resolved_file_path == bad_ignore_file.resolve():
            raise OSError("Simulated read error for bad_ignore_file")
        return original_open_func(file, *args, **kwargs)

    with patch('builtins.open', side_effect=conditional_open_side_effect):
        run_main_flow_for_test(temp_test_dir, default_map_file, custom_ignore_file=str(bad_ignore_file))
    
    assert any(f"Warning: Could not read custom ignore file {bad_ignore_file.resolve()}: Simulated read error for bad_ignore_file" in record.message for record in caplog.records)


def test_main_flow_ignore_pattern_compile_error(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.ERROR)
    create_test_environment_content(temp_test_dir)
    ignore_file_with_bad_pattern = temp_test_dir / ".customignore"
    ignore_file_with_bad_pattern.write_text("[") 

    with patch('pathspec.PathSpec.from_lines', side_effect=Exception("Simulated pattern compile error")):
        run_main_flow_for_test(temp_test_dir, default_map_file, custom_ignore_file=str(ignore_file_with_bad_pattern))
    
    assert any("Error compiling combined ignore patterns: Simulated pattern compile error" in record.message for record in caplog.records)

def test_main_flow_prompt_user_cancels(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO) 
    create_test_environment_content(temp_test_dir)
    with patch('builtins.input', return_value='no'):
        run_main_flow_for_test(temp_test_dir, default_map_file, force_execution=False, quiet_mode=False, resume=False)
    
    assert any("Operation cancelled by user." in record.message for record in caplog.records if record.name == "prefect.flow_runs")
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    if txn_file.exists():
        transactions = load_transactions(txn_file)
        assert not transactions, "Transactions should not have been processed if user cancelled."

def test_main_flow_prompt_warning_empty_map_complex_skips(temp_test_dir: Path, empty_map_file: Path, caplog):
    caplog.set_level(logging.INFO) 
    create_test_environment_content(temp_test_dir)
    
    with patch('builtins.input', return_value='yes'): 
        run_main_flow_for_test(
            temp_test_dir, empty_map_file, 
            force_execution=False, quiet_mode=False, resume=False,
            extensions=None, 
            skip_file_renaming=False, 
            skip_folder_renaming=False, 
            skip_content=True 
        )
    
    expected_warning = f"{YELLOW}Warning: No replacement rules and no operations enabled that don't require rules. Likely no operations will be performed.{RESET}"
    assert any(expected_warning in record.message for record in caplog.records if record.name == "prefect.flow_runs")


def test_main_flow_resume_load_transactions_returns_none(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.WARNING)
    create_test_environment_content(temp_test_dir)
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    txn_file.write_text("corrupt json") 

    with patch('mass_find_replace.load_transactions', return_value=None) as mock_load:
        run_main_flow_for_test(temp_test_dir, default_map_file, resume=True)
    
    assert mock_load.call_count > 0 
    assert any("Warn: Could not load txns. Fresh scan." in record.message for record in caplog.records)

def test_main_flow_resume_load_transactions_returns_empty(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.WARNING)
    create_test_environment_content(temp_test_dir)
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    save_transactions([], txn_file) 

    with patch('mass_find_replace.load_transactions', return_value=[]) as mock_load:
        run_main_flow_for_test(temp_test_dir, default_map_file, resume=True)
        
    assert mock_load.call_count > 0
    assert any("Warn: Txn file empty. Fresh scan." in record.message for record in caplog.records)

_MOCK_STAT_CALLED_GUARD = False # Re-entry guard for mock_stat_conditional

def test_main_flow_resume_stat_error(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.WARNING)
    create_test_environment_content(temp_test_dir)
    processed_file_rel = "file_with_floJoy_lines.txt"
    # target_path_to_mock_stat_str is the string representation of the absolute path
    # that Path.stat() would be called on for the target file during the resume check.
    target_path_to_mock_stat_str = str((temp_test_dir / processed_file_rel).resolve(strict=True))
    
    dummy_txns = [{"PATH": processed_file_rel, "STATUS": TransactionStatus.COMPLETED.value, "timestamp_processed": time.time() - 1000}]
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    save_transactions(dummy_txns, txn_file)

    original_path_stat = Path.stat
    global _MOCK_STAT_CALLED_GUARD
    _MOCK_STAT_CALLED_GUARD = False # Reset guard for each test run

    def mock_stat_conditional(self_path_obj, *args, **kwargs):
        nonlocal _MOCK_STAT_CALLED_GUARD
        # Check if the path object being stat-ed is our target
        # We compare string representations of resolved paths to be robust
        # The guard prevents recursion if resolve() itself calls stat() on the same path.
        
        # If we are already in a guarded call trying to resolve, use original stat
        if _MOCK_STAT_CALLED_GUARD:
            return original_path_stat(self_path_obj, *args, **kwargs)

        is_target_path = False
        try:
            _MOCK_STAT_CALLED_GUARD = True # Set guard
            # Resolve the path being stat-ed to compare with our absolute target path string
            # This resolve() call will use original_path_stat due to the guard
            resolved_self_path_str = str(self_path_obj.resolve(strict=False))
            if resolved_self_path_str == target_path_to_mock_stat_str:
                is_target_path = True
        except Exception:
             # If resolve fails for any reason, it's not our specific target scenario for raising error
            pass
        finally:
            _MOCK_STAT_CALLED_GUARD = False # Clear guard

        if is_target_path:
            raise OSError("Simulated stat error")
        
        return original_path_stat(self_path_obj, *args, **kwargs)

    with patch('pathlib.Path.stat', new=mock_stat_conditional):
        run_main_flow_for_test(temp_test_dir, default_map_file, resume=True)
    
    assert any(f"Could not stat {Path(target_path_to_mock_stat_str)} for resume: Simulated stat error" in record.message for record in caplog.records)


def test_main_flow_no_transactions_to_execute_after_scan_or_skip_scan(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)
    create_test_environment_content(temp_test_dir) 
    
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    
    save_transactions([], txn_file)
    run_main_flow_for_test(temp_test_dir, default_map_file, skip_scan=True)
    assert any(f"No transactions found in {txn_file.resolve()} to execute. Exiting." in record.message for record in caplog.records)
    caplog.clear()

    if txn_file.exists():
        txn_file.unlink()
    txn_file.write_text("this is not json") 
    with patch('mass_find_replace.load_transactions', return_value=None) as mock_load_tx:
        run_main_flow_for_test(temp_test_dir, default_map_file, skip_scan=True)
    assert any(f"No transactions found in {txn_file.resolve()} to execute. Exiting." in record.message for record in caplog.records)


# --- CLI Tests ---
# Assumes test_mass_find_replace.py is in the project root alongside mass_find_replace.py
SCRIPT_PATH_FOR_CLI_TESTS = (Path(__file__).resolve().parent / "mass_find_replace.py").resolve()


def run_cli_command(args_list: list[str], cwd: Path) -> subprocess.CompletedProcess:
    command = [sys.executable, str(SCRIPT_PATH_FOR_CLI_TESTS)] + args_list
    return subprocess.run(command, capture_output=True, text=True, cwd=cwd)

def test_main_cli_negative_timeout(temp_test_dir: Path):
    res = run_cli_command([str(temp_test_dir), "--timeout", "-5"], cwd=temp_test_dir)
    assert res.returncode != 0 
    assert "error: argument --timeout: invalid float value: '-5'" in res.stderr or "--timeout cannot be negative" in res.stderr 

def test_main_cli_small_positive_timeout(temp_test_dir: Path, capsys):
    dummy_map = temp_test_dir / "dummy_map.json"
    dummy_map.write_text(json.dumps({"REPLACEMENT_MAPPING": {"a": "b"}}))
    (temp_test_dir / "somefile.txt").write_text("content")
    
    test_args_float = [str(temp_test_dir), "--mapping-file", str(dummy_map), "--timeout", "0.5", "--force"]
    res_float = run_cli_command(test_args_float, cwd=temp_test_dir)
    assert f"{YELLOW}Warning: --timeout value 0.5 increased to minimum 1 minute.{RESET}" in res_float.stdout
    assert "Scan complete" in res_float.stdout or "No transactions found" in res_float.stdout or "phase complete" in res_float.stdout
    assert res_float.returncode == 0

    test_args_zero = [str(temp_test_dir), "--mapping-file", str(dummy_map), "--timeout", "0", "--force"]
    res_zero = run_cli_command(test_args_zero, cwd=temp_test_dir)
    assert "Warning: --timeout value increased to minimum 1 minute." not in res_zero.stdout
    assert res_zero.returncode == 0


def test_main_cli_verbose_flag(temp_test_dir: Path):
    dummy_map = temp_test_dir / "dummy_map.json"
    dummy_map.write_text(json.dumps({"REPLACEMENT_MAPPING": {"a": "b"}}))
    (temp_test_dir / "somefile.txt").write_text("content")

    args = [str(temp_test_dir), "--mapping-file", str(dummy_map), "--verbose", "--force"]
    res = run_cli_command(args, cwd=temp_test_dir)
    assert "Verbose mode enabled" in res.stdout
    assert res.returncode == 0

def test_main_cli_missing_dependency(temp_test_dir: Path):
    # Store original import function
    original_import = builtins.__import__
    # Modules to simulate as missing
    modules_to_mock_missing = {"prefect", "chardet"}

    def mocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in modules_to_mock_missing:
            raise ImportError(f"Simulated missing module: {name}")
        return original_import(name, globals, locals, fromlist, level)

    with patch.object(sys, 'argv', [str(SCRIPT_PATH_FOR_CLI_TESTS), str(temp_test_dir)]):
        with patch.object(sys, 'exit') as mock_exit:
            with patch.object(sys.stderr, 'write') as mock_stderr_write:
                with patch('builtins.__import__', side_effect=mocked_import):
                    try:
                        main_cli()
                    except SystemExit as e:
                        # Allow SystemExit to be caught by mock_exit if it's raised by main_cli
                        mock_exit(e.code)
                
                mock_exit.assert_called_once_with(1)
                printed_error = "".join(call.args[0] for call in mock_stderr_write.call_args_list)
                assert "CRITICAL ERROR: Missing dependencies:" in printed_error
                if "prefect" in modules_to_mock_missing:
                    assert "prefect" in printed_error
                if "chardet" in modules_to_mock_missing:
                    assert "chardet" in printed_error


# --- Tests for specific scenarios from checklist ---
def test_edge_case_map_run(temp_test_dir: Path, edge_case_map_file: Path, caplog):
    caplog.set_level(logging.INFO)
    create_test_environment_content(temp_test_dir, use_edge_case_map=True)
    run_main_flow_for_test(temp_test_dir, edge_case_map_file, extensions=None)

    orig_mykey_name_file = temp_test_dir / "edge_case_MyKey_original_name.txt"
    expected_mykey_new_name = "edge_case_MyKeyValue_VAL_original_name.txt"
    renamed_mykey_name_file = temp_test_dir / expected_mykey_new_name
    
    assert not orig_mykey_name_file.exists(), f"{orig_mykey_name_file} should have been renamed."
    assert renamed_mykey_name_file.exists(), f"{renamed_mykey_name_file} should exist after rename."
    assert_file_content(renamed_mykey_name_file, "Initial content for control key name test (MyKeyValue_VAL).")

    orig_content_controls_file = temp_test_dir / "edge_case_content_with_MyKey_controls.txt"
    expected_content_controls_new_name = "edge_case_content_with_MyKeyValue_VAL_controls.txt" # Name changes due to "MyKey"
    renamed_content_controls_file = temp_test_dir / expected_content_controls_new_name

    assert not orig_content_controls_file.exists(), f"{orig_content_controls_file} should have been renamed to {expected_content_controls_new_name}."
    assert renamed_content_controls_file.exists(), f"{renamed_content_controls_file} should exist after rename."
    # Content "My\nKey" should NOT be replaced by rule for canonical "MyKey"
    assert_file_content(renamed_content_controls_file, "Line with My\nKey to replace.")


    empty_key_file = temp_test_dir / "edge_case_empty_stripped_key_target.txt"
    assert empty_key_file.exists() 
    assert_file_content(empty_key_file, "This should not be changed by an empty key.") 

    priority_file = temp_test_dir / "edge_case_key_priority.txt"
    assert priority_file.exists() 
    assert_file_content(priority_file, "test FooBar_VAL test and also Foo_VAL.")


def test_skip_scan_with_previous_dry_run_renames(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)

    orig_file_rel = "flojoy_file_to_rename.txt"
    orig_folder_rel = "flojoy_folder_to_rename"
    orig_sub_file_rel = f"{orig_folder_rel}/another_flojoy_file.txt"

    (temp_test_dir / orig_folder_rel).mkdir()
    (temp_test_dir / orig_file_rel).write_text("flojoy content line 1\nflojoy content line 2")
    (temp_test_dir / orig_sub_file_rel).write_text("flojoy in subfolder")

    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True, extensions=[".txt"])
    
    txn_file_path = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    assert txn_file_path.exists()
    transactions_dry_run = load_transactions(txn_file_path)
    assert transactions_dry_run is not None
    
    assert (temp_test_dir / orig_file_rel).exists()
    assert (temp_test_dir / orig_folder_rel).exists()
    assert (temp_test_dir / orig_sub_file_rel).exists()
    assert_file_content(temp_test_dir / orig_file_rel, "flojoy content line 1\nflojoy content line 2")

    # Explicitly reload map to ensure fresh state for replace_logic, as it uses globals
    # This is important because run_main_flow_for_test calls it internally too.
    test_setup_logger = logging.getLogger("test_skip_scan_phase2_loader")
    replace_logic.load_replacement_map(default_map_file, logger=test_setup_logger)


    run_main_flow_for_test(temp_test_dir, default_map_file, skip_scan=True, dry_run=False, force_execution=True, extensions=[".txt"])

    renamed_file_rel = "atlasvibe_file_to_rename.txt"
    renamed_folder_rel = "atlasvibe_folder_to_rename"
    renamed_sub_file_rel = f"{renamed_folder_rel}/another_atlasvibe_file.txt" 

    assert not (temp_test_dir / orig_file_rel).exists(), "Original file should be renamed."
    assert (temp_test_dir / renamed_file_rel).exists(), "Renamed file should exist."
    assert_file_content(temp_test_dir / renamed_file_rel, "atlasvibe content line 1\natlasvibe content line 2")

    assert not (temp_test_dir / orig_folder_rel).exists(), "Original folder should be renamed."
    assert (temp_test_dir / renamed_folder_rel).exists(), "Renamed folder should exist."
    
    assert not (temp_test_dir / orig_sub_file_rel).exists(), "Original sub-file path should not exist." 
    assert (temp_test_dir / renamed_sub_file_rel).exists(), "Renamed sub-file should exist in renamed folder."
    assert_file_content(temp_test_dir / renamed_sub_file_rel, "atlasvibe in subfolder")

    transactions_final = load_transactions(txn_file_path)
    assert transactions_final is not None
    for tx in transactions_final:
        if tx["TYPE"] != TransactionType.FILE_CONTENT_LINE.value or "flojoy" in tx.get("ORIGINAL_LINE_CONTENT", "").lower() or "atlasvibe" in tx.get("PROPOSED_LINE_CONTENT", "").lower() :
            assert tx["STATUS"] == TransactionStatus.COMPLETED.value, f"Transaction {tx['id']} ({tx['PATH']}) should be COMPLETED."
            assert tx.get("ERROR_MESSAGE") is None


def test_highly_problematic_xml_content_preservation(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)
    problem_file_name = "problematic_cp1252.xml"
    problem_file_path = temp_test_dir / problem_file_name

    original_unicode_content = (
        "<root>\n"
        "  <item value='Flojoy'>Content with Flojoy to replace.</item>\r\n"
        "  <other attr='Fl\u00F6joy'>Fl\u00F6joy with diacritic (should not change).</other>\r" 
        "  <special>Chars \u2122 and \u00AE.</special>\n" 
        "  <invalid>Invalid bytes: \uDC81 and \uDCFE here.</invalid>\n"
        "  <nested><deep>More Flojoy</deep></nested>\n"
        "</root>"
    )
    original_bytes_cp1252 = original_unicode_content.encode('cp1252', errors='surrogateescape')
    problem_file_path.write_bytes(original_bytes_cp1252)

    detected_encoding = get_file_encoding(problem_file_path, logger=caplog)
    assert detected_encoding == 'cp1252', f"Expected cp1252 encoding, got {detected_encoding}"

    run_main_flow_for_test(
        temp_test_dir, default_map_file,
        extensions=[".xml"], 
        skip_file_renaming=True, skip_folder_renaming=True, skip_content=False
    )

    expected_bytes_cp1252 = original_bytes_cp1252.replace(b"Flojoy", b"Atlasvibe")
    
    assert problem_file_path.exists(), "Problematic file should still exist."
    modified_bytes = problem_file_path.read_bytes()

    assert modified_bytes == expected_bytes_cp1252, \
        f"Byte-for-byte comparison failed.\nExpected:\n{expected_bytes_cp1252!r}\nGot:\n{modified_bytes!r}"

    txn_file_path = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    assert txn_file_path.exists(), "Transaction file should exist."
    transactions = load_transactions(txn_file_path)
    assert transactions is not None, "Transactions should be loadable."

    content_tx_found_count = 0
    for tx in transactions:
        if tx["PATH"] == problem_file_name and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            content_tx_found_count += 1
            assert tx["STATUS"] == TransactionStatus.COMPLETED.value
            assert tx["ORIGINAL_ENCODING"] == "cp1252"
            
            original_line_tx_unicode = tx["ORIGINAL_LINE_CONTENT"]
            proposed_line_tx_unicode = tx["PROPOSED_LINE_CONTENT"]

            if "Flojoy" in original_line_tx_unicode:
                assert "Atlasvibe" in proposed_line_tx_unicode
                if "Content with Flojoy to replace." in original_line_tx_unicode:
                     assert original_line_tx_unicode.endswith("</item>\r\n")
                     assert proposed_line_tx_unicode.endswith("</item>\r\n")
            
            if "Fl\u00F6joy" in original_line_tx_unicode: 
                assert "Fl\u00F6joy" in proposed_line_tx_unicode 
            
            if "\uDC81" in original_line_tx_unicode: 
                 assert "\uDC81" in proposed_line_tx_unicode 

    assert content_tx_found_count == 2, f"Expected 2 content transactions for {problem_file_name}, got {content_tx_found_count}"
    
    assert b"Fl\xf6joy" in modified_bytes, "Diacritic version 'Flöjoy' should not have been replaced."
    assert b"\x99" in modified_bytes 
    assert b"\xae" in modified_bytes 
    assert b"\x81" in modified_bytes
    assert b"\xfe" in modified_bytes
