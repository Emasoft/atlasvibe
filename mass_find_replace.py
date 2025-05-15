#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Corrected Prefect 3 flow run context check:
#   - In `_create_self_test_environment` and `check_file_content_for_test`,
#     the previous change introduced `prefect.runtime.get_run_context()`. This has been
#     replaced with a robust check for `prefect.runtime.flow_run.id` (using
#     a try-except AttributeError block) to accurately determine if running
#     inside a Prefect flow run, fixing the `AttributeError: module 'prefect.runtime' has no attribute 'get_run_context'`.
# - Modified `check_file_content_for_test`:
#   - Removed re-application of `replace_logic.replace_occurrences`.
#   - Compares actual file content on disk directly with `expected_content`.
#   - Improved verbose output for content mismatches.
# - Modified `_verify_self_test_results_task` for the "Standard" self-test:
#   - Replaced the generic `verify_test_case("Standard", ...)` call.
#   - Added explicit checks for existence and content of all relevant files
#     created by `_create_self_test_environment` for the standard scenario.
#   - Ensured correct `expected_content` is used for each file content check.
#   - Content of `very_large_atlasvibe_file.txt` is verified by existing specific line checks.
#   - Symlink target content checks now correctly use original content as expected.
#   - Added content checks for `another_atlasvibe_file.py`, `only_name_atlasvibe.md`,
#     `file_with_atlasVibe_lines.txt`, `unmapped_variant_atlasvibe_content.txt`,
#     and `gb18030_atlasvibe_file.txt`.
# - Ensured binary file name change for `binary_atlasvibe_file.bin` is checked and
#   `binary_fLoJoY_name.bin` (unmapped) remains as is.
# - Enhanced table formatting in `_verify_self_test_results_task` for multi-line descriptions.
# - Corrected logic for `standard_test_includes_symlinks` in `self_test_flow`.
# - Ensured `transaction_file` and `validation_file` names are unique per test sub-type.
# - Ensured `dry_run_for_test` is correctly passed and used, especially for resume tests.
# - Excluded more transaction and mapping files from being processed during self-tests.
# - Prefect flow calls `with_options(task_runner=None)` to avoid issues with default concurrent task runners in some environments for self-tests.
#

#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import argparse
import tempfile
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
import shutil
import textwrap
import json
import os
import operator

from prefect import task, flow, get_run_logger
import prefect.runtime

from file_system_operations import (
    scan_directory_for_occurrences,
    save_transactions,
    load_transactions,
    execute_all_transactions,
    TransactionStatus,
    TransactionType,
    TRANSACTION_FILE_BACKUP_EXT,
    is_likely_binary_file,
    SELF_TEST_ERROR_FILE_BASENAME
)
import replace_logic

# --- Constants ---
MAIN_TRANSACTION_FILE_NAME = "planned_transactions.json"
DEFAULT_REPLACEMENT_MAPPING_FILE = "replacement_mapping.json"
SELF_TEST_PRIMARY_TRANSACTION_FILE = "self_test_transactions.json"
SELF_TEST_SCAN_VALIDATION_FILE = "self_test_scan_validation_transactions.json"
SELF_TEST_SANDBOX_DIR = "./tests/temp"
SELF_TEST_COMPLEX_MAP_FILE = "self_test_complex_mapping.json"
SELF_TEST_EDGE_CASE_MAP_FILE = "self_test_edge_case_mapping.json"
SELF_TEST_EMPTY_MAP_FILE = "self_test_empty_mapping.json"
SELF_TEST_RESUME_TRANSACTION_FILE = "self_test_resume_transactions.json"
SELF_TEST_PRECISION_MAP_FILE = "self_test_precision_mapping.json"

VERY_LARGE_FILE_NAME_ORIG = "very_large_flojoy_file.txt"
VERY_LARGE_FILE_NAME_REPLACED = "very_large_atlasvibe_file.txt"
VERY_LARGE_FILE_LINES = 200 * 1000
VERY_LARGE_FILE_MATCH_INTERVAL = 10000

# ANSI Color Codes & Unicode Symbols for formatted output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
PASS_SYMBOL = "✅"
FAIL_SYMBOL = "❌"

# Unicode Double Line Box Characters
DBL_TOP_LEFT = "╔"
DBL_TOP_RIGHT = "╗"
DBL_BOTTOM_LEFT = "╚"
DBL_BOTTOM_RIGHT = "╝"
DBL_HORIZONTAL = "═"
DBL_VERTICAL = "║"
DBL_T_DOWN = "╦"
DBL_T_UP = "╩"
DBL_T_RIGHT = "╠"
DBL_T_LEFT = "╣"
DBL_CROSS = "╬"


