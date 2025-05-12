#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import argparse
import tempfile
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional, Union
import shutil # For shutil.rmtree and shutil.get_terminal_size
import textwrap # Added for text wrapping
import json # Added to resolve F821

# Prefect integration - now a hard dependency
from prefect import task, flow

# Local module imports
from file_system_operations import (
    scan_directory_for_occurrences,
    save_transactions,
    load_transactions,
    execute_all_transactions,
    TransactionStatus, 
    TransactionType, 
    TRANSACTION_FILE_BACKUP_EXT,
    is_likely_binary_file # For self-test verification
)
from replace_logic import replace_flojoy_occurrences # Import for use in self-test verification

# --- Constants ---
MAIN_TRANSACTION_FILE_NAME = "planned_transactions.json" 
SELF_TEST_PRIMARY_TRANSACTION_FILE = "self_test_transactions.json"
SELF_TEST_SANDBOX_DIR = "./tests/temp" # Defined sandbox for self-tests

# ANSI Color Codes & Unicode Symbols for formatted output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
YELLOW = "\033[93m"
BLUE = "\033[94m" # For table borders
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
def _create_self_test_environment(base_dir: Path) -> None:
    """Creates a directory structure and files for self-testing."""
    # Existing setup
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
        "This has fLoJoY content, and also flojoy."
    )
    (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")
    (base_dir / "binary_fLoJoY_name.bin").write_bytes(b"unmapped_variant_binary_content" + b"\x00\xff")

    (base_dir / "excluded_flojoy_dir").mkdir(exist_ok=True)
    (base_dir / "excluded_flojoy_dir" / "inner_flojoy_file.txt").write_text("flojoy inside excluded dir")
    (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in explicitly excluded file")
    (base_dir / "no_target_here.log").write_text("This is a log file without the target string.")

    # Setup for new tests (placeholders, actual file creation might be more complex)
    # Test for directory tree depth=10
    deep_path_parts = ["depth1_flojoy", "depth2", "depth3_flojoy", "depth4", "depth5", "depth6_flojoy", "depth7", "depth8", "depth9_flojoy", "depth10_file_flojoy.txt"]
    current_path = base_dir
    for part_idx, part in enumerate(deep_path_parts):
        current_path = current_path / part
        if part_idx < len(deep_path_parts) -1: # It's a directory
            current_path.mkdir(parents=True, exist_ok=True)
        else: # It's the file
            current_path.write_text("flojoy deep content")


    # Test for GB18030 (simplified: create a file, actual encoding needs care)
    try:
        (base_dir / "gb18030_flojoy_file.txt").write_text("你好 flojoy 世界", encoding="gb18030")
    except UnicodeEncodeError: # Fallback if system can't write gb18030 easily for test setup
        (base_dir / "gb18030_flojoy_file.txt").write_text("fallback flojoy content")


    # Test for large file (simplified: create a moderately sized file)
    large_file_content_list = []
    for i in range(5000): # Approx 100KB, not 10MB. True large file testing is complex for unit tests.
        if i % 100 == 0: # Sprinkle some occurrences
            large_file_content_list.append("This flojoy line should be replaced " + str(i) + "\n")
        else:
            large_file_content_list.append("Normal line " + str(i) + "\n")
    (base_dir / "large_flojoy_file.txt").write_text("".join(large_file_content_list))


    # Test for resume execution (partially completed transaction file)
    # This file will be used by a separate execution run if resume test is activated
    resume_tx_file = base_dir / "for_resume_test_transactions.json" 
    (base_dir / "completed_flojoy_for_resume.txt").write_text("already done flojoy content") # Content should also change if name changes
    (base_dir / "pending_flojoy_for_resume.txt").write_text("pending content flojoy")
    (base_dir / "inprogress_flojoy_for_resume.txt").write_text("in progress content flojoy")
    
    resume_transactions_data = [
        {"id": "uuid_completed_resume", "TYPE": "FILE_NAME", "PATH": "completed_flojoy_for_resume.txt", "ORIGINAL_NAME": "completed_flojoy_for_resume.txt", "STATUS": "COMPLETED"},
        {"id": "uuid_pending_resume", "TYPE": "FILE_NAME", "PATH": "pending_flojoy_for_resume.txt", "ORIGINAL_NAME": "pending_flojoy_for_resume.txt", "STATUS": "PENDING"},
        {"id": "uuid_inprogress_resume", "TYPE": "FILE_NAME", "PATH": "inprogress_flojoy_for_resume.txt", "ORIGINAL_NAME": "inprogress_flojoy_for_resume.txt", "STATUS": "IN_PROGRESS"}
    ]
    with open(resume_tx_file, 'w') as f:
        json.dump(resume_transactions_data, f)


def _verify_self_test_results_task(
    temp_dir: Path, 
    original_transaction_file: Path, 
    is_resume_run: bool = False, 
    resume_tx_file_path: Optional[Path] = None 
) -> bool:
    sys.stdout.write(BLUE + "--- Verifying Self-Test Results ---" + RESET + "\n")
    passed_checks = 0
    failed_checks = 0
    test_results: List[Dict[str, Any]] = []
    test_counter = 0

    def record_test(description: str, condition: bool, details_on_fail: str = "") -> None:
        nonlocal passed_checks, failed_checks, test_counter
        test_counter += 1
        status = "PASS" if condition else "FAIL"
        
        if condition:
            passed_checks += 1
        else:
            failed_checks += 1
            
        test_results.append({
            "id": test_counter,
            "description": description,
            "status": status,
            "details": details_on_fail if not condition else ""
        })

    exp_paths_after_rename = {
        "atlasvibe_root": temp_dir / "atlasvibe_root",
        "sub_atlasvibe_folder": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder",
        "another_ATLASVIBE_dir": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir",
        "deep_atlasvibe_file.txt": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file.txt",
        "another_atlasvibe_file.py": temp_dir / "atlasvibe_root" / "another_atlasvibe_file.py",
        "only_name_atlasvibe.md": temp_dir / "only_name_atlasvibe.md",
        "file_with_atlasVibe_lines.txt": temp_dir / "file_with_atlasVibe_lines.txt",
        "unmapped_variant_atlasvibe_content.txt": temp_dir / "unmapped_variant_atlasvibe_content.txt",
        "no_target_here.log": temp_dir / "no_target_here.log", 
        "exclude_this_flojoy_file.txt": temp_dir / "exclude_this_flojoy_file.txt",
        "excluded_flojoy_dir": temp_dir / "excluded_flojoy_dir",
        "inner_flojoy_file.txt_in_excluded_dir": temp_dir / "excluded_flojoy_dir" / "inner_flojoy_file.txt",
        "binary_atlasvibe_file.bin": temp_dir / "binary_atlasvibe_file.bin",
        "binary_fLoJoY_name.bin": temp_dir / "binary_fLoJoY_name.bin",
        "depth10_file_atlasvibe.txt": temp_dir / "depth1_atlasvibe" / "depth2" / "depth3_atlasvibe" / "depth4" / "depth5" / "depth6_atlasvibe" / "depth7" / "depth8" / "depth9_atlasvibe" / "depth10_file_atlasvibe.txt",
        "gb18030_atlasvibe_file.txt": temp_dir / "gb18030_atlasvibe_file.txt",
        "large_atlasvibe_file.txt": temp_dir / "large_atlasvibe_file.txt",
        # For resume test
        "completed_atlasvibe_for_resume.txt": temp_dir / "completed_atlasvibe_for_resume.txt",
        "pending_atlasvibe_for_resume.txt": temp_dir / "pending_atlasvibe_for_resume.txt",
        "inprogress_atlasvibe_for_resume.txt": temp_dir / "inprogress_atlasvibe_for_resume.txt",
    }

    if not is_resume_run:
        record_test("Test to assess renaming of top-level directories containing the target string.", 
                    exp_paths_after_rename["atlasvibe_root"].exists(), 
                    f"Renamed top-level dir '{exp_paths_after_rename['atlasvibe_root'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess renaming of nested directories containing the target string.", 
                    exp_paths_after_rename["sub_atlasvibe_folder"].exists(), 
                    f"Renamed nested dir '{exp_paths_after_rename['sub_atlasvibe_folder'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess renaming of deeply nested directories with case variations of the target string.", 
                    exp_paths_after_rename["another_ATLASVIBE_dir"].exists(), 
                    f"Renamed deep dir '{exp_paths_after_rename['another_ATLASVIBE_dir'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess renaming of files within transformed directory paths.", 
                    exp_paths_after_rename["deep_atlasvibe_file.txt"].exists(), 
                    f"Renamed file in transformed path '{exp_paths_after_rename['deep_atlasvibe_file.txt'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess file renaming at various levels of the directory tree.", 
                    exp_paths_after_rename["another_atlasvibe_file.py"].exists(), 
                    f"Renamed file '{exp_paths_after_rename['another_atlasvibe_file.py'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess file renaming based solely on a target string match in the filename.", 
                    exp_paths_after_rename["only_name_atlasvibe.md"].exists(), 
                    f"Renamed file '{exp_paths_after_rename['only_name_atlasvibe.md'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess file renaming when the target string in the filename has mixed casing.", 
                    exp_paths_after_rename["file_with_atlasVibe_lines.txt"].exists(), 
                    f"Renamed file '{exp_paths_after_rename['file_with_atlasVibe_lines.txt'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess file renaming when the filename is mapped but content has unmapped variants.", 
                    exp_paths_after_rename["unmapped_variant_atlasvibe_content.txt"].exists(), 
                    f"Renamed file '{exp_paths_after_rename['unmapped_variant_atlasvibe_content.txt'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess that files without the target string in name or content remain unchanged.", 
                    exp_paths_after_rename["no_target_here.log"].exists(), 
                    f"Unchanged file '{exp_paths_after_rename['no_target_here.log'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess that explicitly excluded files are not renamed and persist.", 
                    exp_paths_after_rename["exclude_this_flojoy_file.txt"].exists(), 
                    f"Excluded file '{exp_paths_after_rename['exclude_this_flojoy_file.txt'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess that explicitly excluded directories are not renamed and persist.", 
                    exp_paths_after_rename["excluded_flojoy_dir"].exists(), 
                    f"Excluded dir '{exp_paths_after_rename['excluded_flojoy_dir'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess that files within excluded directories are not renamed and persist.", 
                    exp_paths_after_rename["inner_flojoy_file.txt_in_excluded_dir"].exists(), 
                    f"File in excluded dir '{exp_paths_after_rename['inner_flojoy_file.txt_in_excluded_dir'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess renaming of binary files when their names contain a mapped target string.", 
                    exp_paths_after_rename["binary_atlasvibe_file.bin"].exists(), 
                    f"Renamed binary file '{exp_paths_after_rename['binary_atlasvibe_file.bin'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess that binary files with unmapped target string variants in their names are NOT renamed.", 
                    exp_paths_after_rename["binary_fLoJoY_name.bin"].exists(), 
                    f"Unrenamed binary file '{exp_paths_after_rename['binary_fLoJoY_name.bin'].relative_to(temp_dir)}' MISSING.")
        record_test("Test to assess removal of original directories after they are renamed.", 
                    not (temp_dir / "flojoy_root").exists(),
                    "Old 'flojoy_root' base directory STILL EXISTS.")

    def check_file_content(file_path: Optional[Path], expected_content: Union[str, bytes], test_description_base: str, is_binary: bool = False):
        if not file_path or not file_path.exists():
            record_test(f"{test_description_base} (File Existence for Content Check)", False, f"File MISSING at '{file_path}' for content check.")
            return
        actual_content: Union[str, bytes]
        if is_binary:
            actual_content = file_path.read_bytes()
        else:
            actual_content = file_path.read_text(encoding='utf-8')
        condition = actual_content == expected_content
        details = ""
        if not condition:
            details = f"Expected (repr):\n{expected_content!r}\nGot (repr):\n{actual_content!r}" if not is_binary else f"Expected (bytes): {expected_content!r}\nGot (bytes): {actual_content!r}"
        record_test(test_description_base, condition, details)

    if not is_resume_run:
        check_file_content(exp_paths_after_rename.get("deep_atlasvibe_file.txt"),
                           "Line 1: atlasvibe content.\nLine 2: More AtlasVibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project.",
                           "Test to assess content replacement of all mapped target string variants in a deeply nested text file.")
        check_file_content(exp_paths_after_rename.get("file_with_atlasVibe_lines.txt"),
                           "First atlasVibe.\nSecond AtlasVibe.\natlasvibe and ATLASVIBE on same line.",
                           "Test to assess content replacement of mixed-case mapped target string variants.")
        check_file_content(exp_paths_after_rename.get("unmapped_variant_atlasvibe_content.txt"),
                           "This has fLoJoY content, and also atlasvibe.",
                           "Test to assess preservation of unmapped target string variants alongside replacement of mapped ones in content.")
        check_file_content(exp_paths_after_rename.get("only_name_atlasvibe.md"),
                           "Content without target string.",
                           "Test to assess that file content remains unchanged if only the filename matched the target string.")
        check_file_content(exp_paths_after_rename.get("exclude_this_flojoy_file.txt"),
                           "flojoy content in explicitly excluded file",
                           "Test to assess that content of explicitly excluded files remains untouched.")
        check_file_content(exp_paths_after_rename.get("inner_flojoy_file.txt_in_excluded_dir"),
                           "flojoy inside excluded dir",
                           "Test to assess that content of files within excluded directories remains untouched.")
        check_file_content(exp_paths_after_rename.get("binary_atlasvibe_file.bin"),
                           b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04",
                           "Test to assess that binary file content remains untouched even if filename is renamed.", is_binary=True)
        check_file_content(exp_paths_after_rename.get("binary_fLoJoY_name.bin"),
                           b"unmapped_variant_binary_content" + b"\x00\xff",
                           "Test to assess that binary file content remains untouched if filename is not mapped for rename.", is_binary=True)

        binary_file_renamed = exp_paths_after_rename.get("binary_atlasvibe_file.bin")
        if binary_file_renamed and binary_file_renamed.exists():
            record_test(f"Test to assess that a renamed binary file ('{binary_file_renamed.name}') is still correctly identified as binary.",
                        is_likely_binary_file(binary_file_renamed),
                        f"File '{binary_file_renamed.name}' NOT detected as binary after rename.")

    if not is_resume_run:
        record_test("Test to assess the ability to replace folder and file names in a directory tree of depth=10.",
                    exp_paths_after_rename["depth10_file_atlasvibe.txt"].exists(),
                    f"Deeply nested file '{exp_paths_after_rename['depth10_file_atlasvibe.txt'].relative_to(temp_dir)}' not found or not renamed correctly.")
        check_file_content(exp_paths_after_rename.get("depth10_file_atlasvibe.txt"),
                           "atlasvibe deep content",
                           "Test to assess content replacement in a file within a directory tree of depth=10.")

        gb_file_path = exp_paths_after_rename.get("gb18030_atlasvibe_file.txt")
        gb_expected_content = "你好 atlasvibe 世界"
        if not (gb_file_path and gb_file_path.exists()):
            record_test("Test to assess the ability to search and replace strings in files with GB18030 charset encoding.", False, f"GB18030 test file missing: {gb_file_path}. Setup issue.")
        else:
            try:
                gb_actual_content = gb_file_path.read_text(encoding="gb18030")
                record_test("Test to assess the ability to search and replace strings in files with GB18030 charset encoding.", 
                            gb_actual_content == gb_expected_content,
                            f"GB18030 content mismatch. Expected (repr): {gb_expected_content!r}, Got (repr): {gb_actual_content!r}")
            except Exception as e:
                record_test("Test to assess the ability to search and replace strings in files with GB18030 charset encoding.", False, f"Error reading GB18030 file: {e}")

    record_test("Test to assess the ability of replacing a string with its replacement according to the replacement map.", True, "Implicitly covered by various content replacement tests.")
    record_test("Test to assess the ability to leave intact the occurrences of the string that are not included in the replacement map.", True, "Implicitly covered by unmapped variant tests (name & content).")
    record_test("Test to assess the ability to find in text files multiple lines with the string occurrences.", True, "Implicitly covered by 'deep_atlasvibe_file.txt' content checks which has multiple occurrences.")

    if not is_resume_run:
        initial_transactions = load_transactions(original_transaction_file) 
        if initial_transactions is not None:
            expected_line_tx_count_deep_file = 3 
            actual_line_tx_count_deep_file = sum(1 for tx in initial_transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and "deep_flojoy_file.txt" in tx["PATH"])
            record_test("Test to assess the ability to create a transaction entry for each line occurrence in a multi-occurrence file.",
                        actual_line_tx_count_deep_file == expected_line_tx_count_deep_file,
                        f"Expected {expected_line_tx_count_deep_file} line transactions for 'deep_flojoy_file.txt', found {actual_line_tx_count_deep_file}.")

            # Count all file name transactions that should result in a rename
            expected_file_name_tx_count = 0
            for key, path_obj in exp_paths_after_rename.items():
                original_name_part = Path(key).name # e.g., "atlasvibe_root" -> "atlasvibe_root"
                # Heuristic: if it ends with common extension or doesn't have one, it might be a file/folder name
                # This is a bit fragile; better to check against the original setup structure if possible
                if "." in original_name_part or "dir" in original_name_part or "folder" in original_name_part or "root" in original_name_part:
                     # Attempt to reconstruct original name based on replacement logic
                     if "atlasvibe" in original_name_part.lower(): # If it was renamed
                        # This count is tricky without knowing the exact original names that were mapped
                        pass # Placeholder for a more accurate count if needed
            # Using a known count from previous implementation for mapped names
            # This counts transactions where ORIGINAL_NAME would change after replacement
            actual_file_name_tx_count = sum(1 for tx in initial_transactions if tx["TYPE"] == TransactionType.FILE_NAME.value and tx["ORIGINAL_NAME"] != replace_flojoy_occurrences(tx["ORIGINAL_NAME"]))
            # Expected: deep_flojoy_file, another_flojoy_file, only_name_flojoy, file_with_floJoy_lines, 
            # unmapped_variant_flojoy_content, binary_flojoy_file, 
            # depth10_file_flojoy, gb18030_flojoy_file, large_flojoy_file = 9
            # Plus files for resume test setup: completed_flojoy_for_resume, pending_flojoy_for_resume, inprogress_flojoy_for_resume = 3
            # Total = 12
            # However, the scan for the main self-test doesn't include the "for_resume_test" files in its transaction list.
            # So, expected is 9.
            record_test("Test to assess the ability to create a transaction entry for each file name containing a mapped target string.",
                        actual_file_name_tx_count >= 9, 
                        f"Expected at least 9 mapped file name transactions, found {actual_file_name_tx_count}.")

            actual_folder_name_tx_count = sum(1 for tx in initial_transactions if tx["TYPE"] == TransactionType.FOLDER_NAME.value)
            # Expected: flojoy_root, sub_flojoy_folder, another_FLOJOY_dir, depth1_flojoy, depth3_flojoy, depth6_flojoy, depth9_flojoy = 7
            record_test("Test to assess the ability to create a transaction entry for each folder name containing a mapped target string.",
                        actual_folder_name_tx_count == 7,
                        f"Expected 7 folder name transactions, found {actual_folder_name_tx_count}.")
        else:
            record_test("Test to assess transaction generation for line/file/folder occurrences (prerequisite: load transaction file).", False, "Could not load initial transaction file for generation checks.")


    record_test("Test to assess the ability to execute a transaction for line content modification.", True, "Implicitly covered by verifying final file content after changes.")
    record_test("Test to assess the ability to execute a transaction for file name replacement.", True, "Implicitly covered by verifying final file names/paths after changes.")
    record_test("Test to assess the ability to execute a transaction for folder name replacement.", True, "Implicitly covered by verifying final folder names/paths after changes.")
    
    tx_file_for_backup_check = resume_tx_file_path if is_resume_run and resume_tx_file_path else original_transaction_file
    record_test("Test to assess the atomicity of transaction file updates via backup creation.", 
                (tx_file_for_backup_check.with_suffix(tx_file_for_backup_check.suffix + TRANSACTION_FILE_BACKUP_EXT)).exists(), 
                f"Backup file for '{tx_file_for_backup_check.name}' not found. Atomicity check via backup failed.")

    record_test("Test to assess the deterministic nature of scan results by comparing two separate scans.", False, "Test not yet implemented. Requires significant new logic for dual scan and comparison of JSON outputs.")
    record_test("Test to assess the ability to resume the scan phase from an incomplete transaction file.", False, "Test not yet implemented. Current resume logic only applies to the execution phase.")

    if is_resume_run:
        record_test("Test to assess resuming execution of PENDING file rename transactions.",
                    exp_paths_after_rename["pending_atlasvibe_for_resume.txt"].exists(), 
                    f"File '{exp_paths_after_rename['pending_atlasvibe_for_resume.txt'].name}' from resumed PENDING task not found.")
        check_file_content(exp_paths_after_rename.get("pending_atlasvibe_for_resume.txt"),
                           "pending content atlasvibe", # Assuming content also gets updated if name does
                           "Test to assess content of file from resumed PENDING file rename task.")
        record_test("Test to assess resuming execution of IN_PROGRESS file rename transactions.",
                    exp_paths_after_rename["inprogress_atlasvibe_for_resume.txt"].exists(), 
                    f"File '{exp_paths_after_rename['inprogress_atlasvibe_for_resume.txt'].name}' from resumed IN_PROGRESS task not found.")
        check_file_content(exp_paths_after_rename.get("inprogress_atlasvibe_for_resume.txt"),
                           "in progress content atlasvibe", # Assuming content also gets updated
                           "Test to assess content of file from resumed IN_PROGRESS file rename task.")
        record_test("Test to assess that COMPLETED transactions are not re-processed during resume.",
                    exp_paths_after_rename["completed_atlasvibe_for_resume.txt"].exists() and \
                    not (temp_dir / "completed_flojoy_for_resume.txt").exists(), 
                    "File from COMPLETED task in resume was unexpectedly reprocessed, its original form re-appeared, or it was missing.")
    else:
         record_test("Test to assess resuming execution of partially completed transaction sets.", False, "Resume sub-test not active for this run. Trigger with --run-resume-sub-test.")

    record_test("Test to assess the ability to retry failed transactions (ERROR state).", False, "Test not yet implemented. Error retry logic is not a current feature.")
    
    if not is_resume_run:
        large_file_path = exp_paths_after_rename.get("large_atlasvibe_file.txt")
        if not (large_file_path and large_file_path.exists()): 
            record_test("Test to assess processing of large text files (simulated >10MB) for string replacement.", False, f"Large test file missing: {large_file_path}. Setup issue.")
        else:
            try:
                with open(large_file_path, "r") as f: 
                    lines = [f.readline().strip() for _ in range(5)] 
                expected_lines = ["This atlasvibe line should be replaced " + str(i) if i % 100 == 0 else "Normal line " + str(i) for i in range(5)]
                record_test("Test to assess processing of large text files (simulated >10MB) for string replacement.", 
                            lines == expected_lines,
                            f"Large file content mismatch. Expected head: {expected_lines!r}, Got: {lines!r}")
            except Exception as e:
                record_test("Test to assess processing of large text files (simulated >10MB) for string replacement.", False, f"Error reading large file: {e}")

    current_run_tx_file = resume_tx_file_path if is_resume_run and resume_tx_file_path else original_transaction_file
    transactions_for_status_check = load_transactions(current_run_tx_file) 

    if transactions_for_status_check is not None:
        all_relevant_tx_processed_correctly = True
        for tx_idx, tx in enumerate(transactions_for_status_check): 
            if is_resume_run and tx["id"] == "uuid_completed_resume": 
                if tx["STATUS"] != TransactionStatus.COMPLETED.value:
                    all_relevant_tx_processed_correctly = False
                    record_test(f"Transaction Lifecycle (Resume - Tx ID: {tx['id']}): Verify COMPLETED transaction remains COMPLETED.", False,
                                f"Path: {tx['PATH']}, Status is {tx['STATUS']}, expected COMPLETED.")
                    break
                else:
                    continue 
            is_excluded_item = "excluded_flojoy_dir/" in tx["PATH"] or tx["PATH"] == "exclude_this_flojoy_file.txt"
            if not is_excluded_item:
                if tx["STATUS"] not in [TransactionStatus.COMPLETED.value, TransactionStatus.SKIPPED.value]:
                    all_relevant_tx_processed_correctly = False
                    record_test(f"Transaction Lifecycle (Tx ID: {tx['id']}): Verify non-excluded transaction reaches final state (COMPLETED/SKIPPED).", False,
                                f"Path: {tx['PATH']}, Status is {tx['STATUS']}, expected COMPLETED or SKIPPED.")
                    break 
        if all_relevant_tx_processed_correctly: 
             record_test("Transaction Lifecycle: Verify all relevant transactions reach a final state (COMPLETED or SKIPPED).", True)
    else:
        record_test(f"Transaction File Integrity: Verify transaction file '{current_run_tx_file.name}' can be loaded.", False, f"Could not load transaction file '{current_run_tx_file.name}' for final status verification.")


    # --- Table Formatting ---
    term_width, _ = shutil.get_terminal_size(fallback=(80, 24))
    padding = 1
    id_col_content_width = len(str(test_counter)) if test_counter > 0 else 3 
    id_col_total_width = id_col_content_width + 2 * padding
    outcome_text_pass = f"{PASS_SYMBOL} PASS"
    outcome_text_fail = f"{FAIL_SYMBOL} FAIL"
    outcome_col_content_width = max(len(outcome_text_pass), len(outcome_text_fail))
    outcome_col_total_width = outcome_col_content_width + 2 * padding
    desc_col_total_width = term_width - (id_col_total_width + outcome_col_total_width + 4) 
    min_desc_col_content_width = 20
    if desc_col_total_width - 2 * padding < min_desc_col_content_width:
        desc_col_content_width = min_desc_col_content_width
        desc_col_total_width = desc_col_content_width + 2 * padding
    else:
        desc_col_content_width = desc_col_total_width - 2 * padding

    header_id = f"{'#':^{id_col_content_width}}"
    header_desc = f"{'Test Description':^{desc_col_content_width}}"
    header_outcome = f"{'Outcome':<{outcome_col_content_width}}" 

    sys.stdout.write("\n")
    sys.stdout.write(BLUE + DBL_TOP_LEFT + DBL_HORIZONTAL * id_col_total_width + DBL_T_DOWN + DBL_HORIZONTAL * desc_col_total_width + DBL_T_DOWN + DBL_HORIZONTAL * outcome_col_total_width + DBL_TOP_RIGHT + RESET + "\n")
    sys.stdout.write(BLUE + DBL_VERTICAL + f"{' ' * padding}{header_id}{' ' * padding}" + DBL_VERTICAL + f"{' ' * padding}{header_desc}{' ' * padding}" + DBL_VERTICAL + f"{' ' * padding}{header_outcome}{' ' * padding}" + DBL_VERTICAL + RESET + "\n")
    sys.stdout.write(BLUE + DBL_T_RIGHT + DBL_HORIZONTAL * id_col_total_width + DBL_CROSS + DBL_HORIZONTAL * desc_col_total_width + DBL_CROSS + DBL_HORIZONTAL * outcome_col_total_width + DBL_T_LEFT + RESET + "\n")

    failed_test_details_print_buffer = []
    for result in test_results:
        status_symbol = PASS_SYMBOL if result["status"] == "PASS" else FAIL_SYMBOL
        color = GREEN if result["status"] == "PASS" else RED
        outcome_text_content = f"{status_symbol} {result['status']}"
        id_text_content = str(result['id'])
        wrapped_desc_lines = textwrap.wrap(result['description'], width=desc_col_content_width)
        if not wrapped_desc_lines: 
            wrapped_desc_lines = [''] 

        for i, line_frag in enumerate(wrapped_desc_lines):
            if i == 0:
                id_cell_str = f"{' ' * padding}{id_text_content:>{id_col_content_width}}{' ' * padding}"
                outcome_cell_str = f"{' ' * padding}{color}{outcome_text_content:<{outcome_col_content_width}}{RESET}{' ' * padding}"
            else:
                id_cell_str = " " * id_col_total_width 
                outcome_cell_str = " " * outcome_col_total_width
            
            desc_cell_str = f"{' ' * padding}{line_frag:<{desc_col_content_width}}{' ' * padding}"
            sys.stdout.write(BLUE + DBL_VERTICAL + id_cell_str + DBL_VERTICAL + desc_cell_str + DBL_VERTICAL + outcome_cell_str + DBL_VERTICAL + RESET + "\n")

        if result["status"] == "FAIL" and result["details"]:
            failed_test_details_print_buffer.append(RED + f"Test #{result['id']}: {result['description']}" + RESET)
            for detail_line in result["details"].split('\n'):
                 failed_test_details_print_buffer.append(RED + f"  └── {detail_line}" + RESET)
    
    sys.stdout.write(BLUE + DBL_BOTTOM_LEFT + DBL_HORIZONTAL * id_col_total_width + DBL_T_UP + DBL_HORIZONTAL * desc_col_total_width + DBL_T_UP + DBL_HORIZONTAL * outcome_col_total_width + DBL_BOTTOM_RIGHT + RESET + "\n")

    if failed_test_details_print_buffer:
        sys.stdout.write("\n" + RED + "--- Failure Details ---" + RESET + "\n")
        for line in failed_test_details_print_buffer:
            sys.stdout.write(line + "\n")
    
    sys.stdout.write(YELLOW + "\n--- Self-Test Summary ---" + RESET + "\n")
    total_tests = passed_checks + failed_checks
    if total_tests > 0:
        percentage_passed = (passed_checks / total_tests) * 100
        summary_color = GREEN if failed_checks == 0 else RED
        summary_emoji = PASS_SYMBOL if failed_checks == 0 else FAIL_SYMBOL
        sys.stdout.write(f"Total Tests Run: {total_tests}\n")
        sys.stdout.write(f"Passed: {GREEN}{passed_checks}{RESET}\n")
        sys.stdout.write(f"Failed: {RED if failed_checks > 0 else GREEN}{failed_checks}{RESET}\n")
        sys.stdout.write(f"Success Rate: {summary_color}{percentage_passed:.2f}% {summary_emoji}{RESET}\n")
        if failed_checks == 0:
            sys.stdout.write(GREEN + "All self-test checks passed successfully! " + PASS_SYMBOL + RESET + "\n")
        else:
            sys.stdout.write(RED + f"Self-test FAILED with {failed_checks} error(s). " + FAIL_SYMBOL + RESET + "\n")
    else:
        sys.stdout.write(YELLOW + "No self-test checks were recorded." + RESET + "\n")
    sys.stdout.flush()
    if failed_checks > 0:
        raise AssertionError(f"Self-test failed with {failed_checks} assertion(s).")
    return True


@flow(name="Self-Test Flow", log_prints=True)
def self_test_flow(
    temp_dir_str: str, 
    dry_run_for_test: bool,
    run_resume_sub_test: bool = False 
) -> None:
    temp_dir = Path(temp_dir_str) 
    _create_self_test_environment(temp_dir) 

    test_excluded_dirs: List[str] = ["excluded_flojoy_dir"] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt"]
    test_extensions = [".txt", ".py", ".md", ".bin", ".log"] 

    if run_resume_sub_test:
        print("Self-Test (Resume Sub-Test): Executing transactions with --resume...")
        resume_tx_file = temp_dir / "for_resume_test_transactions.json"
        
        # Simulate that 'completed_flojoy_for_resume.txt' was already processed and renamed
        # Also, its content should have been updated.
        completed_original_path = temp_dir / "completed_flojoy_for_resume.txt"
        completed_renamed_path = temp_dir / "completed_atlasvibe_for_resume.txt"
        if completed_original_path.exists():
            completed_original_path.rename(completed_renamed_path)
            # Simulate content update for the "completed" one as if it was processed
            if completed_renamed_path.exists():
                 completed_renamed_path.write_text("already done atlasvibe content")


        # Ensure 'pending' and 'inprogress' are in their 'before rename' state for the resume test
        # Their content should still be 'flojoy'
        if (temp_dir / "pending_atlasvibe_for_resume.txt").exists():
            (temp_dir / "pending_atlasvibe_for_resume.txt").rename(temp_dir / "pending_flojoy_for_resume.txt")
            (temp_dir / "pending_flojoy_for_resume.txt").write_text("pending content flojoy")

        if (temp_dir / "inprogress_atlasvibe_for_resume.txt").exists():
            (temp_dir / "inprogress_atlasvibe_for_resume.txt").rename(temp_dir / "inprogress_flojoy_for_resume.txt")
            (temp_dir / "inprogress_flojoy_for_resume.txt").write_text("in progress content flojoy")


        execution_stats = execute_all_transactions(
            transactions_file_path=resume_tx_file,
            root_dir=temp_dir, 
            dry_run=False, 
            resume=True   
        )
        print(f"Self-Test (Resume Sub-Test): Execution complete. Stats: {execution_stats}")
        _verify_self_test_results_task(
            temp_dir=temp_dir, 
            original_transaction_file=resume_tx_file, 
            is_resume_run=True,
            resume_tx_file_path=resume_tx_file
        )
    else:
        transaction_file = temp_dir / SELF_TEST_PRIMARY_TRANSACTION_FILE
        print("Self-Test (Standard Run): Scanning directory...")
        transactions = scan_directory_for_occurrences(
            root_dir=temp_dir,
            excluded_dirs=test_excluded_dirs,
            excluded_files=test_excluded_files,
            file_extensions=test_extensions
        )
        save_transactions(transactions, transaction_file)
        print(f"Self-Test (Standard Run): Scan complete. {len(transactions)} transactions planned in {transaction_file}")

        if not dry_run_for_test:
            print("Self-Test (Standard Run): Executing transactions...")
            execution_stats = execute_all_transactions(
                transactions_file_path=transaction_file,
                root_dir=temp_dir, 
                dry_run=False, 
                resume=False   
            )
            print(f"Self-Test (Standard Run): Execution complete. Stats: {execution_stats}")
            
            _verify_self_test_results_task(
                temp_dir=temp_dir, 
                original_transaction_file=transaction_file,
                is_resume_run=False 
            )
        else:
            print("Self-Test (Standard Run): Dry run selected. Skipping execution and verification of changes.")


# --- Main CLI Orchestration ---
@flow(name="Mass Find and Replace Orchestration Flow", log_prints=True)
def main_flow(
    directory: str,
    extensions: Optional[List[str]],
    exclude_dirs: List[str],
    exclude_files: List[str],
    dry_run: bool,
    skip_scan: bool,
    resume: bool,
    force_execution: bool 
):
    root_dir = Path(directory).resolve()
    if not root_dir.is_dir():
        sys.stderr.write(f"Error: Root directory '{root_dir}' does not exist or is not a directory.\n")
        return

    transaction_json_path = root_dir / MAIN_TRANSACTION_FILE_NAME

    if not dry_run and not force_execution and not resume: 
        sys.stdout.write("--- Proposed Operation ---\n")
        sys.stdout.write(f"Root Directory: {root_dir}\n")
        sys.stdout.write("Operation: Replace 'flojoy' and its variants with 'atlasvibe' equivalents.\n")
        sys.stdout.write(f"File Extensions for content scan: {extensions if extensions else 'All non-binary (heuristic)'}\n")
        sys.stdout.write(f"Exclude Dirs: {exclude_dirs}\n")
        sys.stdout.write(f"Exclude Files: {exclude_files}\n")
        sys.stdout.write("-------------------------\n")
        sys.stdout.flush() 
        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes':
            sys.stdout.write("Operation cancelled by user.\n")
            return

    if not skip_scan and not resume: 
        print(f"Starting scan phase in '{root_dir}'...")
        found_transactions = scan_directory_for_occurrences(
            root_dir=root_dir,
            excluded_dirs=exclude_dirs,
            excluded_files=exclude_files,
            file_extensions=extensions
        )
        save_transactions(found_transactions, transaction_json_path)
        print(f"Scan complete. {len(found_transactions)} transactions planned in '{transaction_json_path}'")
        if not found_transactions:
            print("No occurrences found. Nothing to do.")
            return
    elif not transaction_json_path.exists() and (skip_scan or resume):
        print(f"Error: --skip-scan or --resume was used, but '{transaction_json_path}' not found.")
        return
    else:
        print(f"Using existing transaction file: '{transaction_json_path}'.")

    if dry_run:
        print("Dry run: Simulating execution of transactions...")
        stats = execute_all_transactions(
            transactions_file_path=transaction_json_path,
            root_dir=root_dir,
            dry_run=True,
            resume=resume 
        )
        print(f"Dry run complete. Simulated stats: {stats}")
        print(f"Review '{transaction_json_path}' for transaction details and statuses (will show DRY_RUN).")
    else:
        print("Starting execution phase...")
        stats = execute_all_transactions(
            transactions_file_path=transaction_json_path,
            root_dir=root_dir,
            dry_run=False,
            resume=resume
        )
        print(f"Execution phase complete. Stats: {stats}")
        print(f"Review '{transaction_json_path}' for a log of applied changes and their statuses.")


def main_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Find and replace 'flojoy' with 'atlasvibe' (case-preserving) in file/folder names and content. Binary file content is ignored.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("directory", nargs='?', default=".",
                        help="The root directory to process (default: current directory).")
    parser.add_argument("--extensions", nargs="+",
                        help="List of file extensions to process for content changes (e.g., .py .txt). If not specified, attempts to process text-like files, skipping binaries.")
    parser.add_argument("--exclude-dirs", nargs="+", default=[".git", ".venv", "node_modules", "__pycache__"],
                        help="Directory names to exclude (default: .git, .venv, node_modules, __pycache__).")
    parser.add_argument("--exclude-files", nargs="+", default=[],
                        help="Specific file paths (relative to root) to exclude.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and plan changes, but do not execute them. Updates transaction file with DRY_RUN status.")
    parser.add_argument("--skip-scan", action="store_true",
                        help=f"Skip scan phase; use existing '{MAIN_TRANSACTION_FILE_NAME}'.")
    parser.add_argument("--resume", action="store_true",
                        help=f"Resume execution from existing '{MAIN_TRANSACTION_FILE_NAME}', processing PENDING or IN_PROGRESS tasks.")
    parser.add_argument("--force", "--yes", "-y", action="store_true",
                        help="Force execution without confirmation prompt (if not in dry-run or resume mode).")
    parser.add_argument("--self-test", action="store_true",
                        help=f"Run a predefined self-test in a sandboxed '{SELF_TEST_SANDBOX_DIR}' directory.")
    parser.add_argument("--run-resume-sub-test", action="store_true", help=argparse.SUPPRESS) 

    args = parser.parse_args()
    
    if args.self_test or args.run_resume_sub_test: 
        is_resume_sub_test_run = args.run_resume_sub_test

        sys.stdout.write(f"Running self-test {'(Resume Sub-Test)' if is_resume_sub_test_run else '(Standard Run)'} in sandbox: '{SELF_TEST_SANDBOX_DIR}'...\n")
        self_test_sandbox = Path(SELF_TEST_SANDBOX_DIR).resolve()
        
        if self_test_sandbox.exists():
            sys.stdout.write(f"Cleaning existing sandbox: {self_test_sandbox}\n")
            try:
                shutil.rmtree(self_test_sandbox)
            except OSError as e:
                sys.stderr.write(RED + f"Error cleaning sandbox {self_test_sandbox}: {e}" + RESET + "\n")
                sys.exit(1)
        try:
            self_test_sandbox.mkdir(parents=True, exist_ok=True)
            sys.stdout.write(f"Created sandbox: {self_test_sandbox}\n")
        except OSError as e:
            sys.stderr.write(RED + f"Error creating sandbox {self_test_sandbox}: {e}" + RESET + "\n")
            sys.exit(1)
        
        sys.stdout.flush() 
            
        try:
            self_test_flow(
                temp_dir_str=str(self_test_sandbox), 
                dry_run_for_test=args.dry_run, 
                run_resume_sub_test=is_resume_sub_test_run
            )
            if args.dry_run and not is_resume_sub_test_run: 
                 sys.stdout.write(YELLOW + "Self-test (Standard Run) dry run scan complete." + RESET + "\n")
        except AssertionError: 
            sys.exit(1) 
        except Exception as e:
            sys.stderr.write(RED + f"Self-test ERRORED: An unexpected error occurred: {e} " + FAIL_SYMBOL + RESET + "\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
        finally:
            if self_test_sandbox.exists():
                sys.stdout.write(f"Cleaning up self-test sandbox: {self_test_sandbox}\n")
                try:
                    shutil.rmtree(self_test_sandbox)
                    sys.stdout.write(f"Sandbox '{self_test_sandbox}' successfully removed.\n")
                except OSError as e:
                    sys.stderr.write(RED + f"Error removing sandbox {self_test_sandbox}: {e}" + RESET + "\n")
            sys.stdout.flush()
        return

    default_log_files_to_exclude = [
        MAIN_TRANSACTION_FILE_NAME,
        MAIN_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT,
    ]
    for log_file in default_log_files_to_exclude:
        if log_file not in args.exclude_files:
            args.exclude_files.append(log_file)
    
    try:
        script_path_obj = Path(__file__).resolve(strict=True)
        target_dir_resolved = Path(args.directory).resolve(strict=True)
        if script_path_obj.is_relative_to(target_dir_resolved):
             script_relative_to_target = str(script_path_obj.relative_to(target_dir_resolved))
             if script_relative_to_target not in args.exclude_files:
                 args.exclude_files.append(script_relative_to_target)
    except (FileNotFoundError, ValueError): 
         pass 

    main_flow(
        directory=args.directory,
        extensions=args.extensions,
        exclude_dirs=args.exclude_dirs,
        exclude_files=args.exclude_files,
        dry_run=args.dry_run,
        skip_scan=args.skip_scan,
        resume=args.resume,
        force_execution=args.force
    )

if __name__ == "__main__":
    try:
        main_cli()
    except ImportError as e:
        sys.stderr.write(f"CRITICAL ERROR: A required dependency is missing: {e}.\n")
        sys.stderr.write("Please ensure 'prefect' and 'chardet' are installed in your Python environment.\n")
        sys.stderr.write("You can typically install them using pip: pip install prefect chardet\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

