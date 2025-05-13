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
from typing import List, Dict, Any, Optional, Union, Callable 
import shutil 
import textwrap 
import json 
import os 
import operator 

from prefect import task, flow

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
    include_symlink_tests: bool = False
) -> None:
    """Creates a directory structure and files for self-testing."""
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
            "This has fLoJoY content, and also flojoy." 
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
        for i in range(1000): 
            if i % 50 == 0:
                large_file_content_list.append("This flojoy line should be replaced " + str(i) + "\n")
            else:
                large_file_content_list.append("Normal line " + str(i) + "\n")
        (base_dir / "large_flojoy_file.txt").write_text("".join(large_file_content_list), encoding='utf-8')
        (base_dir / SELF_TEST_ERROR_FILE_BASENAME).write_text("This file will cause a rename error during tests.")

    if include_very_large_file:
        print(f"Generating very large file: {VERY_LARGE_FILE_NAME_ORIG}...")
        with open(base_dir / VERY_LARGE_FILE_NAME_ORIG, 'w', encoding='utf-8') as f:
            for i in range(VERY_LARGE_FILE_LINES):
                if i == 0 or i == VERY_LARGE_FILE_LINES // 2 or i == VERY_LARGE_FILE_LINES - 1 or \
                   i % VERY_LARGE_FILE_MATCH_INTERVAL == 0:
                    f.write(f"Line {i+1}: This is a flojoy line that should be replaced.\n")
                else:
                    f.write(f"Line {i+1}: This is a standard non-matching line with some padding to make it longer.\n")
        print("Very large file generated.")

    if include_precision_test_file:
        precision_content_lines = [
            "Standard flojoy here.\n",                 
            "Another Flojoy for title case.\r\n",      
            "Test FLÖJOY_DIACRITIC with mixed case.\n",
            "  flojoy  with exact spaces.\n",          
            "  flojoy   with extra spaces.\n",         
            "key\twith\ncontrol characters.\n",        
            "unrelated content\n",
            "你好flojoy世界 (Chinese chars).\n",       
            "emoji😊flojoy test.\n",                  
        ]
        problematic_bytes_line = b"malformed-\xff-flojoy-bytes\n" 
        
        with open(base_dir / "precision_test_flojoy_source.txt", "wb") as f: 
            for line_str in precision_content_lines:
                f.write(line_str.encode('utf-8', errors='surrogateescape')) 
            f.write(problematic_bytes_line)
        
        (base_dir / "precision_name_flojoy_test.md").write_text("File for precision rename test.")


    if use_complex_map:
        (base_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS").mkdir(parents=True, exist_ok=True)
        (base_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS" / "file_with_diacritics_ȕsele̮Ss_diá͡cRiti̅cS.txt").write_text(
            "Content with ȕsele̮Ss_diá͡cRiti̅cS and also useless_diacritics.\nAnd another Flojoy for good measure (should remain if not in complex map)."
        )
        (base_dir / "file_with_spaces_The spaces will not be ignored.md").write_text(
            "This file has The spaces will not be ignored in its name and content."
        )
        (base_dir / "_My_Love&Story.log").write_text("Log for _My_Love&Story and _my_love&story. And My_Love&Story.")
        (base_dir / "filename_with_COCO4_ep-m.data").write_text("Data for COCO4_ep-m and Coco4_ep-M. Also coco4_ep-m.")
        (base_dir / "special_chars_in_content_test.txt").write_text(
            "This line contains characters|not<allowed^in*paths::will/be!escaped%when?searched~in$filenames@and\"foldernames to be replaced."
        )
        (base_dir / "complex_map_key_withcontrolchars_original_name.txt").write_text( 
            "Content for complex map control key filename test."
        )
        (base_dir / "complex_map_content_with_key_with_controls.txt").write_text(
             "Line with key_with\tcontrol\nchars to replace."
        )

    if use_edge_case_map:
        (base_dir / "edge_case_MyKey_original_name.txt").write_text("Initial content for control key name test (MyKey).")
        (base_dir / "edge_case_content_with_MyKey_controls.txt").write_text("Line with My\nKey to replace.")
        (base_dir / "edge_case_empty_stripped_key_target.txt").write_text("This should not be changed by an empty key.")
        (base_dir / "edge_case_key_priority.txt").write_text("test foo bar test and also foo.")

    if for_resume_test_phase_2:
        (base_dir / "newly_added_flojoy_for_resume.txt").write_text("This flojoy content is new for resume.")
        if (base_dir / "only_name_atlasvibe.md").exists(): 
             (base_dir / "only_name_atlasvibe.md").write_text("Content without target string, but now with flojoy.")
    
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
            print("Symlinks created (or already existed) for testing.")
        except OSError as e:
            print(f"{YELLOW}Warning: Could not create symlinks for testing (OSError: {e}). Symlink tests may be skipped or fail.{RESET}")
        except Exception as e: 
            print(f"{YELLOW}Warning: An unexpected error occurred creating symlinks: {e}. Symlink tests may be affected.{RESET}")


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
    is_complex_map_test: bool = False,
    is_edge_case_test: bool = False,
    is_empty_map_test: bool = False,
    is_resume_test: bool = False, 
    standard_test_includes_large_file: bool = False,
    is_precision_test: bool = False,
    standard_test_includes_symlinks: bool = False,
    symlinks_were_ignored_in_scan: bool = False 
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

    if is_empty_map_test:
        transactions = load_transactions(original_transaction_file)
        record_test("[Empty Map] No transactions generated", transactions is not None and len(transactions) == 0, f"Expected 0 transactions, got {len(transactions) if transactions else 'None'}")
    
    elif is_precision_test:
        precision_source_orig_name = "precision_test_flojoy_source.txt"
        precision_source_renamed_name = "precision_test_atlasvibe_plain_source.txt" 
        
        precision_renamed_path = temp_dir / precision_source_renamed_name
        
        record_test("[Precision Test] Filename 'precision_test_flojoy_source.txt' renamed", precision_renamed_path.exists())
        record_test("[Precision Test] Original filename 'precision_test_flojoy_source.txt' removed", not (temp_dir / precision_source_orig_name).exists())

        precision_name_orig = "precision_name_flojoy_test.md"
        precision_name_renamed = "precision_name_atlasvibe_plain_test.md" 
        record_test("[Precision Test] Filename 'precision_name_flojoy_test.md' renamed", (temp_dir / precision_name_renamed).exists())
        record_test("[Precision Test] Original filename 'precision_name_flojoy_test.md' removed", not (temp_dir / precision_name_orig).exists())


        if precision_renamed_path.exists():
            original_content_bytes_list = []
            _orig_precision_content_lines = [
                "Standard flojoy here.\n",
                "Another Flojoy for title case.\r\n",
                "Test FLÖJOY_DIACRITIC with mixed case.\n",
                "  flojoy  with exact spaces.\n",
                "  flojoy   with extra spaces.\n",
                "key\twith\ncontrol characters.\n",
                "unrelated content\n",
                "你好flojoy世界 (Chinese chars).\n",
                "emoji😊flojoy test.\n",
            ]
            _orig_problematic_bytes_line = b"malformed-\xff-flojoy-bytes\n" 
            for line_str in _orig_precision_content_lines:
                original_content_bytes_list.append(line_str.encode('utf-8', errors='surrogateescape'))
            original_content_bytes_list.append(_orig_problematic_bytes_line)

            actual_lines_bytes = precision_renamed_path.read_bytes().splitlines(keepends=True)
            
            record_test(f"[Precision Test] Line count check", len(actual_lines_bytes) == len(original_content_bytes_list), f"Expected {len(original_content_bytes_list)} lines, got {len(actual_lines_bytes)}")

            for i, original_line_bytes in enumerate(original_content_bytes_list):
                if i < len(actual_lines_bytes):
                    actual_line_bytes_from_file = actual_lines_bytes[i]
                    
                    original_line_str_for_processing = original_line_bytes.decode('utf-8', errors='surrogateescape')
                    expected_processed_line_str = replace_logic.replace_occurrences(original_line_str_for_processing)
                    expected_processed_line_bytes = expected_processed_line_str.encode('utf-8', errors='surrogateescape')
                    
                    record_test(f"[Precision Test] Line {i+1} byte-for-byte content", actual_line_bytes_from_file == expected_processed_line_bytes, f"Line {i+1}:\nExpected: {expected_processed_line_bytes!r}\nActual:   {actual_line_bytes_from_file!r}")
                else:
                    record_test(f"[Precision Test] Line {i+1} missing in actual output", False)


    elif is_resume_test:
        final_transactions = load_transactions(original_transaction_file)
        record_test("[Resume Test] Final transaction log loaded", final_transactions is not None)
        if final_transactions:
            new_file_processed = any(
                tx["PATH"] == "newly_added_flojoy_for_resume.txt" and tx["STATUS"] == TransactionStatus.COMPLETED.value
                for tx in final_transactions if tx["TYPE"] == TransactionType.FILE_NAME.value
            )
            new_file_content_processed = any(
                tx["PATH"] == "newly_added_flojoy_for_resume.txt" and tx["STATUS"] == TransactionStatus.COMPLETED.value
                for tx in final_transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value
            )
            record_test("[Resume Test] Newly added file name processed", new_file_processed)
            record_test("[Resume Test] Newly added file content processed", new_file_content_processed)
            check_file_content_for_test(temp_dir / "newly_added_atlasvibe_for_resume.txt", 
                                   "This atlasvibe content is new for resume.",
                                   "[Resume Test] Content of newly added file after resume", record_test_func=record_test)

            large_file_tx_found_completed = any(
                "large_flojoy_file.txt" in tx["PATH"] and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and tx["STATUS"] == TransactionStatus.COMPLETED.value
                for tx in final_transactions
            )
            record_test("[Resume Test] Initially PENDING content transaction completed", large_file_tx_found_completed)
            
            error_file_tx_status = ""
            for tx in final_transactions:
                if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME and tx["TYPE"] == TransactionType.FILE_NAME.value:
                    error_file_tx_status = tx["STATUS"]
                    break
            record_test("[Resume Test] Error file transaction re-attempted and FAILED again", error_file_tx_status == TransactionStatus.FAILED.value)
            record_test("[Resume Test] Original error file still exists after failed resume attempt", (temp_dir / SELF_TEST_ERROR_FILE_BASENAME).exists())

    elif is_edge_case_test:
        exp_edge_paths = {
            "control_key_renamed_file": temp_dir / "MyKeyValue_VAL.txt", 
            "control_key_content_file": temp_dir / "edge_case_content_with_MyKey_controls.txt", 
            "empty_stripped_key_file": temp_dir / "edge_case_empty_stripped_key_target.txt", 
            "key_priority_file": temp_dir / "edge_case_key_priority.txt" 
        }
        record_test("[Edge Case] Control char key ('My\\nKey') - filename rename", exp_edge_paths["control_key_renamed_file"].exists(), f"File missing: {exp_edge_paths['control_key_renamed_file']}")
        check_file_content_for_test(exp_edge_paths["control_key_content_file"],
                               "Line with MyKeyValue_VAL to replace.",
                               "[Edge Case] Control char key ('My\\nKey') - content replacement", record_test_func=record_test)
        
        check_file_content_for_test(exp_edge_paths["empty_stripped_key_file"],
                               "This should not be changed by an empty key.",
                               "[Edge Case] Empty stripped key ('\\t') - content unchanged", record_test_func=record_test)

        check_file_content_for_test(exp_edge_paths["key_priority_file"],
                               "test FooBar_VAL test and also Foo_VAL.", 
                               "[Edge Case] Key priority ('foo bar' vs 'foo')", record_test_func=record_test)

    elif is_complex_map_test:
        exp_paths_complex_map = {
            "diacritic_folder_replaced": temp_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL", 
            "file_in_diacritic_folder_replaced_name": temp_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.txt", 
            "file_with_spaces_replaced_name": temp_dir / "The control characters \n will be ignored_VAL.md",
            "my_love_story_replaced_name": temp_dir / "_My_Story&Love_VAL.log", 
            "coco4_replaced_name": temp_dir / "MOCO4_ip-N_VAL.data", 
            "special_chars_content_file": temp_dir / "special_chars_in_content_test.txt", 
            "control_chars_key_renamed_file": temp_dir / "Value_for_key_with_controls_VAL.txt", 
            "control_chars_key_content_file": temp_dir / "complex_map_content_with_key_with_controls.txt" 
        }
        record_test("[Complex] Diacritic folder rename", exp_paths_complex_map["diacritic_folder_replaced"].exists(), f"Dir missing: {exp_paths_complex_map['diacritic_folder_replaced']}")
        record_test("[Complex] File in diacritic folder rename", exp_paths_complex_map["file_in_diacritic_folder_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['file_in_diacritic_folder_replaced_name']}")
        record_test("[Complex] File with spaces in name rename (value has newline)", exp_paths_complex_map["file_with_spaces_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['file_with_spaces_replaced_name']}")
        record_test("[Complex] File with '&' in name rename", exp_paths_complex_map["my_love_story_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['my_love_story_replaced_name']}")
        record_test("[Complex] File with '-' and mixed case in name rename", exp_paths_complex_map["coco4_replaced_name"].exists(), f"File missing: {exp_paths_complex_map['coco4_replaced_name']}")
        record_test("[Complex] File for special chars in content (name unchanged)", exp_paths_complex_map["special_chars_content_file"].exists(), f"File missing: {exp_paths_complex_map['special_chars_content_file']}")
        record_test("[Complex] Control char key ('key_with\\tcontrol\\nchars') - filename rename", exp_paths_complex_map["control_chars_key_renamed_file"].exists(), f"File missing: {exp_paths_complex_map['control_chars_key_renamed_file']}")
        record_test("[Complex] Original diacritic folder removed", not (temp_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS").exists(), "Original diacritic folder still exists.")
        
        check_file_content_for_test(exp_paths_complex_map.get("file_in_diacritic_folder_replaced_name"),
                           "Content with dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL and also dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.\nAnd another Flojoy for good measure (should remain if not in complex map).", 
                           "[Complex] Diacritic key replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("file_with_spaces_replaced_name"),
                           "This file has The control characters \n will be ignored_VAL in its name and content.",
                           "[Complex] Key with spaces, value with newline replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("my_love_story_replaced_name"),
                           "Log for _My_Story&Love_VAL and _my_story&love_VAL. And My_Love&Story.", 
                           "[Complex] Key with '&' and case variants replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("coco4_replaced_name"),
                           "Data for MOCO4_ip-N_VAL and Moco4_ip-N_VAL. Also MOCO4_ip-N_VAL.", 
                           "[Complex] Key with '-' and mixed case replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("special_chars_content_file"),
                           "This line contains SpecialCharsKeyMatched_VAL to be replaced.",
                           "[Complex] Special chars key replacement in content.", record_test_func=record_test)
        check_file_content_for_test(exp_paths_complex_map.get("control_chars_key_content_file"), 
                           "Line with Value_for_key_with_controls_VAL to replace.", 
                           "[Complex] Key with control chars in key - content replacement", record_test_func=record_test)

    elif not is_exec_resume_run and not is_scan_resume_run: # Standard self-test run
        exp_paths_std_map = {
            "atlasvibe_root": temp_dir / "atlasvibe_root",
            "deep_atlasvibe_file.txt": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file.txt",
            "very_large_atlasvibe_file.txt": temp_dir / VERY_LARGE_FILE_NAME_REPLACED
        }
        record_test("Top-level dir rename", exp_paths_std_map["atlasvibe_root"].exists(), f"Dir missing: {exp_paths_std_map['atlasvibe_root']}")
        record_test("Original top-level dir removed", not (temp_dir / "flojoy_root").exists(), "Old 'flojoy_root' dir STILL EXISTS.")
        check_file_content_for_test(exp_paths_std_map.get("deep_atlasvibe_file.txt"),
                           "Line 1: atlasvibe content.\nLine 2: More Atlasvibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project.",
                           "Content replacement (deeply nested, mixed case, Test #16 target)", record_test_func=record_test)
        if standard_test_includes_large_file:
            record_test("[Standard Test] Very large file renamed", exp_paths_std_map["very_large_atlasvibe_file.txt"].exists())
            if exp_paths_std_map["very_large_atlasvibe_file.txt"].exists():
                with open(exp_paths_std_map["very_large_atlasvibe_file.txt"], 'r', encoding='utf-8') as f:
                    line_0 = f.readline().strip()
                    expected_line_0 = "Line 1: This is a atlasvibe line that should be replaced."
                    record_test("[Standard Test] Very large file - line 0 content", line_0 == expected_line_0, f"Expected: '{expected_line_0}', Got: '{line_0}'")
                    
                    for i in range(1, VERY_LARGE_FILE_LINES // 2): 
                        f.readline()
                    line_mid = f.readline().strip()
                    expected_line_mid = f"Line {VERY_LARGE_FILE_LINES // 2 + 1}: This is a atlasvibe line that should be replaced."
                    record_test("[Standard Test] Very large file - middle line content", line_mid == expected_line_mid, f"Expected: '{expected_line_mid}', Got: '{line_mid}'")
        
        if standard_test_includes_symlinks:
            link_file_orig = temp_dir / "link_to_file_flojoy.txt"
            link_dir_orig = temp_dir / "link_to_dir_flojoy"
            link_file_renamed_path = temp_dir / "link_to_file_atlasvibe.txt"
            link_dir_renamed_path = temp_dir / "link_to_dir_atlasvibe"
            
            if symlinks_were_ignored_in_scan:
                record_test("[Symlink Test - Ignored] Original file symlink exists", os.path.lexists(link_file_orig))
                record_test("[Symlink Test - Ignored] Renamed file symlink does NOT exist", not os.path.lexists(link_file_renamed_path))
                record_test("[Symlink Test - Ignored] Original dir symlink exists", os.path.lexists(link_dir_orig))
                record_test("[Symlink Test - Ignored] Renamed dir symlink does NOT exist", not os.path.lexists(link_dir_renamed_path))
            else:
                record_test("[Symlink Test - Processed] Renamed file symlink exists", os.path.lexists(link_file_renamed_path))
                if os.path.lexists(link_file_renamed_path):
                    record_test("[Symlink Test - Processed] Renamed file symlink is a symlink", link_file_renamed_path.is_symlink())
                
                record_test("[Symlink Test - Processed] Renamed dir symlink exists", os.path.lexists(link_dir_renamed_path))
                if os.path.lexists(link_dir_renamed_path):
                    record_test("[Symlink Test - Processed] Renamed dir symlink is a symlink", link_dir_renamed_path.is_symlink())

            target_file = temp_dir / "symlink_targets_outside" / "target_file_flojoy.txt"
            target_dir_file = temp_dir / "symlink_targets_outside" / "target_dir_flojoy" / "another_flojoy_file.txt"
            check_file_content_for_test(target_file, "flojoy in symlink target file", "[Symlink Test] Target file content unchanged (regardless of ignore flag)", record_test_func=record_test)
            check_file_content_for_test(target_dir_file, "flojoy content in symlinked dir target", "[Symlink Test] Target dir file content unchanged (regardless of ignore flag)", record_test_func=record_test)


    # Common verification logic (table printing, summary)
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
    run_complex_map_sub_test: bool = False,
    run_edge_case_sub_test: bool = False,
    run_empty_map_sub_test: bool = False,
    run_resume_test: bool = False,
    run_precision_test: bool = False,
    ignore_symlinks_for_this_test_run: bool = False 
) -> None:
    temp_dir = Path(temp_dir_str)
    
    current_mapping_file_for_test: Path
    test_scenario_name = "Standard"
    is_verification_resume_test = False
    is_verification_precision_test = False
    
    standard_test_includes_large_file = not (
        run_complex_map_sub_test or run_edge_case_sub_test or 
        run_empty_map_sub_test or run_resume_test or run_precision_test
    )
    standard_test_includes_symlinks = standard_test_includes_large_file or run_precision_test or run_resume_test


    if run_complex_map_sub_test:
        test_scenario_name = "Complex Map"
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
    elif run_edge_case_sub_test:
        test_scenario_name = "Edge Case"
        current_mapping_file_for_test = temp_dir / SELF_TEST_EDGE_CASE_MAP_FILE
        edge_case_map_data = {
            "REPLACEMENT_MAPPING": {
                "My\nKey": "MyKeyValue_VAL", 
                "Key\nWith\tControls": "ControlValue_VAL", 
                "\t": "ShouldBeSkipped_VAL",             
                "foo": "Foo_VAL",
                "foo bar": "FooBar_VAL"                   
            }
        }
        with open(current_mapping_file_for_test, 'w', encoding='utf-8') as f:
            json.dump(edge_case_map_data, f, indent=2)
    elif run_empty_map_sub_test:
        test_scenario_name = "Empty Map"
        current_mapping_file_for_test = temp_dir / SELF_TEST_EMPTY_MAP_FILE
        empty_map_data = {"REPLACEMENT_MAPPING": {}}
        with open(current_mapping_file_for_test, 'w', encoding='utf-8') as f:
            json.dump(empty_map_data, f, indent=2)
    elif run_resume_test:
        test_scenario_name = "Resume"
        is_verification_resume_test = True 
        current_mapping_file_for_test = temp_dir / DEFAULT_REPLACEMENT_MAPPING_FILE 
        default_map_data = { 
            "REPLACEMENT_MAPPING": {
                "flojoy": "atlasvibe", "Flojoy": "Atlasvibe", "floJoy": "atlasVibe",
                "FloJoy": "AtlasVibe", "FLOJOY": "ATLASVIBE"
            }
        }
        with open(current_mapping_file_for_test, 'w', encoding='utf-8') as f:
            json.dump(default_map_data, f, indent=2)
    elif run_precision_test:
        test_scenario_name = "Precision"
        is_verification_precision_test = True
        current_mapping_file_for_test = temp_dir / SELF_TEST_PRECISION_MAP_FILE
        precision_map_data = {
            "REPLACEMENT_MAPPING": {
                "flojoy": "atlasvibe_plain",      
                "Flojoy": "Atlasvibe_TitleCase",  
                "FLÖJOY_DIACRITIC": "ATLASVIBE_DIACRITIC_VAL", 
                "  flojoy  ": "  atlasvibe_spaced_val  ", 
                "key\twith\ncontrol": "value_for_control_key_val" 
            }
        }
        with open(current_mapping_file_for_test, 'w', encoding='utf-8') as f:
            json.dump(precision_map_data, f, indent=2)
    else: # Standard test
        current_mapping_file_for_test = temp_dir / DEFAULT_REPLACEMENT_MAPPING_FILE
        default_map_data = { 
            "REPLACEMENT_MAPPING": {
                "flojoy": "atlasvibe", "Flojoy": "Atlasvibe", "floJoy": "atlasVibe",
                "FloJoy": "AtlasVibe", "FLOJOY": "ATLASVIBE"
            }
        }
        with open(current_mapping_file_for_test, 'w', encoding='utf-8') as f:
            json.dump(default_map_data, f, indent=2)
    
    print(f"Self-Test ({test_scenario_name}): Using mapping file {current_mapping_file_for_test.name}")

    load_success = replace_logic.load_replacement_map(current_mapping_file_for_test)
    if not load_success: 
        if run_empty_map_sub_test and not replace_logic._REPLACEMENT_MAPPING_CONFIG and replace_logic._COMPILED_PATTERN is None:
             print(f"Self-Test ({test_scenario_name}): Successfully loaded an empty map as expected.")
        else:
            raise RuntimeError(f"Self-Test FATAL: Could not load or process replacement map {current_mapping_file_for_test} for test run.")
    elif run_empty_map_sub_test and replace_logic._REPLACEMENT_MAPPING_CONFIG:
        raise RuntimeError(f"Self-Test FATAL: Expected empty map for {test_scenario_name}, but found rules.")

    print(f"Self-Test ({test_scenario_name}): Successfully initialized replacement map from {current_mapping_file_for_test}")

    _create_self_test_environment(
        temp_dir, 
        use_complex_map=run_complex_map_sub_test, 
        use_edge_case_map=run_edge_case_sub_test,
        include_very_large_file=standard_test_includes_large_file,
        include_precision_test_file=run_precision_test,
        include_symlink_tests=standard_test_includes_symlinks 
    )

    test_excluded_dirs: List[str] = ["excluded_flojoy_dir", "symlink_targets_outside"] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt", current_mapping_file_for_test.name] 
    test_extensions = [".txt", ".py", ".md", ".bin", ".log", ".data"] 

    transaction_file_name_base = "transactions"
    if run_complex_map_sub_test:
        transaction_file_name_base = "complex_map_transactions"
    elif run_edge_case_sub_test:
        transaction_file_name_base = "edge_case_transactions"
    elif run_empty_map_sub_test:
        transaction_file_name_base = "empty_map_transactions"
    elif run_resume_test:
        transaction_file_name_base = Path(SELF_TEST_RESUME_TRANSACTION_FILE).stem
    elif run_precision_test:
        transaction_file_name_base = "precision_test_transactions"
    else: # Standard test
        transaction_file_name_base = Path(SELF_TEST_PRIMARY_TRANSACTION_FILE).stem
        if ignore_symlinks_for_this_test_run: 
            transaction_file_name_base += "_ignore_symlinks"


    transaction_file = temp_dir / f"{transaction_file_name_base}.json"
    validation_file = temp_dir / f"{transaction_file_name_base}_validation.json" if not (run_empty_map_sub_test or run_resume_test or run_precision_test) else None
    
    if run_resume_test:
        print(f"Self-Test ({test_scenario_name}): Phase 1 - Initial scan and partial execution simulation...")
        initial_transactions = scan_directory_for_occurrences(
            temp_dir, 
            test_excluded_dirs, 
            test_excluded_files, 
            test_extensions,
            ignore_symlinks=False 
        )
        
        if initial_transactions:
            fn_tx_indices = [i for i, tx in enumerate(initial_transactions) if tx["TYPE"] == TransactionType.FILE_NAME.value]
            if fn_tx_indices:
                initial_transactions[fn_tx_indices[0]]["STATUS"] = TransactionStatus.COMPLETED.value
                if len(fn_tx_indices) > 1: 
                     initial_transactions[fn_tx_indices[1]]["STATUS"] = TransactionStatus.IN_PROGRESS.value
            
            for tx in initial_transactions:
                if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME and tx["TYPE"] == TransactionType.FILE_NAME.value:
                    tx["STATUS"] = TransactionStatus.FAILED.value
                    tx["ERROR_MESSAGE"] = "Simulated failure from initial run"
                    break
        
        save_transactions(initial_transactions, transaction_file) 
        print(f"Self-Test ({test_scenario_name}): Saved intermediate transaction file with {len(initial_transactions)} transactions.")
        
        print(f"Self-Test ({test_scenario_name}): Phase 2 - Modifying environment for resume scan...")
        _create_self_test_environment(temp_dir, for_resume_test_phase_2=True, include_symlink_tests=True) 

        print(f"Self-Test ({test_scenario_name}): Phase 3 - Running main_flow with --resume...")
        main_flow(
            directory=str(temp_dir),
            mapping_file=str(current_mapping_file_for_test),
            extensions=test_extensions,
            exclude_dirs=test_excluded_dirs,
            exclude_files=test_excluded_files,
            dry_run=dry_run_for_test, 
            skip_scan=False, 
            resume=True,     
            force_execution=True,
            ignore_symlinks_arg=ignore_symlinks_for_this_test_run 
        )
    else: 
        transactions1 = scan_directory_for_occurrences(
            root_dir=temp_dir,
            excluded_dirs=test_excluded_dirs,
            excluded_files=test_excluded_files,
            file_extensions=test_extensions,
            ignore_symlinks=ignore_symlinks_for_this_test_run 
        )
        save_transactions(transactions1, transaction_file)
        print(f"Self-Test ({test_scenario_name}): First scan complete. {len(transactions1)} transactions planned in {transaction_file}.")

        if run_empty_map_sub_test:
            if len(transactions1) != 0:
                raise AssertionError(f"[Empty Map Test] Expected 0 transactions, got {len(transactions1)}")
            print(f"Self-Test ({test_scenario_name}): Verified 0 transactions as expected.")
        elif validation_file: 
            transactions2 = scan_directory_for_occurrences(
                root_dir=temp_dir,
                excluded_dirs=test_excluded_dirs,
                excluded_files=test_excluded_files,
                file_extensions=test_extensions,
                ignore_symlinks=ignore_symlinks_for_this_test_run
            )
            save_transactions(transactions2, validation_file)
            print(f"Self-Test ({test_scenario_name}): Second scan (for validation) complete. {len(transactions2)} transactions planned in {validation_file}.")

        if not dry_run_for_test and not run_empty_map_sub_test: 
            print(f"Self-Test ({test_scenario_name}): Executing transactions from {transaction_file} (Dry Run = False)...")
            execute_all_transactions(
                transactions_file_path=transaction_file,
                root_dir=temp_dir,
                dry_run=False,
                resume=False 
            )
            print(f"Self-Test ({test_scenario_name}): Execution phase complete.")
        elif dry_run_for_test and not run_empty_map_sub_test:
            print(f"Self-Test ({test_scenario_name}): Dry run. Simulating execution from {transaction_file}.")
            execute_all_transactions(transaction_file, temp_dir, dry_run=True, resume=False)

    _verify_self_test_results_task(
        temp_dir=temp_dir,
        original_transaction_file=transaction_file, 
        validation_transaction_file=validation_file if not (run_resume_test or run_precision_test) else None, 
        is_complex_map_test=run_complex_map_sub_test,
        is_edge_case_test=run_edge_case_sub_test,
        is_empty_map_test=run_empty_map_sub_test,
        is_resume_test=is_verification_resume_test,
        standard_test_includes_large_file=standard_test_includes_large_file,
        is_precision_test=is_verification_precision_test,
        standard_test_includes_symlinks=standard_test_includes_symlinks,
        symlinks_were_ignored_in_scan=ignore_symlinks_for_this_test_run
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
        sys.stdout.write(f"Ignore Symlinks: {ignore_symlinks_arg}\n")
        sys.stdout.write("-------------------------\n")
        sys.stdout.flush()
        if not replace_logic._REPLACEMENT_MAPPING_CONFIG and not extensions: 
            print("No replacement rules loaded and no specific extensions to process. Likely no operations will be performed.")
        
        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes':
            sys.stdout.write("Operation cancelled by user.\n")
            return

    if not skip_scan:
        print(f"Starting scan phase in '{root_dir}' using map '{mapping_file_path}' (Ignore symlinks: {ignore_symlinks_arg})...")
        current_transactions_for_resume_scan = None
        if resume and transaction_json_path.exists(): 
            print(f"Resume mode: Loading existing transactions from {transaction_json_path} for scan augmentation...")
            current_transactions_for_resume_scan = load_transactions(transaction_json_path)
            if current_transactions_for_resume_scan is None:
                 print(f"{YELLOW}Warning: Could not load transactions from {transaction_json_path} for resume scan. Starting fresh scan.{RESET}")
        
        found_transactions = scan_directory_for_occurrences(
            root_dir=root_dir,
            excluded_dirs=exclude_dirs,
            excluded_files=exclude_files,
            file_extensions=extensions,
            ignore_symlinks=ignore_symlinks_arg, 
            resume_from_transactions=current_transactions_for_resume_scan 
        )
        save_transactions(found_transactions, transaction_json_path)
        print(f"Scan complete. {len(found_transactions)} transactions planned in '{transaction_json_path}'")
        if not found_transactions and replace_logic._REPLACEMENT_MAPPING_CONFIG: 
            print("No occurrences found matching the replacement map. Nothing to do.")
            return
        elif not found_transactions and not replace_logic._REPLACEMENT_MAPPING_CONFIG:
            print("Replacement map was empty, and no occurrences found (as expected).")
            return

    elif not transaction_json_path.exists():
        print(f"Error: --skip-scan was used, but '{transaction_json_path}' not found.")
        return
    else:
        print(f"Using existing transaction file: '{transaction_json_path}'. Ensure it was generated with the correct replacement map and symlink settings.")

    if not replace_logic._REPLACEMENT_MAPPING_CONFIG: 
        print("Map is empty. No execution will be performed.")
        return

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

    if args.run_standard_self_test or args.run_complex_map_self_test or \
       args.run_edge_case_self_test or args.run_empty_map_self_test or \
       args.run_resume_self_test or args.run_precision_self_test:
        
        is_complex_run = args.run_complex_map_self_test
        is_edge_case_run = args.run_edge_case_self_test
        is_empty_map_run = args.run_empty_map_self_test
        is_resume_run = args.run_resume_self_test
        is_precision_run = args.run_precision_self_test
        
        test_type_msg = "Standard"
        if is_complex_run:
            test_type_msg = "Complex Map"
        elif is_edge_case_run:
            test_type_msg = "Edge Cases"
        elif is_empty_map_run:
            test_type_msg = "Empty Map"
        elif is_resume_run:
            test_type_msg = "Resume Functionality"
        elif is_precision_run:
            test_type_msg = "Precision"
        
        sys.stdout.write(f"Running self-test ({test_type_msg} scenario) in sandbox: '{SELF_TEST_SANDBOX_DIR}'...\n")
        
        self_test_sandbox = Path(SELF_TEST_SANDBOX_DIR).resolve()
        if self_test_sandbox.exists():
            print(f"Removing existing self-test sandbox: {self_test_sandbox}")
            shutil.rmtree(self_test_sandbox)
        self_test_sandbox.mkdir(parents=True, exist_ok=True)
        print(f"Created self-test sandbox: {self_test_sandbox}")
        
        try:
            if args.run_standard_self_test:
                print("\nRunning Standard Self-Test (Processing Symlinks, ignore_symlinks=False)...")
                self_test_flow(
                    temp_dir_str=str(self_test_sandbox), dry_run_for_test=args.dry_run,
                    run_standard_self_test=True, 
                    ignore_symlinks_for_this_test_run=False 
                )
                if self_test_sandbox.exists(): # Re-create sandbox for the ignored symlink run
                    shutil.rmtree(self_test_sandbox)
                self_test_sandbox.mkdir(parents=True, exist_ok=True)
                print("\nRunning Standard Self-Test (Ignoring Symlinks, ignore_symlinks=True)...")
                self_test_flow(
                    temp_dir_str=str(self_test_sandbox), dry_run_for_test=args.dry_run,
                    run_standard_self_test=True,
                    ignore_symlinks_for_this_test_run=True 
                )
            else: 
                 self_test_flow(
                    temp_dir_str=str(self_test_sandbox),
                    dry_run_for_test=args.dry_run, 
                    run_complex_map_sub_test=is_complex_run,
                    run_edge_case_sub_test=is_edge_case_run,
                    run_empty_map_sub_test=is_empty_map_run,
                    run_resume_test=is_resume_run,
                    run_precision_test=is_precision_run,
                    ignore_symlinks_for_this_test_run=args.ignore_symlinks 
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