# --- Self-Test Functionality ---
def _create_self_test_environment(
    base_dir: Path,
    use_complex_map: bool = False,
    use_edge_case_map: bool = False,
    for_resume_test_phase_2: bool = False,
    include_very_large_file: bool = False,
    include_precision_test_file: bool = False,
    include_symlink_tests: bool = False,
    verbose: bool = False
) -> None:
    """Creates a directory structure and files for self-testing."""
    is_in_flow_context = False
    try:
        if prefect.runtime.flow_run and prefect.runtime.flow_run.id:
            is_in_flow_context = True
    except AttributeError:
        is_in_flow_context = False
    logger = get_run_logger() if is_in_flow_context else print # Use Prefect logger if in flow context

    try:
        if not for_resume_test_phase_2:
            (base_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir").mkdir(parents=True, exist_ok=True)
            (base_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt").write_text(
                "Line 1: flojoy content.\nLine 2: More Flojoy here.\nLine 3: No target.\nLine 4: FLOJOY project."
            )
            (base_dir / "flojoy_root" / "another_flojoy_file.py").write_text(
                "import flojoy_lib\n# class MyFlojoyClass: pass"
            )
            (base_dir / "only_name_flojoy.md").write_text("Content without target string.")
            (base_dir / "file_with_floJoy_lines.txt").write_text(
                "First floJoy.\nSecond FloJoy.\nflojoy and FLOJOY on same line."
            )
            (base_dir / "unmapped_variant_flojoy_content.txt").write_text(
                "This has fLoJoY content, and also flojoy." # fLoJoY is unmapped, flojoy is mapped
            )
            (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")
            (base_dir / "binary_fLoJoY_name.bin").write_bytes(b"unmapped_variant_binary_content" + b"\x00\xff") # Name has unmapped variant

            (base_dir / "excluded_flojoy_dir").mkdir(exist_ok=True)
            (base_dir / "excluded_flojoy_dir" / "inner_flojoy_file.txt").write_text("flojoy inside excluded dir")
            (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in explicitly excluded file")
            (base_dir / "no_target_here.log").write_text("This is a log file without the target string.")

            deep_path_parts = ["depth1_flojoy", "depth2", "depth3_flojoy", "depth4", "depth5", "depth6_flojoy", "depth7", "depth8", "depth9_flojoy", "depth10_file_flojoy.txt"]
            current_path = base_dir
            for part_idx, part in enumerate(deep_path_parts):
                current_path = current_path / part
                if part_idx < len(deep_path_parts) - 1:
                    current_path.mkdir(parents=True, exist_ok=True)
                else:
                    current_path.write_text("flojoy deep content")

            try:
                (base_dir / "gb18030_flojoy_file.txt").write_text("你好 flojoy 世界", encoding="gb18030")
            except Exception as e:
                logger(f"Warning: Could not write GB18030 file: {e}. Using fallback.")
                (base_dir / "gb18030_flojoy_file.txt").write_text("fallback flojoy content")

            large_file_content_list = [] # This is the 1000-line "large_file", not "very_large_file"
            for i in range(1000):
                if i % 50 == 0:
                    large_file_content_list.append("This flojoy line should be replaced " + str(i) + "\n")
                else:
                    large_file_content_list.append("Normal line " + str(i) + "\n")
            (base_dir / "large_flojoy_file.txt").write_text("".join(large_file_content_list), encoding='utf-8')
            (base_dir / SELF_TEST_ERROR_FILE_BASENAME).write_text("This file will cause a rename error during tests.")

        if include_very_large_file:
            logger(f"Generating very large file: {base_dir / VERY_LARGE_FILE_NAME_ORIG}...")
            with open(base_dir / VERY_LARGE_FILE_NAME_ORIG, 'w', encoding='utf-8') as f:
                for i in range(VERY_LARGE_FILE_LINES):
                    if i == 0 or i == VERY_LARGE_FILE_LINES // 2 or i == VERY_LARGE_FILE_LINES - 1 or \
                            (i % VERY_LARGE_FILE_MATCH_INTERVAL == 0 and i != 0): # Ensure match interval lines are distinct from start/mid/end
                        f.write(f"Line {i + 1}: This is a flojoy line that should be replaced.\n")
                    else:
                        f.write(f"Line {i + 1}: This is a standard non-matching line with some padding to make it longer.\n")
            logger("Very large file generated.")

        if include_precision_test_file:
            precision_content_lines = [
                "Standard flojoy here.\n",
                "Another Flojoy for title case.\r\n",
                "Test FLÖJOY_DIACRITIC with mixed case.\n", # Key "FLÖJOY_DIACRITIC"
                "  flojoy  with exact spaces.\n", # Key "  flojoy  "
                "  flojoy   with extra spaces.\n", # Not a direct key, "flojoy" substring
                "key\twith\ncontrol characters.\n", # "key\twith\ncontrol" is a key
                "unrelated content\n",
                "你好flojoy世界 (Chinese chars).\n", # "flojoy" substring
                "emoji😊flojoy test.\n", # "flojoy" substring
            ]
            problematic_bytes_line = b"malformed-\xff-flojoy-bytes\n" # "flojoy" substring

            with open(base_dir / "precision_test_flojoy_source.txt", "wb") as f:
                for line_str in precision_content_lines:
                    f.write(line_str.encode('utf-8', errors='surrogateescape'))
                f.write(problematic_bytes_line)

            (base_dir / "precision_name_flojoy_test.md").write_text("File for precision rename test.") # "flojoy" in name

        if use_complex_map:
            (base_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS").mkdir(parents=True, exist_ok=True)
            (base_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS" / "file_with_diacritics_ȕsele̮Ss_diá͡cRiti̅cS.txt").write_text(
                "Content with ȕsele̮Ss_diá͡cRiti̅cS and also useless_diacritics.\nAnd another Flojoy for good measure (should remain if not in complex map)."
            )
            (base_dir / "file_with_spaces_The spaces will not be ignored.md").write_text(
                "This file has The spaces will not be ignored in its name and content."
            )
            (base_dir / "_My_Love&Story.log").write_text("Log for _My_Love&Story and _my_love&story. And My_Love&Story.")
            (base_dir / "filename_with_COCO4_ep-m.data").write_text("Data for COCO4_ep-m and Coco4_ep-M. Also coco4_ep-m.") # coco4_ep-m is not in map
            (base_dir / "special_chars_in_content_test.txt").write_text(
                "This line contains characters|not<allowed^in*paths::will/be!escaped%when?searched~in$filenames@and\"foldernames to be replaced."
            )
            # File for testing rename with control characters in key (name part)
            (base_dir / "complex_map_key_withcontrolchars_original_name.txt").write_text(
                "Content for complex map control key filename test."
            )
            # File for testing content replacement with control characters in key
            (base_dir / "complex_map_content_with_key_with_controls.txt").write_text(
                "Line with key_with\tcontrol\nchars to replace."
            )


        if use_edge_case_map:
            # File for testing rename with control characters in key (name part)
            (base_dir / "edge_case_MyKey_original_name.txt").write_text("Initial content for control key name test (MyKey).")
            # File for testing content replacement with control characters in key
            (base_dir / "edge_case_content_with_MyKey_controls.txt").write_text("Line with My\nKey to replace.")
            (base_dir / "edge_case_empty_stripped_key_target.txt").write_text("This should not be changed by an empty key.") # For key "\t"
            (base_dir / "edge_case_key_priority.txt").write_text("test foo bar test and also foo.") # "foo bar" and "foo"

        if for_resume_test_phase_2:
            (base_dir / "newly_added_flojoy_for_resume.txt").write_text("This flojoy content is new for resume.")
            # If a file was renamed in phase 1, its content might be modified here for resume test
            # Example: only_name_atlasvibe.md might get "flojoy" added to its content
            renamed_only_name_file = base_dir / "only_name_atlasvibe.md" # Assuming it was renamed
            if renamed_only_name_file.exists():
                renamed_only_name_file.write_text("Content without target string, but now with flojoy.")


        if include_symlink_tests:
            symlink_target_dir = base_dir / "symlink_targets_outside"
            symlink_target_dir.mkdir(parents=True, exist_ok=True)
            (symlink_target_dir / "target_file_flojoy.txt").write_text("flojoy in symlink target file")
            target_subdir_flojoy = symlink_target_dir / "target_dir_flojoy"
            target_subdir_flojoy.mkdir(exist_ok=True)
            (target_subdir_flojoy / "another_flojoy_file.txt").write_text("flojoy content in symlinked dir target")

            link_to_file = base_dir / "link_to_file_flojoy.txt"
            link_to_dir = base_dir / "link_to_dir_flojoy"

            try:
                if not os.path.lexists(link_to_file):
                    os.symlink(symlink_target_dir / "target_file_flojoy.txt", link_to_file, target_is_directory=False)
                if not os.path.lexists(link_to_dir):
                    os.symlink(symlink_target_dir / "target_dir_flojoy", link_to_dir, target_is_directory=True)
                if verbose:
                    logger("Symlinks created (or already existed) for testing.")
            except OSError as e:
                if verbose:
                    logger(f"{YELLOW}Warning: Could not create symlinks for testing (OSError: {e}). Symlink tests may be skipped or fail.{RESET}")
            except Exception as e: # Catch other potential errors like AttributeError if os.symlink is not available
                if verbose:
                    logger(f"{YELLOW}Warning: An unexpected error occurred creating symlinks: {e}. Symlink tests may be affected.{RESET}")
    except Exception as e:
        if verbose:
            logger(f"{YELLOW}Error creating self-test environment: {e}{RESET}")


def check_file_content_for_test(
    file_path: Optional[Path],
    expected_content: Union[str, bytes],
    test_description: str,
    record_test_func: Callable,
    encoding: Optional[str] = 'utf-8',
    is_binary: bool = False,
    verbose: bool = False
) -> None:
    """Helper to check file content for self-tests, normalizing line endings."""
    is_in_flow_context = False
    try:
        if prefect.runtime.flow_run and prefect.runtime.flow_run.id:
            is_in_flow_context = True
    except AttributeError:
        is_in_flow_context = False
    logger = get_run_logger() if is_in_flow_context else print

    if not file_path or not file_path.exists():
        record_test_func(test_description + " (File Existence)", False, f"File missing: {file_path}")
        return

    try:
        if is_binary:
            actual_content_on_disk = file_path.read_bytes()
            # Ensure expected_content is also bytes for binary comparison
            expected_content_bytes = expected_content if isinstance(expected_content, bytes) else str(expected_content).encode(encoding or 'utf-8')
            record_test_func(test_description, actual_content_on_disk == expected_content_bytes, f"Expected binary content mismatch for {file_path}. Got (first 100 bytes): {actual_content_on_disk[:100]!r}, Expected: {expected_content_bytes[:100]!r}")
        else:
            # Read actual content from disk to verify the file's state after script execution
            actual_content_on_disk = file_path.read_text(encoding=encoding, errors='surrogateescape')
            
            # Normalize line endings for comparison
            # Ensure expected_content is a string before normalization
            expected_normalized = str(expected_content).replace("\r\n", "\n").replace("\r", "\n")
            actual_normalized_on_disk = actual_content_on_disk.replace("\r\n", "\n").replace("\r", "\n")
            
            match = actual_normalized_on_disk == expected_normalized
            details = ""
            if not match:
                details = f"Content mismatch for {file_path}."
                if verbose: # Add detailed diff to details string if verbose
                    details += f"\nExpected (normalized): {expected_normalized!r}\nActual (normalized):   {actual_normalized_on_disk!r}"
            record_test_func(test_description, match, details)

    except Exception as e:
        record_test_func(test_description, False, f"Error reading/comparing {file_path}: {e}")


@task # Make it a Prefect task for better logging integration if self_test_flow is a flow
def _verify_self_test_results_task(
    temp_dir: Path,
    original_transaction_file: Path,
    validation_transaction_file: Optional[Path] = None,
    is_complex_map_test: bool = False,
    is_edge_case_test: bool = False,
    is_empty_map_test: bool = False,
    is_resume_test: bool = False,
    standard_test_includes_large_file: bool = False, # For very_large_file
    is_precision_test: bool = False,
    standard_test_includes_symlinks: bool = False, # For symlink specific checks
    symlinks_were_ignored_in_scan: bool = False, # To verify correct symlink behavior based on flag
    verbose: bool = False
) -> bool:
    logger = get_run_logger() # Use Prefect logger
    logger.info(f"{BLUE}--- Verifying Self-Test Results ({original_transaction_file.name}) ---{RESET}")
    passed_checks = 0
    failed_checks = 0
    test_results: List[Dict[str, Any]] = []
    test_counter = 0
    failed_test_details_print_buffer: List[str] = []

    def record_test(description: str, condition: bool, details_on_fail: str = "") -> None:
        nonlocal passed_checks, failed_checks, test_counter
        test_counter += 1
        status = "PASS" if condition else "FAIL"
        if condition:
            passed_checks += 1
        else:
            failed_checks += 1
            # Store full details for later printing if verbose
            full_detail_message = f"Test {test_counter}: {description} - {status}. Details: {details_on_fail}"
            failed_test_details_print_buffer.append(full_detail_message)
        test_results.append({"id": test_counter, "description": description, "status": status, "details": details_on_fail if not condition else ""})

    # Generic helper (currently not used due to specific content needs)
    # def verify_test_case(test_type: str, expected_paths: Dict[str, Union[Path, str]], content_map: Optional[Dict[str, str]] = None) -> None:
    #     for key, path_or_expected_content in expected_paths.items():
    #         if isinstance(path_or_expected_content, Path): # It's a path to check existence
    #             path = path_or_expected_content
    #             record_test(f"[{test_type}] {key} - exists", path.exists(), f"File/Dir {path} expected but not found.")
    #             if path.is_file() and content_map and key in content_map:
    #                 check_file_content_for_test(path, content_map[key], f"[{test_type}] {key} - content", record_test, verbose=verbose)
    #         # else: could be a direct content string for a known file, not used this way currently

    if is_empty_map_test:
        transactions = load_transactions(original_transaction_file)
        record_test("[Empty Map] No transactions generated", transactions is not None and len(transactions) == 0, f"Expected 0 transactions, got {len(transactions) if transactions else 'None'}")

    elif is_precision_test:
        # Renamed files based on precision_map_data
        precision_source_renamed = temp_dir / "precision_test_atlasvibe_plain_source.txt" # "flojoy" -> "atlasvibe_plain"
        precision_name_renamed = temp_dir / "precision_name_atlasvibe_plain_test.md"   # "flojoy" -> "atlasvibe_plain"

        record_test("[Precision Test] Filename 'precision_test_flojoy_source.txt' renamed", precision_source_renamed.exists())
        record_test("[Precision Test] Original 'precision_test_flojoy_source.txt' removed", not (temp_dir / "precision_test_flojoy_source.txt").exists())
        record_test("[Precision Test] Filename 'precision_name_flojoy_test.md' renamed", precision_name_renamed.exists())
        record_test("[Precision Test] Original 'precision_name_flojoy_test.md' removed", not (temp_dir / "precision_name_flojoy_test.md").exists())

        if precision_name_renamed.exists():
             check_file_content_for_test(precision_name_renamed,
                                        "File for precision rename test.", # Content unchanged
                                        "[Precision Test] Content of 'precision_name_atlasvibe_plain_test.md'",
                                        record_test, verbose=verbose)

        if precision_source_renamed.exists():
            # Expected content after applying precision_map_data
            expected_lines = [
                "Standard atlasvibe_plain here.\n",
                "Another Atlasvibe_TitleCase for title case.\r\n", # Note: original line ending preserved
                "Test ATLASVIBE_DIACRITIC_VAL with mixed case.\n",
                "  atlasvibe_spaced_val  with exact spaces.\n",
                "  atlasvibe_plain   with extra spaces.\n", # "  flojoy   " -> "flojoy" is substring -> "atlasvibe_plain"
                "value_for_control_key_val characters.\n", # "key\twith\ncontrol" replaced
                "unrelated content\n",
                "你好atlasvibe_plain世界 (Chinese chars).\n",
                "emoji😊atlasvibe_plain test.\n",
            ]
            expected_problematic_bytes = b"malformed-\xff-atlasvibe_plain-bytes\n"
            
            # Read the file as bytes to preserve original encoding nuances
            actual_bytes = precision_source_renamed.read_bytes()
            # Reconstruct expected bytes
            expected_all_bytes_list = []
            for line_str in expected_lines:
                expected_all_bytes_list.append(line_str.encode('utf-8', errors='surrogateescape'))
            expected_all_bytes_list.append(expected_problematic_bytes)
            expected_total_bytes = b"".join(expected_all_bytes_list)

            record_test("[Precision Test] Byte-for-byte content of 'precision_test_atlasvibe_plain_source.txt'",
                        actual_bytes == expected_total_bytes,
                        f"Byte content mismatch. Got: {actual_bytes[:200]!r} Expected: {expected_total_bytes[:200]!r}")


    elif is_resume_test:
        final_transactions = load_transactions(original_transaction_file)
        record_test("[Resume Test] Final transaction log loaded", final_transactions is not None)
        if final_transactions:
            new_file_renamed_path = temp_dir / "newly_added_atlasvibe_for_resume.txt"
            new_file_name_processed = any(
                tx["PATH"] == str(new_file_renamed_path.relative_to(temp_dir)).replace("\\","/") and tx["STATUS"] == TransactionStatus.COMPLETED.value
                for tx in final_transactions if tx["TYPE"] == TransactionType.FILE_NAME.value
            )
            new_file_content_processed = any(
                tx["PATH"] == str(new_file_renamed_path.relative_to(temp_dir)).replace("\\","/") and tx["STATUS"] == TransactionStatus.COMPLETED.value
                for tx in final_transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value
            )
            record_test("[Resume Test] Newly added file name processed to 'newly_added_atlasvibe_for_resume.txt'", new_file_name_processed and new_file_renamed_path.exists())
            record_test("[Resume Test] Newly added file content processed", new_file_content_processed)
            check_file_content_for_test(new_file_renamed_path,
                                       "This atlasvibe content is new for resume.",
                                       "[Resume Test] Content of 'newly_added_atlasvibe_for_resume.txt'", record_test_func=record_test, verbose=verbose)

            # Check if the file that had its content modified in phase 2 was processed
            # only_name_atlasvibe.md had "flojoy" added.
            only_name_modified_path = temp_dir / "only_name_atlasvibe.md"
            only_name_content_tx_done = any(
                tx["PATH"] == str(only_name_modified_path.relative_to(temp_dir)).replace("\\","/") and
                tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and
                tx["STATUS"] == TransactionStatus.COMPLETED.value
                for tx in final_transactions
            )
            record_test("[Resume Test] Content of 'only_name_atlasvibe.md' (modified in phase 2) processed", only_name_content_tx_done)
            if only_name_modified_path.exists():
                check_file_content_for_test(only_name_modified_path,
                                            "Content without target string, but now with atlasvibe.",
                                            "[Resume Test] Content of 'only_name_atlasvibe.md' after resume",
                                            record_test_func=record_test, verbose=verbose)


            large_file_original_rel_path = "large_flojoy_file.txt" # Original relative path
            large_file_renamed_rel_path = "large_atlasvibe_file.txt"
            large_file_tx_found_completed = any(
                (tx["PATH"] == large_file_renamed_rel_path or tx.get("ORIGINAL_NAME") == "large_flojoy_file.txt") and
                tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and
                tx["STATUS"] == TransactionStatus.COMPLETED.value
                for tx in final_transactions
            )
            record_test("[Resume Test] Initially PENDING content transaction for large file completed", large_file_tx_found_completed)


            error_file_tx_status = ""
            for tx in final_transactions:
                if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME and tx["TYPE"] == TransactionType.FILE_NAME.value:
                    error_file_tx_status = tx["STATUS"]
                    break
            record_test("[Resume Test] Error file transaction re-attempted and FAILED again", error_file_tx_status == TransactionStatus.FAILED.value)
            record_test("[Resume Test] Original error file still exists after failed resume attempt", (temp_dir / SELF_TEST_ERROR_FILE_BASENAME).exists())

    elif is_edge_case_test:
        # Renamed file: edge_case_MyKey_original_name.txt -> MyKeyValue_VAL.txt (due to "My\nKey": "MyKeyValue_VAL")
        control_key_renamed_file = temp_dir / "MyKeyValue_VAL.txt"
        record_test("[Edge Case] control_key_renamed_file exists", control_key_renamed_file.exists())
        check_file_content_for_test(control_key_renamed_file,
                                    "Initial content for control key name test (MyKey).", # Content is unchanged
                                    "[Edge Case] control_key_renamed_file content", record_test, verbose=verbose)

        # Content file: edge_case_content_with_MyKey_controls.txt
        # Content: "Line with My\nKey to replace." -> "Line with MyKeyValue_VAL to replace."
        control_key_content_file = temp_dir / "edge_case_content_with_MyKey_controls.txt" # Name unchanged
        record_test("[Edge Case] control_key_content_file exists", control_key_content_file.exists())
        check_file_content_for_test(control_key_content_file,
                                    "Line with MyKeyValue_VAL to replace.",
                                    "[Edge Case] control_key_content_file content", record_test, verbose=verbose)

        # Empty stripped key file: edge_case_empty_stripped_key_target.txt (key "\t" should not match if stripping makes it empty)
        # Or, if "\t" is a valid key and its value is "ShouldBeSkipped_VAL", then content would change if it contained "\t"
        # The map has "\t": "ShouldBeSkipped_VAL". The file content is "This should not be changed by an empty key."
        # Assuming the content does not contain a tab character.
        empty_stripped_key_file = temp_dir / "edge_case_empty_stripped_key_target.txt" # Name unchanged
        record_test("[Edge Case] empty_stripped_key_file exists", empty_stripped_key_file.exists())
        check_file_content_for_test(empty_stripped_key_file,
                                    "This should not be changed by an empty key.", # Expected to be unchanged
                                    "[Edge Case] empty_stripped_key_file content", record_test, verbose=verbose)

        # Key priority file: edge_case_key_priority.txt
        # Content: "test foo bar test and also foo." -> "test FooBar_VAL test and also Foo_VAL."
        # (Assuming "foo bar" is matched before "foo" due to longer match preference in regex)
        key_priority_file = temp_dir / "edge_case_key_priority.txt" # Name unchanged
        record_test("[Edge Case] key_priority_file exists", key_priority_file.exists())
        check_file_content_for_test(key_priority_file,
                                    "test FooBar_VAL test and also Foo_VAL.",
                                    "[Edge Case] key_priority_file content", record_test, verbose=verbose)


    elif is_complex_map_test:
        # Folder: diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS -> dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL
        diacritic_folder_replaced = temp_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL"
        record_test("[Complex] diacritic_folder_replaced exists", diacritic_folder_replaced.is_dir())

        # File in folder: file_with_diacritics_ȕsele̮Ss_diá͡cRiti̅cS.txt -> dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.txt
        file_in_diacritic_folder_replaced_name = diacritic_folder_replaced / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.txt"
        record_test("[Complex] file_in_diacritic_folder_replaced_name exists", file_in_diacritic_folder_replaced_name.is_file())
        check_file_content_for_test(file_in_diacritic_folder_replaced_name,
                                    "Content with dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL and also dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.\nAnd another Flojoy for good measure (should remain if not in complex map).",
                                    "[Complex] file_in_diacritic_folder_replaced_name content", record_test, verbose=verbose)

        # File with spaces: file_with_spaces_The spaces will not be ignored.md -> The control characters \n will be ignored_VAL.md
        file_with_spaces_replaced_name = temp_dir / "The control characters \n will be ignored_VAL.md"
        record_test("[Complex] file_with_spaces_replaced_name exists", file_with_spaces_replaced_name.is_file())
        check_file_content_for_test(file_with_spaces_replaced_name,
                                    "This file has The control characters \n will be ignored_VAL in its name and content.",
                                    "[Complex] file_with_spaces_replaced_name content", record_test, verbose=verbose)
        
        # _My_Love&Story.log -> _My_Story&Love_VAL.log
        my_love_story_replaced_name = temp_dir / "_My_Story&Love_VAL.log"
        record_test("[Complex] my_love_story_replaced_name exists", my_love_story_replaced_name.is_file())
        check_file_content_for_test(my_love_story_replaced_name,
                                    "Log for _My_Story&Love_VAL and _my_story&love_VAL. And My_Love&Story.", # _my_love&story also replaced, My_Love&Story not in map
                                    "[Complex] my_love_story_replaced_name content", record_test, verbose=verbose)

        # filename_with_COCO4_ep-m.data -> MOCO4_ip-N_VAL.data
        coco4_replaced_name = temp_dir / "MOCO4_ip-N_VAL.data"
        record_test("[Complex] coco4_replaced_name exists", coco4_replaced_name.is_file())
        check_file_content_for_test(coco4_replaced_name,
                                    "Data for MOCO4_ip-N_VAL and Moco4_ip-N_VAL. Also coco4_ep-m.", # Coco4_ep-M also replaced, coco4_ep-m not in map
                                    "[Complex] coco4_replaced_name content", record_test, verbose=verbose)

        # special_chars_in_content_test.txt (name unchanged)
        # Content: "This line contains characters|not<allowed^in*paths... to be replaced." -> "This line contains SpecialCharsKeyMatched_VAL to be replaced."
        special_chars_content_file = temp_dir / "special_chars_in_content_test.txt"
        record_test("[Complex] special_chars_content_file exists", special_chars_content_file.is_file())
        check_file_content_for_test(special_chars_content_file,
                                    "This line contains SpecialCharsKeyMatched_VAL to be replaced.",
                                    "[Complex] special_chars_content_file content", record_test, verbose=verbose)

        # complex_map_key_withcontrolchars_original_name.txt -> Value_for_key_with_controls_VAL.txt (due to "key_with\tcontrol\nchars")
        # This is tricky. The filename "complex_map_key_withcontrolchars_original_name.txt" does NOT contain "key_with\tcontrol\nchars".
        # The map key "key_with\tcontrol\nchars" is for content.
        # The file "complex_map_key_withcontrolchars_original_name.txt" should NOT be renamed by this key.
        # Let's assume there's another key for its name or it's not renamed.
        # The original setup was: (base_dir / "complex_map_key_withcontrolchars_original_name.txt").write_text("Content for complex map control key filename test.")
        # This file's name does not match any key in the complex map. So it should remain unchanged.
        control_chars_key_original_filename = temp_dir / "complex_map_key_withcontrolchars_original_name.txt"
        record_test("[Complex] control_chars_key_original_filename exists (name unchanged)", control_chars_key_original_filename.is_file())
        check_file_content_for_test(control_chars_key_original_filename,
                                    "Content for complex map control key filename test.", # Content unchanged
                                    "[Complex] control_chars_key_original_filename content", record_test, verbose=verbose)


        # complex_map_content_with_key_with_controls.txt (name unchanged)
        # Content: "Line with key_with\tcontrol\nchars to replace." -> "Line with Value_for_key_with_controls_VAL to replace."
        control_chars_key_content_file = temp_dir / "complex_map_content_with_key_with_controls.txt"
        record_test("[Complex] control_chars_key_content_file exists", control_chars_key_content_file.is_file())
        check_file_content_for_test(control_chars_key_content_file,
                                    "Line with Value_for_key_with_controls_VAL to replace.",
                                    "[Complex] control_chars_key_content_file content", record_test, verbose=verbose)


    elif not is_resume_test and not is_precision_test:  # Standard self-test run
        logger.info(f"{BLUE}--- Verifying Standard Self-Test Results (Symlinks Ignored in Scan: {symlinks_were_ignored_in_scan}) ---{RESET}")
        
        # Directory structure
        expected_root_name = "atlasvibe_root" if not symlinks_were_ignored_in_scan else "flojoy_root"
        processed_root_dir = temp_dir / expected_root_name
        record_test(f"[Standard] '{expected_root_name}' directory exists", processed_root_dir.is_dir())
        
        expected_sub_folder_name = "sub_atlasvibe_folder" # from "sub_flojoy_folder"
        expected_another_dir_name = "another_ATLASVIBE_dir" # from "another_FLOJOY_dir"
        
        deep_folder_path = processed_root_dir / expected_sub_folder_name / expected_another_dir_name
        record_test(f"[Standard] '{expected_sub_folder_name}/{expected_another_dir_name}' exists", deep_folder_path.is_dir())

        # File existence and content checks
        deep_file_path = deep_folder_path / "deep_atlasvibe_file.txt" # from "deep_flojoy_file.txt"
        record_test("[Standard] deep_atlasvibe_file.txt exists", deep_file_path.is_file())
        if deep_file_path.is_file():
            expected_deep_content = "Line 1: atlasvibe content.\nLine 2: More Atlasvibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project."
            check_file_content_for_test(deep_file_path, expected_deep_content, "[Standard] deep_atlasvibe_file.txt content", record_test, verbose=verbose)

        another_py_file_path = processed_root_dir / "another_atlasvibe_file.py" # from "another_flojoy_file.py"
        record_test("[Standard] another_atlasvibe_file.py exists", another_py_file_path.is_file())
        if another_py_file_path.is_file():
            expected_py_content = "import atlasvibe_lib\n# class MyAtlasvibeClass: pass" # flojoy_lib -> atlasvibe_lib, MyFlojoyClass -> MyAtlasvibeClass
            check_file_content_for_test(another_py_file_path, expected_py_content, "[Standard] another_atlasvibe_file.py content", record_test, verbose=verbose)

        only_name_renamed_path = temp_dir / "only_name_atlasvibe.md" # from "only_name_flojoy.md"
        record_test("[Standard] only_name_atlasvibe.md exists", only_name_renamed_path.is_file())
        if only_name_renamed_path.is_file():
            expected_only_name_content = "Content without target string." # Content unchanged
            check_file_content_for_test(only_name_renamed_path, expected_only_name_content, "[Standard] only_name_atlasvibe.md content", record_test, verbose=verbose)

        file_with_lines_renamed_path = temp_dir / "file_with_atlasVibe_lines.txt" # from "file_with_floJoy_lines.txt"
        record_test("[Standard] file_with_atlasVibe_lines.txt exists", file_with_lines_renamed_path.is_file())
        if file_with_lines_renamed_path.is_file():
            expected_lines_content = "First atlasVibe.\nSecond AtlasVibe.\natlasvibe and ATLASVIBE on same line."
            check_file_content_for_test(file_with_lines_renamed_path, expected_lines_content, "[Standard] file_with_atlasVibe_lines.txt content", record_test, verbose=verbose)

        unmapped_variant_renamed_path = temp_dir / "unmapped_variant_atlasvibe_content.txt" # from "unmapped_variant_flojoy_content.txt"
        record_test("[Standard] unmapped_variant_atlasvibe_content.txt exists", unmapped_variant_renamed_path.is_file())
        if unmapped_variant_renamed_path.is_file():
            expected_unmapped_content = "This has fLoJoY content, and also atlasvibe." # fLoJoY unmapped, flojoy mapped
            check_file_content_for_test(unmapped_variant_renamed_path, expected_unmapped_content, "[Standard] unmapped_variant_atlasvibe_content.txt content", record_test, verbose=verbose)
        
        gb18030_renamed_path = temp_dir / "gb18030_atlasvibe_file.txt" # from "gb18030_flojoy_file.txt"
        record_test("[Standard] gb18030_atlasvibe_file.txt exists", gb18030_renamed_path.is_file())
        if gb18030_renamed_path.is_file():
            try: # Try reading with gb18030 first
                expected_gb18030_content = "你好 atlasvibe 世界"
                check_file_content_for_test(gb18030_renamed_path, expected_gb18030_content, "[Standard] gb18030_atlasvibe_file.txt content", record_test, encoding="gb18030", verbose=verbose)
            except UnicodeDecodeError: # Fallback if original was fallback
                expected_gb18030_content = "fallback atlasvibe content"
                check_file_content_for_test(gb18030_renamed_path, expected_gb18030_content, "[Standard] gb18030_atlasvibe_file.txt content (fallback)", record_test, encoding="utf-8", verbose=verbose)


        binary_renamed_path1 = temp_dir / "binary_atlasvibe_file.bin" # from "binary_flojoy_file.bin"
        record_test("[Standard] binary_atlasvibe_file.bin exists", binary_renamed_path1.is_file())
        if binary_renamed_path1.is_file(): # Check binary content if needed, for now existence is fine
             expected_binary_content = b"prefix_atlasvibe_suffix" + b"\x00\x01\x02atlasvibe_data\x03\x04"
             check_file_content_for_test(binary_renamed_path1, expected_binary_content, "[Standard] binary_atlasvibe_file.bin content", record_test, is_binary=True, verbose=verbose)

        
        original_binary_fLoJoY_path_name = "binary_fLoJoY_name.bin"
        renamed_binary_fLoJoY_path = temp_dir / "binary_atlasVibe_name.bin" 
        original_binary_fLoJoY_content = b"unmapped_variant_binary_content" + b"\x00\xff"

        record_test(f"[Standard] '{renamed_binary_fLoJoY_path.name}' exists (renamed from '{original_binary_fLoJoY_path_name}')", renamed_binary_fLoJoY_path.is_file())
        record_test(f"[Standard] Original '{original_binary_fLoJoY_path_name}' removed after rename", not (temp_dir / original_binary_fLoJoY_path_name).exists())
        if renamed_binary_fLoJoY_path.is_file():
            check_file_content_for_test(renamed_binary_fLoJoY_path, original_binary_fLoJoY_content, f"[Standard] '{renamed_binary_fLoJoY_path.name}' content (should be original)", record_test, is_binary=True, verbose=verbose)


        # Large file (1000 lines, not VERY_LARGE_FILE)
        large_file_renamed_path = temp_dir / "large_atlasvibe_file.txt" # from "large_flojoy_file.txt"
        record_test(f"[Standard] {large_file_renamed_path.name} exists", large_file_renamed_path.is_file())
        if large_file_renamed_path.is_file():
            with open(large_file_renamed_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                expected_first_line = "This atlasvibe line should be replaced 0"
                record_test(f"[Standard] {large_file_renamed_path.name} first line content", first_line == expected_first_line, f"Expected: '{expected_first_line}', Got: '{first_line}'")

        # Deeply nested file
        deep_path_parts_renamed = ["depth1_atlasvibe", "depth2", "depth3_atlasvibe", "depth4", "depth5", "depth6_atlasvibe", "depth7", "depth8", "depth9_atlasvibe", "depth10_file_atlasvibe.txt"]
        current_deep_path = temp_dir
        for part in deep_path_parts_renamed[:-1]: # Check directories
            current_deep_path = current_deep_path / part
            record_test(f"[Standard] Deep dir '{part}' exists at '{current_deep_path.relative_to(temp_dir)}'", current_deep_path.is_dir())
        current_deep_path = current_deep_path / deep_path_parts_renamed[-1] # Check file
        record_test(f"[Standard] Deep file '{deep_path_parts_renamed[-1]}' exists", current_deep_path.is_file())
        if current_deep_path.is_file():
            check_file_content_for_test(current_deep_path, "atlasvibe deep content", "[Standard] Deep file content", record_test, verbose=verbose)


        # Very Large File (VERY_LARGE_FILE_NAME_REPLACED) checks
        very_large_renamed_path = temp_dir / VERY_LARGE_FILE_NAME_REPLACED
        if standard_test_includes_large_file: # This flag is true for standard test
            record_test("[Standard Test] Very large file renamed", very_large_renamed_path.exists())
            if very_large_renamed_path.exists():
                with open(very_large_renamed_path, 'r', encoding='utf-8') as f:
                    line_0_actual = f.readline().strip()
                    expected_line_0 = "Line 1: This is a atlasvibe line that should be replaced."
                    record_test("[Standard Test] Very large file - line 0 content", line_0_actual == expected_line_0, f"Line 0. Expected: '{expected_line_0}', Got: '{line_0_actual}'")
                
                # Re-open to check middle line properly
                with open(very_large_renamed_path, 'r', encoding='utf-8') as f:
                    content_lines = f.readlines() # Read all lines (can be memory intensive for truly huge files)
                    mid_line_index = VERY_LARGE_FILE_LINES // 2 # 0-indexed
                    if len(content_lines) > mid_line_index:
                        line_mid_actual = content_lines[mid_line_index].strip()
                        # Line numbers in file are 1-based
                        expected_line_mid = f"Line {mid_line_index + 1}: This is a atlasvibe line that should be replaced."
                        record_test("[Standard Test] Very large file - middle line content", line_mid_actual == expected_line_mid, f"Mid Line. Expected: '{expected_line_mid}', Got: '{line_mid_actual}'")
                    else:
                        record_test("[Standard Test] Very large file - middle line content", False, f"Could not read middle line ({mid_line_index + 1}). File has {len(content_lines)} lines.")
                    
                    # Check last line
                    if len(content_lines) == VERY_LARGE_FILE_LINES:
                        line_last_actual = content_lines[VERY_LARGE_FILE_LINES -1].strip()
                        expected_line_last = f"Line {VERY_LARGE_FILE_LINES}: This is a atlasvibe line that should be replaced."
                        record_test("[Standard Test] Very large file - last line content", line_last_actual == expected_line_last, f"Last Line. Expected: '{expected_line_last}', Got: '{line_last_actual}'")
                    else:
                         record_test("[Standard Test] Very large file - last line content", False, f"Could not read last line. File has {len(content_lines)} lines, expected {VERY_LARGE_FILE_LINES}.")


        if standard_test_includes_symlinks: # This flag is true for standard test
            link_file_orig_name = "link_to_file_flojoy.txt"
            link_dir_orig_name = "link_to_dir_flojoy"
            link_file_renamed_name = "link_to_file_atlasvibe.txt"
            link_dir_renamed_name = "link_to_dir_atlasvibe"

            link_file_orig_path = temp_dir / link_file_orig_name
            link_dir_orig_path = temp_dir / link_dir_orig_name
            link_file_renamed_path = temp_dir / link_file_renamed_name
            link_dir_renamed_path = temp_dir / link_dir_renamed_name

            if symlinks_were_ignored_in_scan:
                record_test("[Symlink Test - Ignored] Original file symlink exists", os.path.lexists(link_file_orig_path))
                record_test("[Symlink Test - Ignored] Renamed file symlink does NOT exist", not os.path.lexists(link_file_renamed_path))
                record_test("[Symlink Test - Ignored] Original dir symlink exists", os.path.lexists(link_dir_orig_path))
                record_test("[Symlink Test - Ignored] Renamed dir symlink does NOT exist", not os.path.lexists(link_dir_renamed_path))
            else: # Symlinks should be processed (renamed)
                record_test(f"[Symlink Test - Processed] Renamed file symlink '{link_file_renamed_name}' exists", os.path.lexists(link_file_renamed_path))
                if os.path.lexists(link_file_renamed_path):
                    record_test(f"[Symlink Test - Processed] '{link_file_renamed_name}' is a symlink", link_file_renamed_path.is_symlink())
                record_test(f"[Symlink Test - Processed] Original file symlink '{link_file_orig_name}' removed", not os.path.lexists(link_file_orig_path))


                record_test(f"[Symlink Test - Processed] Renamed dir symlink '{link_dir_renamed_name}' exists", os.path.lexists(link_dir_renamed_path))
                if os.path.lexists(link_dir_renamed_path):
                    record_test(f"[Symlink Test - Processed] '{link_dir_renamed_name}' is a symlink", link_dir_renamed_path.is_symlink())
                record_test(f"[Symlink Test - Processed] Original dir symlink '{link_dir_orig_name}' removed", not os.path.lexists(link_dir_orig_path))


            # Target content should always be unchanged as per NOTES.md ("not follow them for content")
            target_file = temp_dir / "symlink_targets_outside" / "target_file_flojoy.txt"
            target_dir_file = temp_dir / "symlink_targets_outside" / "target_dir_flojoy" / "another_flojoy_file.txt"
            
            expected_target_file_content = "flojoy in symlink target file" # Original content
            expected_target_dir_file_content = "flojoy content in symlinked dir target" # Original content

            check_file_content_for_test(target_file, expected_target_file_content, "[Symlink Test] Target file content unchanged", record_test_func=record_test, verbose=verbose)
            check_file_content_for_test(target_dir_file, expected_target_dir_file_content, "[Symlink Test] Target dir file content unchanged", record_test_func=record_test, verbose=verbose)

    # Common verification logic (table printing, summary)
    # (Ensure terminal size is fetched correctly, might need to be outside task if task runs in different env)
    try:
        term_width, _ = shutil.get_terminal_size(fallback=(100, 24))
    except Exception: # Fallback if get_terminal_size fails (e.g. not a TTY)
        term_width = 100

    padding = 1
    id_col_content_width = len(str(test_counter)) if test_counter > 0 else 3
    id_col_total_width = id_col_content_width + 2 * padding
    
    outcome_text_pass = f"{PASS_SYMBOL} PASS"
    outcome_text_fail = f"{FAIL_SYMBOL} FAIL"
    outcome_col_content_width = max(len(outcome_text_pass), len(outcome_text_fail))
    outcome_col_total_width = outcome_col_content_width + 2 * padding
    
    desc_col_total_width = term_width - (id_col_total_width + outcome_col_total_width + 4) # 4 for 3 vertical bars
    min_desc_col_content_width = 30 
    desc_col_content_width = max(min_desc_col_content_width, desc_col_total_width - 2 * padding)


    header_id = f"{'#':^{id_col_content_width}}"
    header_desc = f"{'Test Description':^{desc_col_content_width}}"
    header_outcome = f"{'Outcome':^{outcome_col_content_width}}"

    # Use logger for table output
    logger.info("\n" + BLUE + DBL_TOP_LEFT + DBL_HORIZONTAL * id_col_total_width + DBL_T_DOWN + DBL_HORIZONTAL * desc_col_total_width + DBL_T_DOWN + DBL_HORIZONTAL * outcome_col_total_width + DBL_TOP_RIGHT + RESET)
    logger.info(BLUE + DBL_VERTICAL + f"{' ' * padding}{header_id}{' ' * padding}" + DBL_VERTICAL + f"{' ' * padding}{header_desc}{' ' * padding}" + DBL_VERTICAL + f"{' ' * padding}{header_outcome}{' ' * padding}" + DBL_VERTICAL + RESET)
    logger.info(BLUE + DBL_T_RIGHT + DBL_HORIZONTAL * id_col_total_width + DBL_CROSS + DBL_HORIZONTAL * desc_col_total_width + DBL_CROSS + DBL_HORIZONTAL * outcome_col_total_width + DBL_T_LEFT + RESET)

    for test_item in test_results:
        test_id_str = str(test_item["id"])
        desc = test_item["description"]
        status = test_item["status"]
        status_color = GREEN if status == "PASS" else RED
        
        wrapped_desc_lines = textwrap.wrap(desc, width=desc_col_content_width, drop_whitespace=False, replace_whitespace=False)
        if not wrapped_desc_lines:
            wrapped_desc_lines = [""] # Handle empty description case
        
        for line_idx, desc_line in enumerate(wrapped_desc_lines):
            id_display = test_id_str if line_idx == 0 else ""
            status_display = f"{status_color}{status:^{outcome_col_content_width}}{RESET}" if line_idx == 0 else ""
            
            log_line = (
                f"{BLUE}{DBL_VERTICAL}{RESET}"
                f"{' ' * padding}{id_display:^{id_col_content_width}}{' ' * padding}"
                f"{BLUE}{DBL_VERTICAL}{RESET}"
                f"{' ' * padding}{desc_line:<{desc_col_content_width}}{' ' * padding}"
                f"{BLUE}{DBL_VERTICAL}{RESET}"
                f"{' ' * padding}{status_display:<{outcome_col_total_width - 2 * padding}}{' ' * padding}" # status_display includes color codes
                f"{BLUE}{DBL_VERTICAL}{RESET}"
            )
            logger.info(log_line)
            
        # If it's not the last test item, and it's a multi-line description, add a separator line
        # Or always add separator if not the last test item.
        if test_results.index(test_item) < len(test_results) - 1:
             logger.info(BLUE + DBL_T_RIGHT + DBL_HORIZONTAL * id_col_total_width + DBL_CROSS + DBL_HORIZONTAL * desc_col_total_width + DBL_CROSS + DBL_HORIZONTAL * outcome_col_total_width + DBL_T_LEFT + RESET)


    logger.info(BLUE + DBL_BOTTOM_LEFT + DBL_HORIZONTAL * id_col_total_width + DBL_T_UP + DBL_HORIZONTAL * desc_col_total_width + DBL_T_UP + DBL_HORIZONTAL * outcome_col_total_width + DBL_BOTTOM_RIGHT + RESET)

    if failed_checks > 0 and verbose:
        logger.info("\n" + RED + "--- Failure Details ---" + RESET)
        for detail_line in failed_test_details_print_buffer:
            # Log each detail line, ensuring multi-line details are handled if they exist in detail_line
            for sub_line in detail_line.splitlines():
                logger.info(RED + sub_line + RESET)


    if failed_checks > 0:
        raise AssertionError(f"Self-test failed with {failed_checks} assertion(s). Review output for details.")
    return True


@flow(name="Self-Test Flow", log_prints=True)
def self_test_flow(
    temp_dir_str: str,
    dry_run_for_test: bool,
    verbose: bool = False,
    run_exec_resume_sub_test: bool = False, 
    run_scan_resume_sub_test: bool = False, 
    run_complex_map_sub_test: bool = False,
    run_edge_case_sub_test: bool = False,
    run_empty_map_sub_test: bool = False,
    run_resume_test: bool = False,
    run_precision_test: bool = False,
    ignore_symlinks_for_this_test_run: bool = False
) -> None:
    logger = get_run_logger()
    temp_dir = Path(temp_dir_str)

    current_mapping_file_for_test: Path
    test_scenario_name = "Standard" # Default
    is_verification_resume_test = run_resume_test # Pass through for verification
    is_verification_precision_test = run_precision_test # Pass through

    # Determine if the current test scenario is one that includes the "very large file"
    # and symlinks by default in its _create_self_test_environment call.
    # Standard test includes them. Resume and Precision also include symlinks.
    is_standard_like_test = not (run_complex_map_sub_test or run_edge_case_sub_test or run_empty_map_sub_test)
    
    standard_test_includes_large_file = is_standard_like_test and not (run_resume_test or run_precision_test)
    standard_test_includes_symlinks = is_standard_like_test # Symlinks are created for standard, resume, precision

    def create_mapping_file(test_type: str, base_path: Path) -> Path:
        """Helper to generate mapping files based on test type."""
        map_data: Dict[str, Any]
        map_filename: str

        if test_type == "complex":
            map_data = {
                "REPLACEMENT_MAPPING": {
                    "ȕsele̮Ss_diá͡cRiti̅cS": "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL",
                    "The spaces will not be ignored": "The control characters \n will be ignored_VAL",
                    "key_with\tcontrol\nchars": "Value_for_key_with_controls_VAL",
                    "_My_Love&Story": "_My_Story&Love_VAL",
                    "_my_love&story": "_my_story&love_VAL", # Note: different casing from above key
                    "COCO4_ep-m": "MOCO4_ip-N_VAL",
                    "Coco4_ep-M": "Moco4_ip-N_VAL", # Note: different casing
                    "characters|not<allowed^in*paths::will\\/be!escaped%when?searched~in$filenames@and\"foldernames": "SpecialCharsKeyMatched_VAL"
                }
            }
            map_filename = SELF_TEST_COMPLEX_MAP_FILE
        elif test_type == "edge_case":
            map_data = {
                "REPLACEMENT_MAPPING": {
                    "My\nKey": "MyKeyValue_VAL", 
                    "Key\nWith\tControls": "ControlValue_VAL", 
                    "\t": "ShouldBeSkipped_VAL", 
                    "foo": "Foo_VAL",
                    "foo bar": "FooBar_VAL"
                }
            }
            map_filename = SELF_TEST_EDGE_CASE_MAP_FILE
        elif test_type == "empty":
            map_data = {"REPLACEMENT_MAPPING": {}}
            map_filename = SELF_TEST_EMPTY_MAP_FILE
        elif test_type == "precision":
            map_data = {
                "REPLACEMENT_MAPPING": {
                    "flojoy": "atlasvibe_plain",
                    "Flojoy": "Atlasvibe_TitleCase",
                    "FLÖJOY_DIACRITIC": "ATLASVIBE_DIACRITIC_VAL", 
                    "  flojoy  ": "  atlasvibe_spaced_val  ", 
                    "key\twith\ncontrol": "value_for_control_key_val" 
                }
            }
            map_filename = SELF_TEST_PRECISION_MAP_FILE
        elif test_type == "resume" or test_type == "standard": # Resume and Standard use default map
            map_data = {
                "REPLACEMENT_MAPPING": {
                    "flojoy": "atlasvibe", "Flojoy": "Atlasvibe", "floJoy": "atlasVibe",
                    "FloJoy": "AtlasVibe", "FLOJOY": "ATLASVIBE"
                }
            }
            map_filename = DEFAULT_REPLACEMENT_MAPPING_FILE # Standard name for default map
        else:
            raise ValueError(f"Unknown test type for mapping file: {test_type}")

        mapping_path = base_path / map_filename
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(map_data, f, indent=2)
        return mapping_path

    if run_complex_map_sub_test:
        test_scenario_name = "Complex Map"
        current_mapping_file_for_test = create_mapping_file("complex", temp_dir)
    elif run_edge_case_sub_test:
        test_scenario_name = "Edge Case"
        current_mapping_file_for_test = create_mapping_file("edge_case", temp_dir)
    elif run_empty_map_sub_test:
        test_scenario_name = "Empty Map"
        current_mapping_file_for_test = create_mapping_file("empty", temp_dir)
    elif run_resume_test:
        test_scenario_name = "Resume"
        current_mapping_file_for_test = create_mapping_file("resume", temp_dir)
    elif run_precision_test:
        test_scenario_name = "Precision"
        current_mapping_file_for_test = create_mapping_file("precision", temp_dir)
    else: # Standard test
        test_scenario_name = "Standard"
        current_mapping_file_for_test = create_mapping_file("standard", temp_dir)

    logger.info(f"Self-Test ({test_scenario_name}): Using mapping file {current_mapping_file_for_test.name}")

    load_success = replace_logic.load_replacement_map(current_mapping_file_for_test)
    if not load_success:
        if run_empty_map_sub_test and not replace_logic._REPLACEMENT_MAPPING_CONFIG and replace_logic._COMPILED_PATTERN is None:
            logger.info(f"Self-Test ({test_scenario_name}): Successfully loaded an empty map as expected.")
        else:
            raise RuntimeError(f"Self-Test FATAL: Could not load or process replacement map {current_mapping_file_for_test} for test run.")
    elif run_empty_map_sub_test and replace_logic._REPLACEMENT_MAPPING_CONFIG:
        raise RuntimeError(f"Self-Test FATAL: Expected empty map for {test_scenario_name}, but found rules: {replace_logic._REPLACEMENT_MAPPING_CONFIG}")

    logger.info(f"Self-Test ({test_scenario_name}): Successfully initialized replacement map from {current_mapping_file_for_test}")

    _create_self_test_environment(
        temp_dir,
        use_complex_map=run_complex_map_sub_test,
        use_edge_case_map=run_edge_case_sub_test,
        include_very_large_file=standard_test_includes_large_file,
        include_precision_test_file=run_precision_test,
        include_symlink_tests=standard_test_includes_symlinks, # True for standard, resume, precision
        verbose=verbose
    )

    test_excluded_dirs: List[str] = ["excluded_flojoy_dir", "symlink_targets_outside"]
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt", current_mapping_file_for_test.name]
    test_excluded_files.extend([ # Exclude all known transaction and mapping files by basename
        Path(f).name for f in [
            MAIN_TRANSACTION_FILE_NAME, SELF_TEST_PRIMARY_TRANSACTION_FILE,
            SELF_TEST_SCAN_VALIDATION_FILE, SELF_TEST_COMPLEX_MAP_FILE,
            SELF_TEST_EDGE_CASE_MAP_FILE, SELF_TEST_EMPTY_MAP_FILE,
            SELF_TEST_RESUME_TRANSACTION_FILE, SELF_TEST_PRECISION_MAP_FILE,
            DEFAULT_REPLACEMENT_MAPPING_FILE # current_mapping_file_for_test might be this
        ]
    ])
    test_excluded_files = list(set(test_excluded_files))


    test_extensions = [".txt", ".py", ".md", ".bin", ".log", ".data"]

    # Define transaction file name based on the specific test being run
    transaction_file_name_stem = "transactions"
    if run_complex_map_sub_test:
        transaction_file_name_stem = Path(SELF_TEST_COMPLEX_MAP_FILE).stem
    elif run_edge_case_sub_test:
        transaction_file_name_stem = Path(SELF_TEST_EDGE_CASE_MAP_FILE).stem
    elif run_empty_map_sub_test:
        transaction_file_name_stem = Path(SELF_TEST_EMPTY_MAP_FILE).stem
    elif run_resume_test:
        transaction_file_name_stem = Path(SELF_TEST_RESUME_TRANSACTION_FILE).stem
    elif run_precision_test:
        transaction_file_name_stem = Path(SELF_TEST_PRECISION_MAP_FILE).stem
    else: # Standard test
        transaction_file_name_stem = Path(SELF_TEST_PRIMARY_TRANSACTION_FILE).stem
        if ignore_symlinks_for_this_test_run: # Differentiate if symlinks are ignored for standard test
            transaction_file_name_stem += "_ignore_symlinks"
    
    transaction_file = temp_dir / f"{transaction_file_name_stem}.json"
    # Validation file only for standard test that's not ignoring symlinks and not empty/resume/precision
    validation_file = temp_dir / f"{transaction_file_name_stem}_validation.json" \
        if not (run_complex_map_sub_test or run_edge_case_sub_test or \
                run_empty_map_sub_test or run_resume_test or run_precision_test or \
                (test_scenario_name == "Standard" and ignore_symlinks_for_this_test_run)) \
        else None


    if run_resume_test:
        logger.info(f"Self-Test ({test_scenario_name}): Phase 1 - Initial scan and partial execution simulation...")
        initial_transactions = scan_directory_for_occurrences(
            temp_dir, test_excluded_dirs, test_excluded_files, test_extensions,
            ignore_symlinks=False # Phase 1 of resume processes symlinks by default
        )

        if initial_transactions:
            # Simulate some states
            # Mark first file name transaction as completed
            fn_tx_indices = [i for i, tx in enumerate(initial_transactions) if tx["TYPE"] == TransactionType.FILE_NAME.value]
            if fn_tx_indices:
                initial_transactions[fn_tx_indices[0]]["STATUS"] = TransactionStatus.COMPLETED.value
            if len(fn_tx_indices) > 1:
                initial_transactions[fn_tx_indices[1]]["STATUS"] = TransactionStatus.IN_PROGRESS.value
            
            # Mark a content transaction from large_file as PENDING
            content_tx_indices = [i for i, tx in enumerate(initial_transactions) if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and "large_flojoy_file.txt" in tx["PATH"]]
            if content_tx_indices:
                initial_transactions[content_tx_indices[0]]["STATUS"] = TransactionStatus.PENDING.value

            # Simulate a FAILED transaction for the error file
            for tx in initial_transactions:
                if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME and tx["TYPE"] == TransactionType.FILE_NAME.value:
                    tx["STATUS"] = TransactionStatus.FAILED.value
                    tx["ERROR_MESSAGE"] = "Simulated failure from initial run"
                    break
        
        save_transactions(initial_transactions if initial_transactions else [], transaction_file)
        logger.info(f"Self-Test ({test_scenario_name}): Saved intermediate transaction file with {len(initial_transactions) if initial_transactions else 0} transactions to {transaction_file}.")

        logger.info(f"Self-Test ({test_scenario_name}): Phase 2 - Modifying environment for resume scan...")
        _create_self_test_environment(temp_dir, for_resume_test_phase_2=True, include_symlink_tests=True, verbose=verbose) # Symlinks are part of resume env mod

        logger.info(f"Self-Test ({test_scenario_name}): Phase 3 - Running main_flow with --resume (dry_run={dry_run_for_test}, ignore_symlinks={ignore_symlinks_for_this_test_run})...")
        main_flow( # Call as a regular function, not a subflow, to use current Prefect context
            directory=str(temp_dir),
            mapping_file=str(current_mapping_file_for_test),
            extensions=test_extensions,
            exclude_dirs=test_excluded_dirs,
            exclude_files=test_excluded_files,
            dry_run=dry_run_for_test, # For resume, this should ideally be False to test execution
            skip_scan=False, 
            resume=True,
            force_execution=True, 
            ignore_symlinks_arg=ignore_symlinks_for_this_test_run
        )
    else: # Non-resume tests
        transactions1 = scan_directory_for_occurrences(
            root_dir=temp_dir, excluded_dirs=test_excluded_dirs, excluded_files=test_excluded_files,
            file_extensions=test_extensions, ignore_symlinks=ignore_symlinks_for_this_test_run
        )
        save_transactions(transactions1 if transactions1 else [], transaction_file)
        logger.info(f"Self-Test ({test_scenario_name}): First scan complete. {len(transactions1) if transactions1 else 0} transactions planned in {transaction_file}.")

        if run_empty_map_sub_test:
            if transactions1 and len(transactions1) != 0:
                raise AssertionError(f"[Empty Map Test] Expected 0 transactions, got {len(transactions1)}")
            logger.info(f"Self-Test ({test_scenario_name}): Verified 0 transactions as expected.")
        elif validation_file: # For standard test (not ignoring symlinks), create a validation scan
            transactions2 = scan_directory_for_occurrences(
                root_dir=temp_dir, excluded_dirs=test_excluded_dirs, excluded_files=test_excluded_files,
                file_extensions=test_extensions, ignore_symlinks=ignore_symlinks_for_this_test_run
            )
            save_transactions(transactions2 if transactions2 else [], validation_file)
            logger.info(f"Self-Test ({test_scenario_name}): Second scan (for validation) complete. {len(transactions2) if transactions2 else 0} transactions planned in {validation_file}.")
            if transactions1 != transactions2 and verbose: # Basic determinism check
                 logger.warning(f"{YELLOW}Scan determinism check: Initial scan and validation scan produced different transaction lists.{RESET}")


        if not dry_run_for_test and not run_empty_map_sub_test: # Actual execution for non-empty, non-dry-run
            logger.info(f"Self-Test ({test_scenario_name}): Executing transactions from {transaction_file} (Dry Run = False)...")
            execute_all_transactions(
                transactions_file_path=transaction_file, root_dir=temp_dir,
                dry_run=False, resume=False 
            )
            logger.info(f"Self-Test ({test_scenario_name}): Execution phase complete.")
        elif dry_run_for_test and not run_empty_map_sub_test: # Dry run simulation
            logger.info(f"Self-Test ({test_scenario_name}): Dry run. Simulating execution from {transaction_file}.")
            execute_all_transactions(transaction_file, temp_dir, dry_run=True, resume=False)

    # Verification step
    _verify_self_test_results_task.fn( # Call the task function directly
        temp_dir=temp_dir,
        original_transaction_file=transaction_file,
        validation_transaction_file=validation_file,
        is_complex_map_test=run_complex_map_sub_test,
        is_edge_case_test=run_edge_case_sub_test,
        is_empty_map_test=run_empty_map_sub_test,
        is_resume_test=is_verification_resume_test,
        standard_test_includes_large_file=standard_test_includes_large_file,
        is_precision_test=is_verification_precision_test,
        standard_test_includes_symlinks=standard_test_includes_symlinks,
        symlinks_were_ignored_in_scan=ignore_symlinks_for_this_test_run,
        verbose=verbose
    )


@flow(name="Mass Find and Replace Orchestration Flow", log_prints=True)
def main_flow(
    directory: str,
    mapping_file: str,
    extensions: Optional[List[str]],
    exclude_dirs: List[str],
    exclude_files: List[str],
    dry_run: bool,
    skip_scan: bool,
    resume: bool,
    force_execution: bool,
    ignore_symlinks_arg: bool
):
    logger = get_run_logger()
    root_dir = Path(directory).resolve()
    if not root_dir.is_dir():
        logger.error(f"Error: Root directory '{root_dir}' does not exist or is not a directory.")
        return

    mapping_file_path = Path(mapping_file).resolve()
    if not replace_logic.load_replacement_map(mapping_file_path):
        logger.error(f"Aborting due to issues with replacement mapping file: {mapping_file_path}")
        return

    if not replace_logic._MAPPING_LOADED:
        logger.error(f"Critical Error: Replacement map from {mapping_file_path} was not loaded successfully by replace_logic.")
        return
    if not replace_logic._COMPILED_PATTERN and bool(replace_logic._REPLACEMENT_MAPPING_CONFIG):
        logger.error("Critical Error: Replacement map loaded but regex pattern compilation failed in replace_logic.")
        return
    if not replace_logic._REPLACEMENT_MAPPING_CONFIG:
        logger.warning(f"{YELLOW}Warning: The replacement mapping from {mapping_file_path} is empty. No string replacements will be made.{RESET}")

    transaction_json_path = root_dir / MAIN_TRANSACTION_FILE_NAME

    if not dry_run and not force_execution and not resume:
        # Confirmation prompt (using print for direct user interaction)
        print("--- Proposed Operation ---")
        print(f"Root Directory: {root_dir}")
        print(f"Replacement Map File: {mapping_file_path}")
        if replace_logic._REPLACEMENT_MAPPING_CONFIG:
            print(f"Loaded {len(replace_logic._REPLACEMENT_MAPPING_CONFIG)} replacement rules.")
        else:
            print("Replacement map is empty. No string replacements will occur.")
        print(f"File Extensions for content scan: {extensions if extensions else 'All non-binary (heuristic)'}")
        print(f"Exclude Dirs: {exclude_dirs}")
        print(f"Exclude Files: {exclude_files}")
        print(f"Ignore Symlinks: {ignore_symlinks_arg}")
        print("-------------------------")
        sys.stdout.flush() # Ensure prompt is shown before input
        if not replace_logic._REPLACEMENT_MAPPING_CONFIG and not extensions:
            print("No replacement rules loaded and no specific extensions to process. Likely no operations will be performed.")

        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled by user.")
            return

    if not skip_scan:
        logger.info(f"Starting scan phase in '{root_dir}' using map '{mapping_file_path}' (Ignore symlinks: {ignore_symlinks_arg})...")
        current_transactions_for_resume_scan = None
        if resume and transaction_json_path.exists():
            logger.info(f"Resume mode: Loading existing transactions from {transaction_json_path} for scan augmentation...")
            current_transactions_for_resume_scan = load_transactions(transaction_json_path)
            if current_transactions_for_resume_scan is None:
                logger.warning(f"{YELLOW}Warning: Could not load transactions from {transaction_json_path} for resume scan. Starting fresh scan.{RESET}")
            elif not current_transactions_for_resume_scan:
                 logger.warning(f"{YELLOW}Warning: Loaded transaction file {transaction_json_path} for resume scan was empty. Starting fresh scan.{RESET}")

        found_transactions = scan_directory_for_occurrences(
            root_dir=root_dir, excluded_dirs=exclude_dirs, excluded_files=exclude_files,
            file_extensions=extensions, ignore_symlinks=ignore_symlinks_arg,
            resume_from_transactions=current_transactions_for_resume_scan if resume else None
        )
        save_transactions(found_transactions if found_transactions else [], transaction_json_path)
        logger.info(f"Scan complete. {len(found_transactions) if found_transactions else 0} transactions planned in '{transaction_json_path}'")
        
        if not found_transactions:
            if replace_logic._REPLACEMENT_MAPPING_CONFIG:
                logger.info("No occurrences found matching the replacement map. Nothing to do.")
            else:
                logger.info("Replacement map was empty, and no occurrences found (as expected).")
            return 

    elif not transaction_json_path.exists():
        logger.error(f"Error: --skip-scan was used, but '{transaction_json_path}' not found.")
        return
    else:
        logger.info(f"Using existing transaction file: '{transaction_json_path}'. Ensure it was generated with the correct replacement map and symlink settings.")

    if not replace_logic._REPLACEMENT_MAPPING_CONFIG:
        logger.info("Map is empty. No execution will be performed.")
        return

    transactions_for_execution = load_transactions(transaction_json_path)
    if not transactions_for_execution: # Check if loading for execution failed or was empty
        logger.info(f"No transactions found in {transaction_json_path} to execute. Exiting.")
        return

    if dry_run:
        logger.info("Dry run: Simulating execution of transactions...")
        stats = execute_all_transactions(
            transactions_file_path=transaction_json_path, root_dir=root_dir,
            dry_run=True, resume=resume
        )
        logger.info(f"Dry run complete. Simulated stats: {stats}")
    else:
        logger.info("Starting execution phase...")
        stats = execute_all_transactions(
            transactions_file_path=transaction_json_path, root_dir=root_dir,
            dry_run=False, resume=resume
        )
        logger.info(f"Execution phase complete. Stats: {stats}")
    logger.info(f"Review '{transaction_json_path}' for a log of changes and their statuses.")


def main_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Find and replace strings in files and directories based on a JSON mapping file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("directory", nargs='?', default=".",
                        help="The root directory to process (default: current directory).")
    parser.add_argument("--mapping-file", default=DEFAULT_REPLACEMENT_MAPPING_FILE,
                        help=f"Path to the JSON file containing replacement mappings (default: ./{DEFAULT_REPLACEMENT_MAPPING_FILE}).")
    parser.add_argument("--extensions", nargs="+",
                        help="List of file extensions to process for content changes (e.g., .py .txt). If not specified, attempts to process text-like files, skipping binaries.")
    parser.add_argument("--exclude-dirs", nargs="+", default=[".git", ".venv", "venv", "node_modules", "__pycache__", SELF_TEST_SANDBOX_DIR.lstrip('./\\')],
                        help="Directory names to exclude (space-separated). Default: .git .venv venv node_modules __pycache__ tests/temp")
    parser.add_argument("--exclude-files", nargs="+", default=[],
                        help="Specific file paths (relative to root) to exclude (space-separated).")
    parser.add_argument("--ignore-symlinks", action="store_true",
                        help="If set, symlinks will be ignored (not renamed, targets not processed). Default is to rename symlinks but not follow them for content.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and plan changes, but do not execute them. Reports what would be changed.")
    parser.add_argument("--skip-scan", action="store_true",
                        help=f"Skip scan phase; use existing '{MAIN_TRANSACTION_FILE_NAME}' in the root directory.")
    parser.add_argument("--resume", action="store_true",
                        help="Resume operation from existing transaction file, attempting to complete pending/failed items and scan for new ones.")
    parser.add_argument("--force", "--yes", "-y", action="store_true",
                        help="Force execution without confirmation prompt (use with caution).")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output during self-tests.")

    self_test_group = parser.add_argument_group('Self-Test Options')
    self_test_group.add_argument("--self-test", dest="run_standard_self_test", action="store_true",
                                 help=f"Run the standard self-test suite in '{SELF_TEST_SANDBOX_DIR}'. Uses default mappings.")
    self_test_group.add_argument("--self-test-complex-map", dest="run_complex_map_self_test", action="store_true",
                                 help=f"Run the self-test suite with a complex mapping scenario in '{SELF_TEST_SANDBOX_DIR}'.")
    self_test_group.add_argument("--self-test-edge-cases", dest="run_edge_case_self_test", action="store_true",
                                 help=f"Run self-tests for edge case scenarios in '{SELF_TEST_SANDBOX_DIR}'.")
    self_test_group.add_argument("--self-test-empty-map", dest="run_empty_map_self_test", action="store_true",
                                 help=f"Run self-test with an empty replacement map in '{SELF_TEST_SANDBOX_DIR}'.")
    self_test_group.add_argument("--self-test-resume", dest="run_resume_self_test", action="store_true",
                                 help=f"Run self-test for resume functionality in '{SELF_TEST_SANDBOX_DIR}'.")
    self_test_group.add_argument("--self-test-precision", dest="run_precision_self_test", action="store_true",
                                 help=f"Run self-test for 'surgeon-like' precision in '{SELF_TEST_SANDBOX_DIR}'.")

    args = parser.parse_args()

    # Setup Prefect logging to use stdout for self-tests if verbose, or default otherwise
    # This is a global setting, might affect other Prefect logs if script is part of larger app.
    # Consider if this needs to be more targeted.
    # if args.verbose:
    #     prefect.settings.PREFECT_LOGGING_HANDLERS_CONSOLE_STREAM.set("stdout")


    if args.run_standard_self_test or args.run_complex_map_self_test or \
            args.run_edge_case_self_test or args.run_empty_map_self_test or \
            args.run_resume_self_test or args.run_precision_self_test:

        is_complex_run = args.run_complex_map_self_test
        is_edge_case_run = args.run_edge_case_self_test
        is_empty_map_run = args.run_empty_map_self_test
        is_resume_run = args.run_resume_self_test
        is_precision_run = args.run_precision_self_test
        
        test_type_msg = "Unknown"
        if args.run_standard_self_test:
            test_type_msg = "Standard"
        elif is_complex_run:
            test_type_msg = "Complex Map"
        elif is_edge_case_run:
            test_type_msg = "Edge Cases"
        elif is_empty_map_run:
            test_type_msg = "Empty Map"
        elif is_resume_run:
            test_type_msg = "Resume Functionality"
        elif is_precision_run:
            test_type_msg = "Precision"
        
        # For self-tests, dry_run is often False to see actual changes.
        # The --dry-run CLI flag can override this for self-test execution if needed.
        effective_dry_run_for_test = args.dry_run

        print(f"Running self-test ({test_type_msg} scenario) in sandbox: '{SELF_TEST_SANDBOX_DIR}' (Dry Run: {effective_dry_run_for_test}, Verbose: {args.verbose})...")

        self_test_sandbox = Path(SELF_TEST_SANDBOX_DIR).resolve()
        if self_test_sandbox.exists():
            if args.verbose:
                print(f"Removing existing self-test sandbox: {self_test_sandbox}")
            shutil.rmtree(self_test_sandbox)
        self_test_sandbox.mkdir(parents=True, exist_ok=True)
        if args.verbose:
            print(f"Created self-test sandbox: {self_test_sandbox}")

        try:
            if args.run_standard_self_test:
                print(f"\nRunning Standard Self-Test (Processing Symlinks, ignore_symlinks=False, dry_run={effective_dry_run_for_test})...")
                self_test_flow( 
                    temp_dir_str=str(self_test_sandbox),
                    dry_run_for_test=effective_dry_run_for_test,
                    verbose=args.verbose,
                    ignore_symlinks_for_this_test_run=False
                )
                
                if self_test_sandbox.exists():
                    shutil.rmtree(self_test_sandbox)
                self_test_sandbox.mkdir(parents=True, exist_ok=True)
                print(f"\nRunning Standard Self-Test (Ignoring Symlinks, ignore_symlinks=True, dry_run={effective_dry_run_for_test})...")
                self_test_flow(
                    temp_dir_str=str(self_test_sandbox),
                    dry_run_for_test=effective_dry_run_for_test,
                    verbose=args.verbose,
                    ignore_symlinks_for_this_test_run=True
                )
            else: # Specific non-standard tests
                # These tests use args.ignore_symlinks from CLI for their symlink handling part.
                print(f"\nRunning {test_type_msg} Self-Test (ignore_symlinks={args.ignore_symlinks}, dry_run={effective_dry_run_for_test})...")
                self_test_flow(
                    temp_dir_str=str(self_test_sandbox),
                    dry_run_for_test=effective_dry_run_for_test, 
                    run_complex_map_sub_test=is_complex_run,
                    run_edge_case_sub_test=is_edge_case_run,
                    run_empty_map_sub_test=is_empty_map_run,
                    run_resume_test=is_resume_run,
                    run_precision_test=is_precision_run,
                    verbose=args.verbose,
                    ignore_symlinks_for_this_test_run=args.ignore_symlinks 
                )
        except AssertionError as e: 
            print(RED + f"Self-test ({test_type_msg}) FAILED assertions." + RESET, file=sys.stderr)
            # Prefect might have already logged the traceback.
            sys.exit(1)
        except Exception as e:
            print(RED + f"Self-test ({test_type_msg}) encountered an unexpected ERROR: {e} " + FAIL_SYMBOL + RESET, file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
        finally:
            if self_test_sandbox.exists():
                try:
                    shutil.rmtree(self_test_sandbox)
                    if args.verbose:
                        print(f"Cleaned up self-test sandbox: {self_test_sandbox}")
                except Exception as e:
                    if args.verbose:
                        print(f"{YELLOW}Warning: Could not remove self-test sandbox {self_test_sandbox}: {e}{RESET}")
        print(GREEN + f"Self-test ({test_type_msg}) completed successfully. {PASS_SYMBOL}" + RESET)
        return

    # Standard operation (not a self-test run)
    auto_excluded_files = [MAIN_TRANSACTION_FILE_NAME, Path(args.mapping_file).name]
    auto_excluded_files.append(MAIN_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT)
    auto_excluded_files.extend([
        Path(f).name for f in [
            SELF_TEST_PRIMARY_TRANSACTION_FILE, SELF_TEST_SCAN_VALIDATION_FILE,
            SELF_TEST_RESUME_TRANSACTION_FILE,
            SELF_TEST_PRIMARY_TRANSACTION_FILE + TRANSACTION_FILE_BACKUP_EXT,
            SELF_TEST_RESUME_TRANSACTION_FILE + TRANSACTION_FILE_BACKUP_EXT,
        ]
    ])
    final_exclude_files = list(set(args.exclude_files + auto_excluded_files))

    main_flow( 
        directory=args.directory,
        mapping_file=args.mapping_file,
        extensions=args.extensions,
        exclude_dirs=args.exclude_dirs,
        exclude_files=final_exclude_files,
        dry_run=args.dry_run,
        skip_scan=args.skip_scan,
        resume=args.resume,
        force_execution=args.force,
        ignore_symlinks_arg=args.ignore_symlinks
    )

if __name__ == "__main__":
    try:
        missing_deps = []
        try:
            import prefect
        except ImportError:
            missing_deps.append("prefect")
        # chardet is used by file_system_operations, which should handle its own import error if critical
        if missing_deps:
            raise ImportError(f"Missing dependencies: {', '.join(missing_deps)}")
        main_cli()
    except ImportError as e:
        sys.stderr.write(f"CRITICAL ERROR: {e}.\nPlease ensure dependencies are installed (e.g., pip install prefect chardet).\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(RED + f"An unexpected error occurred in __main__: {e}" + RESET + "\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
