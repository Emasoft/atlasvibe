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
from typing import List, Dict, Any, Optional, Union, Callable # Added Callable
import shutil # For shutil.rmtree and shutil.get_terminal_size
import textwrap # Added for text wrapping
import json # Added to resolve F821
import os # For os.chmod
import operator # For sorting transactions

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
# Import specific functions from replace_logic, or the module itself
import replace_logic # To call its loading function or access its state

# --- Constants ---
MAIN_TRANSACTION_FILE_NAME = "planned_transactions.json"
DEFAULT_REPLACEMENT_MAPPING_FILE = "replacement_mapping.json" # Default name
SELF_TEST_PRIMARY_TRANSACTION_FILE = "self_test_transactions.json"
SELF_TEST_SCAN_VALIDATION_FILE = "self_test_scan_validation_transactions.json"
SELF_TEST_SANDBOX_DIR = "./tests/temp" # Defined sandbox for self-tests
SELF_TEST_COMPLEX_MAP_FILE = "self_test_complex_mapping.json"

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
def _create_self_test_environment(base_dir: Path, use_complex_map: bool = False) -> None:
    """Creates a directory structure and files for self-testing."""
    # Standard "flojoy" test files
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
        "This has fLoJoY content, and also flojoy." # fLoJoY is not in default map
    )
    (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")
    (base_dir / "binary_fLoJoY_name.bin").write_bytes(b"unmapped_variant_binary_content" + b"\x00\xff")

    (base_dir / "excluded_flojoy_dir").mkdir(exist_ok=True)
    (base_dir / "excluded_flojoy_dir" / "inner_flojoy_file.txt").write_text("flojoy inside excluded dir")
    (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in explicitly excluded file")
    (base_dir / "no_target_here.log").write_text("This is a log file without the target string.")

    deep_path_parts = ["depth1_flojoy", "depth2", "depth3_flojoy", "depth4", "depth5", "depth6_flojoy", "depth7", "depth8", "depth9_flojoy", "depth10_file_flojoy.txt"]
    current_path = base_dir
    for part_idx, part in enumerate(deep_path_parts):
        current_path = current_path / part
        if part_idx < len(deep_path_parts) -1:
            current_path.mkdir(parents=True, exist_ok=True)
        else:
            current_path.write_text("flojoy deep content")

    try:
        (base_dir / "gb18030_flojoy_file.txt").write_text("你好 flojoy 世界", encoding="gb18030")
    except Exception:
        (base_dir / "gb18030_flojoy_file.txt").write_text("fallback flojoy content")

    large_file_content_list = []
    for i in range(5000):
        if i % 100 == 0:
            large_file_content_list.append("This flojoy line should be replaced " + str(i) + "\n")
        else:
            large_file_content_list.append("Normal line " + str(i) + "\n")
    (base_dir / "large_flojoy_file.txt").write_text("".join(large_file_content_list), encoding='utf-8')

    # Files for resume tests (using flojoy map)
    (base_dir / "completed_flojoy_for_exec_resume.txt").write_text("already done flojoy content")
    (base_dir / "pending_flojoy_for_exec_resume.txt").write_text("pending content flojoy")
    (base_dir / "inprogress_flojoy_for_exec_resume.txt").write_text("in progress content flojoy")
    resume_exec_tx_data = [
        {"id": "uuid_completed_exec_resume", "TYPE": "FILE_NAME", "PATH": "completed_flojoy_for_exec_resume.txt", "ORIGINAL_NAME": "completed_flojoy_for_exec_resume.txt", "STATUS": "COMPLETED"},
        {"id": "uuid_pending_exec_resume", "TYPE": "FILE_NAME", "PATH": "pending_flojoy_for_exec_resume.txt", "ORIGINAL_NAME": "pending_flojoy_for_exec_resume.txt", "STATUS": "PENDING"},
        {"id": "uuid_inprogress_exec_resume", "TYPE": "FILE_NAME", "PATH": "inprogress_flojoy_for_exec_resume.txt", "ORIGINAL_NAME": "inprogress_flojoy_for_exec_resume.txt", "STATUS": "IN_PROGRESS"}
    ]
    with open(base_dir / "for_exec_resume_test_transactions.json", 'w', encoding='utf-8') as f:
        json.dump(resume_exec_tx_data, f, indent=2)

    (base_dir / "scan_resume_initial_flojoy.txt").write_text("initial flojoy item for scan resume")
    (base_dir / "scan_resume_new_flojoy_folder").mkdir(exist_ok=True)
    (base_dir / "scan_resume_new_flojoy_folder" / "scan_resume_new_file_flojoy.txt").write_text("new flojoy item for scan resume")
    scan_resume_partial_data = [
        {"id": "uuid_scan_resume_initial", "TYPE": "FILE_NAME", "PATH": "scan_resume_initial_flojoy.txt", "ORIGINAL_NAME": "scan_resume_initial_flojoy.txt", "STATUS": "PENDING"}
    ]
    with open(base_dir / "for_scan_resume_test_transactions.json", 'w', encoding='utf-8') as f:
        json.dump(scan_resume_partial_data, f, indent=2)

    (base_dir / "error_file_flojoy.txt").write_text("This file will cause an error.")

    if use_complex_map:
        # Create files specific to the complex map test
        (base_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS").mkdir(parents=True, exist_ok=True)
        (base_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS" / "file_with_diacritics_ȕsele̮Ss_diá͡cRiti̅cS.txt").write_text(
            "Content with ȕsele̮Ss_diá͡cRiti̅cS and also useless_diacritics.\nAnd another Flojoy for good measure (should remain if not in complex map)."
        )
        (base_dir / "file_with_spaces_The spaces will not be ignored.md").write_text(
            "This file has The spaces will not be ignored in its name and content."
        )
        (base_dir / "_My_Love&Story.log").write_text("Log for _My_Love&Story and _my_love&story.")
        (base_dir / "filename_with_COCO4_ep-m.data").write_text("Data for COCO4_ep-m and Coco4_ep-M.")
        
        (base_dir / "special_chars_in_content_test.txt").write_text(
            "This line contains characters|not<allowed^in*paths::will/be!escaped%when?searched~in$filenames@and\"foldernames to be replaced."
        )
        # File with control characters in its name and content for testing control char stripping from keys
        (base_dir / "file_with_key_with\tcontrol\nchars.txt").write_text(
            "Content for key_with\tcontrol\nchars here."
        )

def check_file_content_for_test( 
    file_path: Optional[Path],
    expected_content: Union[str, bytes],
    test_description: str,
    record_test_func: Callable, 
    encoding: Optional[str] = 'utf-8',
    is_binary: bool = False
) -> None:
    """Helper to check file content for self-tests, normalizing line endings for strings."""
    if file_path is None or not file_path.exists():
        record_test_func(test_description + " (File Existence)", False, f"File missing: {file_path}")
        return

    try:
        if is_binary:
            actual_content = file_path.read_bytes()
            record_test_func(test_description, actual_content == expected_content, f"Expected binary content mismatch for {file_path}. Got (first 100 bytes): {actual_content[:100]!r}")
        else:
            actual_content = file_path.read_text(encoding=encoding, errors='surrogateescape')
            if isinstance(expected_content, str):
                # Normalize line endings for comparison as git might change them on checkout
                actual_content_normalized = actual_content.replace("\r\n", "\n").replace("\r", "\n")
                expected_content_normalized = expected_content.replace("\r\n", "\n").replace("\r", "\n")
                record_test_func(test_description, actual_content_normalized == expected_content_normalized, f"Expected content mismatch for {file_path}.\nExpected:\n'''{expected_content_normalized!r}'''\nGot:\n'''{actual_content_normalized!r}'''")
            else: 
                 record_test_func(test_description, False, f"Type mismatch for expected content (should be str) for {file_path}")

    except Exception as e:
        record_test_func(test_description, False, f"Error reading/comparing {file_path}: {e}")


def _verify_self_test_results_task(
    temp_dir: Path,
    original_transaction_file: Path,
    validation_transaction_file: Optional[Path] = None,
    is_exec_resume_run: bool = False,
    is_scan_resume_run: bool = False,
    resume_tx_file_path: Optional[Path] = None,
    is_complex_map_test: bool = False # Flag for complex map specific checks
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
        test_results.append({"id": test_counter, "description": description, "status": status, "details": details_on_fail if not condition else ""})

    exp_paths_std_map = {
        "atlasvibe_root": temp_dir / "atlasvibe_root",
        "sub_atlasvibe_folder": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder",
        "another_ATLASVIBE_dir": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir",
        "deep_atlasvibe_file.txt": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file.txt",
        "another_atlasvibe_file.py": temp_dir / "atlasvibe_root" / "another_atlasvibe_file.py",
        "only_name_atlasvibe.md": temp_dir / "only_name_atlasvibe.md",
        "file_with_atlasVibe_lines.txt": temp_dir / "file_with_atlasVibe_lines.txt", 
        "unmapped_variant_atlasvibe_content.txt": temp_dir / "unmapped_variant_atlasvibe_content.txt",
        "depth1_atlasvibe": temp_dir / "depth1_atlasvibe",
        "depth3_atlasvibe": temp_dir / "depth1_atlasvibe" / "depth2" / "depth3_atlasvibe",
        "depth6_atlasvibe": temp_dir / "depth1_atlasvibe" / "depth2" / "depth3_atlasvibe" / "depth4" / "depth5" / "depth6_atlasvibe",
        "depth9_atlasvibe": temp_dir / "depth1_atlasvibe" / "depth2" / "depth3_atlasvibe" / "depth4" / "depth5" / "depth6_atlasvibe" / "depth7" / "depth8" / "depth9_atlasvibe",
        "depth10_file_atlasvibe.txt": temp_dir / "depth1_atlasvibe" / "depth2" / "depth3_atlasvibe" / "depth4" / "depth5" / "depth6_atlasvibe" / "depth7" / "depth8" / "depth9_atlasvibe" / "depth10_file_atlasvibe.txt",
        "gb18030_atlasvibe_file.txt": temp_dir / "gb18030_atlasvibe_file.txt",
        "large_atlasvibe_file.txt": temp_dir / "large_atlasvibe_file.txt",
        "binary_atlasvibe_file.bin": temp_dir / "binary_atlasvibe_file.bin",
        "error_file_atlasvibe.txt": temp_dir / "error_file_atlasvibe.txt", 
        "no_target_here.log": temp_dir / "no_target_here.log",
        "exclude_this_flojoy_file.txt": temp_dir / "exclude_this_flojoy_file.txt",
        "excluded_flojoy_dir": temp_dir / "excluded_flojoy_dir",
        "inner_flojoy_file.txt_in_excluded_dir": temp_dir / "excluded_flojoy_dir" / "inner_flojoy_file.txt",
        "binary_fLoJoY_name.bin": temp_dir / "binary_fLoJoY_name.bin", 
        "error_file_flojoy.txt_orig": temp_dir / "error_file_flojoy.txt", 
    }
    exp_paths_resume = { 
        "completed_atlasvibe_for_exec_resume.txt": temp_dir / "completed_atlasvibe_for_exec_resume.txt",
        "pending_atlasvibe_for_exec_resume.txt": temp_dir / "pending_atlasvibe_for_exec_resume.txt",
        "inprogress_atlasvibe_for_exec_resume.txt": temp_dir / "inprogress_atlasvibe_for_exec_resume.txt",
        "scan_resume_initial_atlasvibe.txt": temp_dir / "scan_resume_initial_atlasvibe.txt",
        "scan_resume_new_atlasvibe_folder": temp_dir / "scan_resume_new_atlasvibe_folder",
        "scan_resume_new_file_atlasvibe.txt": temp_dir / "scan_resume_new_atlasvibe_folder" / "scan_resume_new_file_atlasvibe.txt",
    }
    exp_paths_complex_map = {
        "diacritic_folder_replaced": temp_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL", 
        "file_in_diacritic_folder_replaced_name": temp_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.txt", 
        "file_with_spaces_replaced_name": temp_dir / "The control characters \n will be ignored_VAL.md",
        "my_love_story_replaced_name": temp_dir / "_My_Story&Love_VAL.log", 
        "my_love_story_dir_replaced": temp_dir / "_My_Story&Love_VAL_dir", 
        "coco4_replaced_name": temp_dir / "MOCO4_ip-N_VAL.data", 
        "special_chars_content_file": temp_dir / "special_chars_in_content_test.txt", 
        "file_with_control_chars_key_replaced_name": temp_dir / "Value_for_key_with_controls_VAL.txt" 
    }

    if is_complex_map_test:
        record_test("[Complex] Diacritic folder rename", exp_paths_complex_map["diacritic_folder_replaced"].exists(), f"Dir missing: {exp_paths_complex_map['diacritic_folder_replaced']}")
        record_test("[Complex] File in diacritic folder rename", exp_paths_complex_map["file_in_diacritic_folder_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['file_in_diacritic_folder_replaced_name']}")
        record_test("[Complex] File with spaces in name rename (value has newline)", exp_paths_complex_map["file_with_spaces_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['file_with_spaces_replaced_name']}")
        record_test("[Complex] File with '&' in name rename", exp_paths_complex_map["my_love_story_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['my_love_story_replaced_name']}")
        record_test("[Complex] File with '-' and mixed case in name rename", exp_paths_complex_map["coco4_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['coco4_replaced_name']}")
        record_test("[Complex] File for special chars in content (name unchanged)", exp_paths_complex_map["special_chars_content_file"].exists(), f"File missing: {exp_paths_complex_map['special_chars_content_file']}")
        record_test("[Complex] File with control chars in key rename", exp_paths_complex_map["file_with_control_chars_key_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['file_with_control_chars_key_replaced_name']}")
        record_test("[Complex] Original diacritic folder removed", not (temp_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS").exists(), "Original diacritic folder still exists.")

    elif not is_exec_resume_run and not is_scan_resume_run: 
        record_test("Top-level dir rename", exp_paths_std_map["atlasvibe_root"].exists(), f"Dir missing: {exp_paths_std_map['atlasvibe_root']}")
        record_test("Original top-level dir removed", not (temp_dir / "flojoy_root").exists(), "Old 'flojoy_root' dir STILL EXISTS.")

    if is_complex_map_test:
        check_file_content_for_test(exp_paths_complex_map.get("file_in_diacritic_folder_replaced_name"),
                           "Content with dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL and also dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.\nAnd another Flojoy for good measure (should remain if not in complex map).", 
                           "[Complex] Diacritic key replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("file_with_spaces_replaced_name"),
                           "This file has The control characters \n will be ignored_VAL in its name and content.",
                           "[Complex] Key with spaces, value with newline replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("my_love_story_replaced_name"),
                           "Log for _My_Story&Love_VAL and _my_story&love_VAL.",
                           "[Complex] Key with '&' and case variants replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("coco4_replaced_name"),
                           "Data for MOCO4_ip-N_VAL and Moco4_ip-N_VAL.",
                           "[Complex] Key with '-' and mixed case replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("special_chars_content_file"),
                           "This line contains SpecialCharsKeyMatched_VAL to be replaced.",
                           "[Complex] Special chars key replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("file_with_control_chars_key_replaced_name"),
                           "Content for Value_for_key_with_controls_VAL here.", 
                           "[Complex] Key with control chars replacement in content.", record_test_func=record_test)


    elif not is_exec_resume_run and not is_scan_resume_run: 
        check_file_content_for_test(exp_paths_std_map.get("deep_atlasvibe_file.txt"),
                           "Line 1: atlasvibe content.\nLine 2: More Atlasvibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project.",
                           "Content replacement (deeply nested, mixed case, Test #16 target)", record_test_func=record_test)
    
    term_width, _ = shutil.get_terminal_size(fallback=(100, 24)) 
    padding = 1
    id_col_content_width = len(str(test_counter)) if test_counter > 0 else 3
    id_col_total_width = id_col_content_width + 2 * padding
    outcome_text_pass = f"{PASS_SYMBOL} PASS"
    outcome_text_fail = f"{FAIL_SYMBOL} FAIL"
    outcome_col_content_width = max(len(outcome_text_pass), len(outcome_text_fail))
    outcome_col_total_width = outcome_col_content_width + 2 * padding
    desc_col_total_width = term_width - (id_col_total_width + outcome_col_total_width + 4) 
    min_desc_col_content_width = 30 
    if desc_col_total_width - 2 * padding < min_desc_col_content_width:
        desc_col_content_width = min_desc_col_content_width
    else:
        desc_col_content_width = desc_col_total_width - 2 * padding
    header_id = f"{'#':^{id_col_content_width}}"
    header_desc = f"{'Test Description':^{desc_col_content_width}}"
    header_outcome = f"{'Outcome':^{outcome_col_content_width}}"
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
        wrapped_desc_lines = textwrap.wrap(result['description'], width=desc_col_content_width, drop_whitespace=False, replace_whitespace=False)
        if not wrapped_desc_lines:
            wrapped_desc_lines = ['']
        for i, line_frag in enumerate(wrapped_desc_lines):
            id_cell_str = f"{' ' * padding}{id_text_content:>{id_col_content_width}}{' ' * padding}" if i == 0 else ' ' * (id_col_total_width)
            outcome_cell_str = f"{' ' * padding}{color}{outcome_text_content:<{outcome_col_content_width}}{RESET}{' ' * padding}" if i == 0 else ' ' * (outcome_col_total_width)
            desc_cell_str = f"{' ' * padding}{line_frag:<{desc_col_content_width}}{' ' * padding}"
            sys.stdout.write(BLUE + DBL_VERTICAL + RESET + id_cell_str + BLUE + DBL_VERTICAL + RESET + desc_cell_str + BLUE + DBL_VERTICAL + RESET + outcome_cell_str + BLUE + DBL_VERTICAL + RESET + "\n")
        if result["status"] == "FAIL" and result["details"]:
            failed_test_details_print_buffer.append(RED + f"\nDetails for Test #{result['id']}: {result['description']}" + RESET)
            for detail_line in result["details"].split('\n'):
                failed_test_details_print_buffer.append(RED + f"  -> {detail_line}" + RESET)
    sys.stdout.write(BLUE + DBL_BOTTOM_LEFT + DBL_HORIZONTAL * id_col_total_width + DBL_T_UP + DBL_HORIZONTAL * desc_col_total_width + DBL_T_UP + DBL_HORIZONTAL * outcome_col_total_width + DBL_BOTTOM_RIGHT + RESET + "\n")
    if failed_test_details_print_buffer:
        sys.stdout.write("\n" + RED + "--- Failure Details ---" + RESET + "\n") 
        for line in failed_test_details_print_buffer:
            sys.stdout.write(line + "\n")
    sys.stdout.write(YELLOW + "\n--- Self-Test Summary ---" + RESET + "\n")
    total_tests_run = passed_checks + failed_checks
    if total_tests_run > 0:
        percentage_passed = (passed_checks / total_tests_run) * 100
        summary_color = GREEN if failed_checks == 0 else RED
        summary_emoji = PASS_SYMBOL if failed_checks == 0 else FAIL_SYMBOL
        sys.stdout.write(f"Total Tests Run: {total_tests_run}\nPassed: {GREEN}{passed_checks}{RESET}\nFailed: {RED if failed_checks > 0 else GREEN}{failed_checks}{RESET}\nSuccess Rate: {summary_color}{percentage_passed:.2f}% {summary_emoji}{RESET}\n")
        if failed_checks == 0:
            sys.stdout.write(GREEN + "All self-test checks passed successfully! " + PASS_SYMBOL + RESET + "\n")
        else:
            sys.stdout.write(RED + f"Self-test FAILED with {failed_checks} error(s). " + FAIL_SYMBOL + RESET + "\n")
    else:
        sys.stdout.write(YELLOW + "No self-test checks were recorded." + RESET + "\n")
    sys.stdout.flush()
    if failed_checks > 0:
        raise AssertionError(f"Self-test failed with {failed_checks} assertion(s). Review output for details.")
    return True


@flow(name="Self-Test Flow", log_prints=True)
def self_test_flow(
    temp_dir_str: str,
    dry_run_for_test: bool,
    run_exec_resume_sub_test: bool = False,
    run_scan_resume_sub_test: bool = False,
    run_complex_map_sub_test: bool = False 
) -> None:
    temp_dir = Path(temp_dir_str)
    
    current_mapping_file_for_test: Path
    if run_complex_map_sub_test:
        current_mapping_file_for_test = temp_dir / SELF_TEST_COMPLEX_MAP_FILE
        complex_map_data = { 
            "REPLACEMENT_MAPPING": {
                "ȕsele̮Ss_diá͡cRiti̅cS": "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL",
                "The spaces will not be ignored": "The control characters \n will be ignored_VAL",
                "key_with\tcontrol\nchars": "Value_for_key_with_controls_VAL", 
                "_My_Love&Story": "_My_Story&Love_VAL",
                "_my_love&story": "_my_story&love_VAL", 
                "COCO4_ep-m": "MOCO4_ip-N_VAL",
                "Coco4_ep-M" : "Moco4_ip-N_VAL",
                "characters|not<allowed^in*paths::will\\/be!escaped%when?searched~in$filenames@and\"foldernames": "SpecialCharsKeyMatched_VAL"
            }
        }
        with open(current_mapping_file_for_test, 'w', encoding='utf-8') as f:
            json.dump(complex_map_data, f, indent=2)
        print(f"Self-Test (Complex Map): Created complex mapping file at {current_mapping_file_for_test}")
    else: 
        current_mapping_file_for_test = temp_dir / DEFAULT_REPLACEMENT_MAPPING_FILE
        default_map_data = { 
            "REPLACEMENT_MAPPING": {
                "flojoy": "atlasvibe", "Flojoy": "Atlasvibe", "floJoy": "atlasVibe",
                "FloJoy": "AtlasVibe", "FLOJOY": "ATLASVIBE"
            }
        }
        with open(current_mapping_file_for_test, 'w', encoding='utf-8') as f:
            json.dump(default_map_data, f, indent=2)

    load_success = replace_logic.load_replacement_map(current_mapping_file_for_test)
    if not load_success:
        raise RuntimeError(f"Self-Test FATAL: Could not load replacement map {current_mapping_file_for_test} for test run.")
    print(f"Self-Test: Successfully loaded replacement map from {current_mapping_file_for_test} into replace_logic.")

    _create_self_test_environment(temp_dir, use_complex_map=run_complex_map_sub_test)

    test_excluded_dirs: List[str] = ["excluded_flojoy_dir"] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt", current_mapping_file_for_test.name] 
    test_extensions = [".txt", ".py", ".md", ".bin", ".log", ".data"] 

    transaction_file: Path
    validation_file: Optional[Path] = None 

    if run_complex_map_sub_test:
        print("Self-Test: Executing Complex Map Test Scenario...")
        transaction_file = temp_dir / "complex_map_transactions.json"
        validation_file = temp_dir / "complex_map_validation_transactions.json" 
    else: 
        print("Self-Test: Executing Standard Test Scenario...")
        transaction_file = temp_dir / SELF_TEST_PRIMARY_TRANSACTION_FILE
        validation_file = temp_dir / SELF_TEST_SCAN_VALIDATION_FILE 
    
    transactions1 = scan_directory_for_occurrences(
        root_dir=temp_dir,
        excluded_dirs=test_excluded_dirs,
        excluded_files=test_excluded_files,
        file_extensions=test_extensions,
    )
    save_transactions(transactions1, transaction_file)
    print(f"Self-Test: First scan complete. {len(transactions1)} transactions planned in {transaction_file}.")

    if validation_file:
        transactions2 = scan_directory_for_occurrences(
            root_dir=temp_dir,
            excluded_dirs=test_excluded_dirs,
            excluded_files=test_excluded_files,
            file_extensions=test_extensions
        )
        save_transactions(transactions2, validation_file)
        print(f"Self-Test: Second scan (for validation) complete. {len(transactions2)} transactions planned in {validation_file}.")

    if not dry_run_for_test:
        print(f"Self-Test: Executing transactions from {transaction_file} (Dry Run = False)...")
        execute_all_transactions(
            transactions_file_path=transaction_file,
            root_dir=temp_dir,
            dry_run=False,
            resume=False 
        )
        print("Self-Test: Execution phase complete.")
    else:
        print(f"Self-Test: Dry run. Simulating execution from {transaction_file}.")
        execute_all_transactions(transaction_file, temp_dir, dry_run=True, resume=False)

    _verify_self_test_results_task(
        temp_dir=temp_dir,
        original_transaction_file=transaction_file,
        validation_transaction_file=validation_file, 
        is_exec_resume_run=run_exec_resume_sub_test, 
        is_scan_resume_run=run_scan_resume_sub_test,
        is_complex_map_test=run_complex_map_sub_test 
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
    force_execution: bool
):
    root_dir = Path(directory).resolve()
    if not root_dir.is_dir():
        sys.stderr.write(f"Error: Root directory '{root_dir}' does not exist or is not a directory.\n")
        return

    mapping_file_path = Path(mapping_file).resolve()
    if not replace_logic.load_replacement_map(mapping_file_path):
        sys.stderr.write(f"Aborting due to issues with replacement mapping file: {mapping_file_path}\n")
        return
    
    if not replace_logic._MAPPING_LOADED: 
        sys.stderr.write(f"Critical Error: Replacement map from {mapping_file_path} was not loaded successfully.\n")
        return
    if not replace_logic._COMPILED_PATTERN and bool(replace_logic._REPLACEMENT_MAPPING_CONFIG):
        sys.stderr.write("Critical Error: Replacement map loaded but regex pattern compilation failed.\n")
        return
    if not replace_logic._REPLACEMENT_MAPPING_CONFIG: 
        print(f"Warning: The replacement mapping from {mapping_file_path} is empty. No replacements will be made.")

    transaction_json_path = root_dir / MAIN_TRANSACTION_FILE_NAME
    
    if not dry_run and not force_execution and not resume:
        sys.stdout.write("--- Proposed Operation ---\n")
        sys.stdout.write(f"Root Directory: {root_dir}\n")
        sys.stdout.write(f"Replacement Map File: {mapping_file_path}\n")
        if replace_logic._REPLACEMENT_MAPPING_CONFIG:
             sys.stdout.write(f"Loaded {len(replace_logic._REPLACEMENT_MAPPING_CONFIG)} replacement rules.\n")
        else:
             sys.stdout.write("Replacement map is empty. No string replacements will occur.\n")
        sys.stdout.write(f"File Extensions for content scan: {extensions if extensions else 'All non-binary (heuristic)'}\n")
        sys.stdout.write(f"Exclude Dirs: {exclude_dirs}\n")
        sys.stdout.write(f"Exclude Files: {exclude_files}\n")
        sys.stdout.write("-------------------------\n")
        sys.stdout.flush()
        if not replace_logic._REPLACEMENT_MAPPING_CONFIG and not extensions: 
            print("No replacement rules loaded and no specific extensions to process. Likely no operations will be performed.")
        
        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes':
            sys.stdout.write("Operation cancelled by user.\n")
            return

    if not skip_scan:
        print(f"Starting scan phase in '{root_dir}' using map '{mapping_file_path}'...")
        current_transactions = None
        if resume:
            if transaction_json_path.exists():
                print(f"Resuming scan, loading existing transactions from {transaction_json_path}...")
                current_transactions = load_transactions(transaction_json_path)
                if current_transactions is None:
                     print(f"{YELLOW}Warning: Could not load transactions from {transaction_json_path} for resume. Starting fresh scan.{RESET}")
            else:
                print(f"Resume requested but {transaction_json_path} not found. Starting fresh scan.")

        found_transactions = scan_directory_for_occurrences(
            root_dir=root_dir,
            excluded_dirs=exclude_dirs,
            excluded_files=exclude_files,
            file_extensions=extensions,
            resume_from_transactions=current_transactions
        )
        save_transactions(found_transactions, transaction_json_path)
        print(f"Scan complete. {len(found_transactions)} transactions planned in '{transaction_json_path}'")
        if not found_transactions:
            print("No occurrences found matching the replacement map. Nothing to do.")
            return
    elif not transaction_json_path.exists():
        print(f"Error: --skip-scan was used, but '{transaction_json_path}' not found.")
        return
    else:
        print(f"Using existing transaction file: '{transaction_json_path}'. Ensure it was generated with the correct replacement map.")

    if dry_run:
        print("Dry run: Simulating execution of transactions...")
        stats = execute_all_transactions(
            transactions_file_path=transaction_json_path,
            root_dir=root_dir,
            dry_run=True,
            resume=resume 
        )
        print(f"Dry run complete. Simulated stats: {stats}")
    else:
        print("Starting execution phase...")
        stats = execute_all_transactions(
            transactions_file_path=transaction_json_path,
            root_dir=root_dir,
            dry_run=False,
            resume=resume
        )
        print(f"Execution phase complete. Stats: {stats}")
    print(f"Review '{transaction_json_path}' for a log of changes and their statuses.")


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
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and plan changes, but do not execute them. Reports what would be changed.")
    parser.add_argument("--skip-scan", action="store_true",
                        help=f"Skip scan phase; use existing '{MAIN_TRANSACTION_FILE_NAME}' in the root directory.")
    parser.add_argument("--resume", action="store_true",
                        help="Resume operation from existing transaction file, attempting to complete pending/failed items and scan for new ones.")
    parser.add_argument("--force", "--yes", "-y", action="store_true",
                        help="Force execution without confirmation prompt (use with caution).")
    
    self_test_group = parser.add_argument_group('Self-Test Options')
    self_test_group.add_argument("--self-test", dest="run_standard_self_test", action="store_true",
                                 help=f"Run the standard self-test suite in '{SELF_TEST_SANDBOX_DIR}'. Uses default mappings.")
    self_test_group.add_argument("--self-test-complex-map", dest="run_complex_map_self_test", action="store_true",
                                 help=f"Run the self-test suite with a complex mapping scenario in '{SELF_TEST_SANDBOX_DIR}'.")

    args = parser.parse_args()

    if args.run_standard_self_test or args.run_complex_map_self_test:
        is_complex_run = args.run_complex_map_self_test
        test_type_msg = "Complex Map" if is_complex_run else "Standard"
        
        sys.stdout.write(f"Running self-test ({test_type_msg} scenario) in sandbox: '{SELF_TEST_SANDBOX_DIR}'...\n")
        
        self_test_sandbox = Path(SELF_TEST_SANDBOX_DIR).resolve()
        if self_test_sandbox.exists():
            print(f"Removing existing self-test sandbox: {self_test_sandbox}")
            shutil.rmtree(self_test_sandbox)
        self_test_sandbox.mkdir(parents=True, exist_ok=True)
        print(f"Created self-test sandbox: {self_test_sandbox}")
        
        try:
            self_test_flow(
                temp_dir_str=str(self_test_sandbox),
                dry_run_for_test=args.dry_run, 
                run_complex_map_sub_test=is_complex_run
            )
        except AssertionError as e: 
            sys.stderr.write(RED + f"Self-test ({test_type_msg}) FAILED assertions." + RESET + "\n")
            sys.exit(1) 
        except Exception as e:
            sys.stderr.write(RED + f"Self-test ({test_type_msg}) encountered an unexpected ERROR: {e} " + FAIL_SYMBOL + RESET + "\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
        finally:
            if self_test_sandbox.exists():
                try:
                    shutil.rmtree(self_test_sandbox)
                    print(f"Cleaned up self-test sandbox: {self_test_sandbox}")
                except Exception as e: 
                    print(f"{YELLOW}Warning: Could not remove self-test sandbox {self_test_sandbox}: {e}{RESET}")
        return 

    auto_excluded_files = [MAIN_TRANSACTION_FILE_NAME, Path(args.mapping_file).name]
    auto_excluded_files.append(MAIN_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT)
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
        force_execution=args.force
    )

if __name__ == "__main__":
    try:
        missing_deps = []
        try:
            import prefect
        except ImportError:
            missing_deps.append("prefect") 
        try:
            import chardet
        except ImportError:
            missing_deps.append("chardet") 

        if missing_deps: 
             raise ImportError(f"Missing dependencies: {', '.join(missing_deps)}")
        main_cli()
    except ImportError as e: 
        sys.stderr.write(f"CRITICAL ERROR: {e}.\nPlease ensure dependencies are installed (e.g., pip install -r requirements.txt).\n")
        sys.exit(1)
    except Exception as e: 
        sys.stderr.write(RED + f"An unexpected error occurred: {e}" + RESET + "\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
