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
from typing import List, Dict, Any, Optional 

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

# ANSI Color Codes & Unicode Symbols for formatted output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
YELLOW = "\033[93m"
PASS_SYMBOL = "✅"
FAIL_SYMBOL = "❌"


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


@task
def _verify_self_test_results_task(
    temp_dir: Path,
    original_transaction_file: Path 
) -> bool:
    print("--- Verifying Self-Test Results ---")
    passed_checks = 0
    failed_checks = 0
    test_results: List[Dict[str, Any]] = []

    def record_test(description: str, condition: bool, details_on_fail: str = "") -> None:
        nonlocal passed_checks, failed_checks
        status = "PASS" if condition else "FAIL"
        
        if condition:
            passed_checks += 1
        else:
            failed_checks += 1
            
        test_results.append({
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

    for name, path in exp_paths_after_rename.items():
        record_test(f"Path '{path.relative_to(temp_dir)}' exists for '{name}'", 
                    path.exists(), 
                    f"Path '{path.relative_to(temp_dir)}' MISSING for '{name}'")

    record_test("Old 'flojoy_root' base directory removed", 
                not (temp_dir / "flojoy_root").exists(),
                "Old 'flojoy_root' base directory STILL EXISTS")

    # Content checks helper
    def check_file_content(file_path: Optional[Path], expected_content: Union[str, bytes], test_description_base: str, is_binary: bool = False):
        if not file_path or not file_path.exists():
            record_test(f"Content check for '{test_description_base}'", False, f"File MISSING at '{file_path}'")
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
                details = f"Content INCORRECT. Expected: {expected_content!r}, Got: {actual_content!r}"
            else: # Text diff might be too verbose for summary, but good for detailed logs
                details = f"Content INCORRECT.\nExpected:\n{expected_content}\nGot:\n{actual_content}"

        record_test(f"Content of '{test_description_base}' is correct", condition, details)

    # Content verifications
    check_file_content(exp_paths_after_rename.get("deep_atlasvibe_file.txt"),
                       "Line 1: atlasvibe content.\nLine 2: More AtlasVibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project.",
                       "deep_atlasvibe_file.txt")
    check_file_content(exp_paths_after_rename.get("file_with_atlasVibe_lines.txt"),
                       "First atlasVibe.\nSecond AtlasVibe.\natlasvibe and ATLASVIBE on same line.",
                       "file_with_atlasVibe_lines.txt")
    check_file_content(exp_paths_after_rename.get("unmapped_variant_atlasvibe_content.txt"),
                       "This has fLoJoY content, and also atlasvibe.",
                       "unmapped_variant_atlasvibe_content.txt (unmapped variant preserved)")
    check_file_content(exp_paths_after_rename.get("only_name_atlasvibe.md"),
                       "Content without target string.",
                       "only_name_atlasvibe.md")
    check_file_content(exp_paths_after_rename.get("exclude_this_flojoy_file.txt"),
                       "flojoy content in explicitly excluded file",
                       "exclude_this_flojoy_file.txt (explicitly excluded)")
    check_file_content(exp_paths_after_rename.get("inner_flojoy_file.txt_in_excluded_dir"),
                       "flojoy inside excluded dir",
                       "inner_flojoy_file.txt (in excluded_dir)")
    
    # Binary file content checks
    check_file_content(exp_paths_after_rename.get("binary_atlasvibe_file.bin"),
                       b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04",
                       "binary_atlasvibe_file.bin (content untouched)", is_binary=True)
    check_file_content(exp_paths_after_rename.get("binary_fLoJoY_name.bin"),
                       b"unmapped_variant_binary_content" + b"\x00\xff",
                       "binary_fLoJoY_name.bin (content untouched)", is_binary=True)

    # Binary file type check
    binary_file_renamed = exp_paths_after_rename.get("binary_atlasvibe_file.bin")
    if binary_file_renamed and binary_file_renamed.exists():
        record_test(f"File '{binary_file_renamed.name}' still detected as binary",
                    is_likely_binary_file(binary_file_renamed),
                    f"File '{binary_file_renamed.name}' NOT detected as binary after rename.")

    # Transaction verification
    transactions = load_transactions(original_transaction_file)
    if transactions is not None:
        found_tx_for_excluded = False
        for tx in transactions:
            tx_path_str = tx["PATH"]
            if "excluded_flojoy_dir/" in tx_path_str or tx_path_str == "exclude_this_flojoy_file.txt":
                found_tx_for_excluded = True
                break 
        record_test("No transactions generated for items within excluded_dirs or matching excluded_files",
                    not found_tx_for_excluded,
                    "Transactions WERE generated for items that should have been excluded by scan.")

        if not found_tx_for_excluded:
            all_non_excluded_processed_correctly = True
            for tx in transactions: # Iterate again, only non-excluded this time
                 if not ("excluded_flojoy_dir/" in tx["PATH"] or tx["PATH"] == "exclude_this_flojoy_file.txt"):
                    if tx["STATUS"] not in [TransactionStatus.COMPLETED.value, TransactionStatus.SKIPPED.value]:
                        all_non_excluded_processed_correctly = False
                        record_test(f"Transaction {tx['id']} (Path: {tx['PATH']}) status check", False,
                                    f"Status is {tx['STATUS']}, expected COMPLETED or SKIPPED.")
                        break # One failure is enough to mark this group test as failed
            if all_non_excluded_processed_correctly: # Only record success if all passed
                 record_test("All non-excluded transactions are COMPLETED or SKIPPED", True)

    else:
        record_test(f"Loading transaction file '{original_transaction_file.name}'", False, "Could not load for status verification.")

    # Print formatted results
    print("\n" + YELLOW + "--- Self-Test Results Table ---" + RESET)
    header = f"{'Status':<10} | {'Test Description'}"
    print(YELLOW + header + RESET)
    print(YELLOW + "-" * (len(header) + 10) + RESET) # Adjust separator length

    for result in test_results:
        status_symbol = PASS_SYMBOL if result["status"] == "PASS" else FAIL_SYMBOL
        color = GREEN if result["status"] == "PASS" else RED
        
        status_cell = f"{color}{status_symbol:<2}{RESET}" # Symbol with padding
        print(f"{status_cell}    | {result['description']}")
        if result["status"] == "FAIL" and result["details"]:
            # Indent details for readability
            details_lines = result["details"].split('\n')
            for i, line in enumerate(details_lines):
                prefix = "     └── Details: " if i == 0 else "                  "
                print(f"{RED}{prefix}{line}{RESET}")
    
    print(YELLOW + "--- Self-Test Verification Summary ---" + RESET)
    total_tests = passed_checks + failed_checks
    if total_tests > 0:
        percentage_passed = (passed_checks / total_tests) * 100
        summary_color = GREEN if failed_checks == 0 else RED
        summary_emoji = PASS_SYMBOL if failed_checks == 0 else FAIL_SYMBOL
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {GREEN}{passed_checks}{RESET}")
        print(f"Failed: {RED if failed_checks > 0 else GREEN}{failed_checks}{RESET}")
        print(f"Percentage Passed: {summary_color}{percentage_passed:.2f}% {summary_emoji}{RESET}")
        
        if failed_checks == 0:
            print(GREEN + "All self-test checks passed successfully! " + PASS_SYMBOL + RESET)
        else:
            print(RED + f"Self-test FAILED with {failed_checks} error(s). " + FAIL_SYMBOL + RESET)
    else:
        print(YELLOW + "No self-test checks were recorded." + RESET)


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
        print(f"Error: Root directory '{root_dir}' does not exist or is not a directory.")
        return

    transaction_json_path = root_dir / MAIN_TRANSACTION_FILE_NAME

    if not dry_run and not force_execution and not resume: 
        print("--- Proposed Operation ---")
        print(f"Root Directory: {root_dir}")
        print("Operation: Replace 'flojoy' and its variants with 'atlasvibe' equivalents.")
        print(f"File Extensions for content scan: {extensions if extensions else 'All non-binary (heuristic)'}")
        print(f"Exclude Dirs: {exclude_dirs}")
        print(f"Exclude Files: {exclude_files}")
        print("-------------------------")
        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled by user.")
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
                        help="Run a predefined self-test in a temporary directory.")

    args = parser.parse_args()
    
    if args.self_test:
        print("Running self-test...")
        with tempfile.TemporaryDirectory(prefix="mass_replace_self_test_") as tmpdir_str:
            try:
                self_test_flow(
                    temp_dir_str=tmpdir_str,
                    dry_run_for_test=args.dry_run
                )
                # _verify_self_test_results_task will raise AssertionError if tests fail
                # If it completes without raising, and not a dry run, it means tests passed.
                if not args.dry_run: # Only print PASSED if it wasn't a dry run and no assertion was raised
                     print(GREEN + "Self-test PASSED successfully! " + PASS_SYMBOL + RESET)
                else:
                     print(YELLOW + "Self-test dry run scan complete." + RESET)
            except AssertionError as e: # Explicitly catch AssertionError from _verify_self_test_results_task
                # The error message from the assertion is already printed by _verify_self_test_results_task's summary
                # print(RED + f"Self-test FAILED: {e} " + FAIL_SYMBOL + RESET) # This would be redundant
                sys.exit(1)
            except Exception as e:
                print(RED + f"Self-test ERRORED: An unexpected error occurred: {e} " + FAIL_SYMBOL + RESET)
                sys.exit(1)
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
        print(f"CRITICAL ERROR: A required dependency is missing: {e}.")
        print("Please ensure 'prefect' and 'chardet' are installed in your Python environment.")
        print("You can typically install them using pip: pip install prefect chardet")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

