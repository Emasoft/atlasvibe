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
# replace_logic is used by file_system_operations

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
    (base_dir / "unmapped_variant_flojoy_content.txt").write_text( # Test unmapped variant in content
        "This has fLoJoY content, and also flojoy."
    )
    (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")
    (base_dir / "binary_fLoJoY_name.bin").write_bytes(b"unmapped_variant_binary_content" + b"\x00\xff") # Unmapped variant in name

    # Exclusions
    (base_dir / "excluded_flojoy_dir").mkdir(exist_ok=True)
    (base_dir / "excluded_flojoy_dir" / "inner_flojoy_file.txt").write_text("flojoy inside excluded dir")
    (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in explicitly excluded file")
    
    (base_dir / "no_target_here.log").write_text("This is a log file without the target string.")


# This is now a regular function, not a Prefect task, to avoid log prefixing on table output.
def _verify_self_test_results_task(
    temp_dir: Path, # This will be the SELF_TEST_SANDBOX_DIR
    original_transaction_file: Path 
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
        "binary_fLoJoY_name.bin": temp_dir / "binary_fLoJoY_name.bin"
    }

    # Path Existence Tests - Functional Descriptions
    record_test("Path: Top-level directory rename (e.g., 'flojoy_root' -> 'atlasvibe_root').", 
                exp_paths_after_rename["atlasvibe_root"].exists(), 
                f"Expected renamed top-level dir '{exp_paths_after_rename['atlasvibe_root'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: Nested directory rename (e.g., 'sub_flojoy_folder' -> 'sub_atlasvibe_folder').", 
                exp_paths_after_rename["sub_atlasvibe_folder"].exists(), 
                f"Expected renamed nested dir '{exp_paths_after_rename['sub_atlasvibe_folder'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: Deeply nested directory rename with case change (e.g., 'another_FLOJOY_dir' -> 'another_ATLASVIBE_dir').", 
                exp_paths_after_rename["another_ATLASVIBE_dir"].exists(), 
                f"Expected renamed deep dir '{exp_paths_after_rename['another_ATLASVIBE_dir'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: File rename within a transformed directory path.", 
                exp_paths_after_rename["deep_atlasvibe_file.txt"].exists(), 
                f"Expected renamed file in transformed path '{exp_paths_after_rename['deep_atlasvibe_file.txt'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: File rename at a shallower level in transformed path.", 
                exp_paths_after_rename["another_atlasvibe_file.py"].exists(), 
                f"Expected renamed file '{exp_paths_after_rename['another_atlasvibe_file.py'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: File rename based on name match only (content irrelevant for name change).", 
                exp_paths_after_rename["only_name_atlasvibe.md"].exists(), 
                f"Expected renamed file '{exp_paths_after_rename['only_name_atlasvibe.md'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: File rename with mixed-case target string in original name.", 
                exp_paths_after_rename["file_with_atlasVibe_lines.txt"].exists(), 
                f"Expected renamed file '{exp_paths_after_rename['file_with_atlasVibe_lines.txt'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: File rename where original name is mapped, content has unmapped variants.", 
                exp_paths_after_rename["unmapped_variant_atlasvibe_content.txt"].exists(), 
                f"Expected renamed file '{exp_paths_after_rename['unmapped_variant_atlasvibe_content.txt'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: File with no target string in name or content remains unchanged.", 
                exp_paths_after_rename["no_target_here.log"].exists(), 
                f"Expected unchanged file '{exp_paths_after_rename['no_target_here.log'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: Explicitly excluded file is not renamed and still exists.", 
                exp_paths_after_rename["exclude_this_flojoy_file.txt"].exists(), 
                f"Expected excluded file '{exp_paths_after_rename['exclude_this_flojoy_file.txt'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: Explicitly excluded directory is not renamed and still exists.", 
                exp_paths_after_rename["excluded_flojoy_dir"].exists(), 
                f"Expected excluded dir '{exp_paths_after_rename['excluded_flojoy_dir'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: File within an excluded directory is not renamed and still exists.", 
                exp_paths_after_rename["inner_flojoy_file.txt_in_excluded_dir"].exists(), 
                f"Expected file in excluded dir '{exp_paths_after_rename['inner_flojoy_file.txt_in_excluded_dir'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: Binary file with a mapped target string in its name is renamed.", 
                exp_paths_after_rename["binary_atlasvibe_file.bin"].exists(), 
                f"Expected renamed binary file '{exp_paths_after_rename['binary_atlasvibe_file.bin'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: Binary file with an unmapped target string variant in its name is NOT renamed.", 
                exp_paths_after_rename["binary_fLoJoY_name.bin"].exists(), 
                f"Expected unrenamed binary file '{exp_paths_after_rename['binary_fLoJoY_name.bin'].relative_to(temp_dir)}' MISSING.")
    record_test("Path: Original top-level directory is removed after its rename.", 
                not (temp_dir / "flojoy_root").exists(),
                "Old 'flojoy_root' base directory STILL EXISTS.")

    # Content checks helper
    def check_file_content(file_path: Optional[Path], expected_content: Union[str, bytes], test_description_base: str, is_binary: bool = False):
        if not file_path or not file_path.exists():
            record_test(f"{test_description_base} (File Existence)", False, f"File MISSING at '{file_path}' for content check.")
            return

        actual_content: Union[str, bytes]
        if is_binary:
            actual_content = file_path.read_bytes()
        else:
            actual_content = file_path.read_text(encoding='utf-8')
        
        condition = actual_content == expected_content
        details = ""
        if not condition:
            if is_binary:
                details = f"Expected (bytes): {expected_content!r}\nGot (bytes): {actual_content!r}"
            else: 
                # For text, show repr to reveal hidden differences for the failing test
                details = f"Expected (repr):\n{expected_content!r}\nGot (repr):\n{actual_content!r}"
        record_test(test_description_base, condition, details)

    # Content verifications - Functional Descriptions
    check_file_content(exp_paths_after_rename.get("deep_atlasvibe_file.txt"),
                       "Line 1: atlasvibe content.\nLine 2: More AtlasVibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project.",
                       "Content: All mapped 'flojoy' variants replaced in a deeply nested text file.")
    check_file_content(exp_paths_after_rename.get("file_with_atlasVibe_lines.txt"),
                       "First atlasVibe.\nSecond AtlasVibe.\natlasvibe and ATLASVIBE on same line.",
                       "Content: Mixed-case mapped 'floJoy' variants replaced correctly in text file.")
    check_file_content(exp_paths_after_rename.get("unmapped_variant_atlasvibe_content.txt"),
                       "This has fLoJoY content, and also atlasvibe.",
                       "Content: Unmapped 'fLoJoY' variant preserved, mapped 'flojoy' variant replaced in text file.")
    check_file_content(exp_paths_after_rename.get("only_name_atlasvibe.md"),
                       "Content without target string.",
                       "Content: File renamed due to name match has its content (without target) unchanged.")
    check_file_content(exp_paths_after_rename.get("exclude_this_flojoy_file.txt"),
                       "flojoy content in explicitly excluded file",
                       "Content: Explicitly excluded file's content remains untouched, even if containing target string.")
    check_file_content(exp_paths_after_rename.get("inner_flojoy_file.txt_in_excluded_dir"),
                       "flojoy inside excluded dir",
                       "Content: File within an excluded directory has its content untouched.")
    check_file_content(exp_paths_after_rename.get("binary_atlasvibe_file.bin"),
                       b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04",
                       "Content: Binary file (renamed due to name match) has its byte content untouched.", is_binary=True)
    check_file_content(exp_paths_after_rename.get("binary_fLoJoY_name.bin"),
                       b"unmapped_variant_binary_content" + b"\x00\xff",
                       "Content: Binary file (name not mapped) has its byte content untouched.", is_binary=True)

    binary_file_renamed = exp_paths_after_rename.get("binary_atlasvibe_file.bin")
    if binary_file_renamed and binary_file_renamed.exists():
        record_test(f"File Type: Renamed binary file ('{binary_file_renamed.name}') is still detected as binary.",
                    is_likely_binary_file(binary_file_renamed),
                    f"File '{binary_file_renamed.name}' NOT detected as binary after rename.")

    transactions = load_transactions(original_transaction_file)
    if transactions is not None:
        found_tx_for_excluded = False
        for tx in transactions:
            tx_path_str = tx["PATH"]
            if "excluded_flojoy_dir/" in tx_path_str or tx_path_str == "exclude_this_flojoy_file.txt":
                found_tx_for_excluded = True
                break 
        record_test("Scan Logic: No transactions generated for items in excluded directories or explicitly excluded files.",
                    not found_tx_for_excluded,
                    "Transactions WERE generated for items that should have been excluded by scan.")

        if not found_tx_for_excluded:
            all_non_excluded_processed_correctly = True
            for tx_idx, tx in enumerate(transactions): 
                 if not ("excluded_flojoy_dir/" in tx["PATH"] or tx["PATH"] == "exclude_this_flojoy_file.txt"):
                    if tx["STATUS"] not in [TransactionStatus.COMPLETED.value, TransactionStatus.SKIPPED.value]:
                        all_non_excluded_processed_correctly = False
                        record_test(f"Transaction Status (Tx ID: {tx['id']}): Non-excluded transaction processed to COMPLETED or SKIPPED.", False,
                                    f"Path: {tx['PATH']}, Status is {tx['STATUS']}, expected COMPLETED or SKIPPED.")
                        break 
            if all_non_excluded_processed_correctly: 
                 record_test("Transaction Status: All non-excluded transactions are COMPLETED or SKIPPED.", True)
    else:
        record_test(f"Transaction File Integrity: '{original_transaction_file.name}' can be loaded for verification.", False, "Could not load for status verification.")

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
    header_outcome = f"{'Outcome':^{outcome_col_content_width}}"

    sys.stdout.write("\n")
    sys.stdout.write(BLUE + DBL_TOP_LEFT + DBL_HORIZONTAL * id_col_total_width + DBL_T_DOWN + DBL_HORIZONTAL * desc_col_total_width + DBL_T_DOWN + DBL_HORIZONTAL * outcome_col_total_width + DBL_TOP_RIGHT + RESET + "\n")
    sys.stdout.write(BLUE + DBL_VERTICAL + f"{' ' * padding}{header_id}{' ' * padding}" + DBL_VERTICAL + f"{' ' * padding}{header_desc}{' ' * padding}" + DBL_VERTICAL + f"{' ' * padding}{header_outcome}{' ' * padding}" + DBL_VERTICAL + RESET + "\n")
    sys.stdout.write(BLUE + DBL_T_RIGHT + DBL_HORIZONTAL * id_col_total_width + DBL_CROSS + DBL_HORIZONTAL * desc_col_total_width + DBL_CROSS + DBL_HORIZONTAL * outcome_col_total_width + DBL_T_LEFT + RESET + "\n")

    failed_test_details = []
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
            failed_test_details.append({"id": result['id'], "description": result['description'], "details": result['details']})
    
    sys.stdout.write(BLUE + DBL_BOTTOM_LEFT + DBL_HORIZONTAL * id_col_total_width + DBL_T_UP + DBL_HORIZONTAL * desc_col_total_width + DBL_T_UP + DBL_HORIZONTAL * outcome_col_total_width + DBL_BOTTOM_RIGHT + RESET + "\n")

    if failed_test_details:
        sys.stdout.write("\n" + RED + "--- Failure Details ---" + RESET + "\n")
        for failure in failed_test_details:
            sys.stdout.write(RED + f"Test #{failure['id']}: {failure['description']}" + RESET + "\n")
            details_lines = failure['details'].split('\n')
            for line in details_lines:
                sys.stdout.write(RED + f"  └── {line}" + RESET + "\n")
    
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
    dry_run_for_test: bool
) -> None:
    temp_dir = Path(temp_dir_str) 
    _create_self_test_environment(temp_dir)

    test_excluded_dirs: List[str] = ["excluded_flojoy_dir"] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt"]
    test_extensions = [".txt", ".py", ".md", ".bin", ".log"] 

    transaction_file = temp_dir / SELF_TEST_PRIMARY_TRANSACTION_FILE

    print("Self-Test: Scanning directory...")
    transactions = scan_directory_for_occurrences(
        root_dir=temp_dir,
        excluded_dirs=test_excluded_dirs,
        excluded_files=test_excluded_files,
        file_extensions=test_extensions
    )
    save_transactions(transactions, transaction_file)
    print(f"Self-Test: Scan complete. {len(transactions)} transactions planned in {transaction_file}")

    if not dry_run_for_test:
        print("Self-Test: Executing transactions...")
        execution_stats = execute_all_transactions(
            transactions_file_path=transaction_file,
            root_dir=temp_dir, 
            dry_run=False, 
            resume=False   
        )
        print(f"Self-Test: Execution complete. Stats: {execution_stats}")
        
        _verify_self_test_results_task(
            temp_dir=temp_dir, 
            original_transaction_file=transaction_file
        )
    else:
        print("Self-Test: Dry run selected. Skipping execution and verification of changes.")


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

    args = parser.parse_args()
    
    if args.self_test:
        sys.stdout.write(f"Running self-test in sandbox: '{SELF_TEST_SANDBOX_DIR}'...\n")
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
                dry_run_for_test=args.dry_run
            )
            if not args.dry_run:
                 pass
            else:
                 sys.stdout.write(YELLOW + "Self-test dry run scan complete." + RESET + "\n")
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

