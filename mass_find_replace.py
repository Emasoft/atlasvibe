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
    (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in excluded file")
    (base_dir / "no_target_here.log").write_text("This is a log file without the target string.")
    (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")


@task
def _verify_self_test_results_task(
    temp_dir: Path,
    original_transaction_file: Path 
) -> bool:
    print("--- Verifying Self-Test Results ---")
    passed_checks = 0
    failed_checks = 0

    def check(condition: bool, pass_msg: str, fail_msg: str) -> None:
        nonlocal passed_checks, failed_checks
        if condition:
            print(f"PASS: {pass_msg}")
            passed_checks += 1
        else:
            print(f"FAIL: {fail_msg}")
            failed_checks += 1

    exp_paths_after_rename = {
        "atlasvibe_root": temp_dir / "atlasvibe_root",
        "sub_atlasvibe_folder": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder",
        "another_ATLASVIBE_dir": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir",
        "deep_atlasvibe_file.txt": temp_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file.txt",
        "another_atlasvibe_file.py": temp_dir / "atlasvibe_root" / "another_atlasvibe_file.py",
        "only_name_atlasvibe.md": temp_dir / "only_name_atlasvibe.md",
        "file_with_atlasVibe_lines.txt": temp_dir / "file_with_atlasVibe_lines.txt",
        "no_target_here.log": temp_dir / "no_target_here.log", 
        "exclude_this_flojoy_file.txt": temp_dir / "exclude_this_flojoy_file.txt",
        "binary_atlasvibe_file.bin": temp_dir / "binary_atlasvibe_file.bin"
    }

    for name, path in exp_paths_after_rename.items():
        check(path.exists(), f"Path '{path.relative_to(temp_dir)}' exists for '{name}'.",
              f"Path '{path.relative_to(temp_dir)}' MISSING for '{name}'.")

    check(not (temp_dir / "flojoy_root").exists(), "Old 'flojoy_root' base directory removed.",
          "Old 'flojoy_root' base directory STILL EXISTS.")

    deep_file = exp_paths_after_rename.get("deep_atlasvibe_file.txt")
    if deep_file and deep_file.exists():
        content = deep_file.read_text(encoding='utf-8')
        expected_content = "Line 1: atlasvibe content.\nLine 2: More AtlasVibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project."
        check(content == expected_content, "Content of 'deep_atlasvibe_file.txt' correct.",
              f"Content of 'deep_atlasvibe_file.txt' INCORRECT. Got:\n{content}\nExpected:\n{expected_content}")

    multi_line_file = exp_paths_after_rename.get("file_with_atlasVibe_lines.txt")
    if multi_line_file and multi_line_file.exists():
        content = multi_line_file.read_text(encoding='utf-8')
        expected_content = "First atlasVibe.\nSecond AtlasVibe.\natlasvibe and ATLASVIBE on same line."
        check(content == expected_content, "Content of 'file_with_atlasVibe_lines.txt' correct.",
              f"Content of 'file_with_atlasVibe_lines.txt' INCORRECT. Got:\n{content}\nExpected:\n{expected_content}")

    only_name_file = exp_paths_after_rename.get("only_name_atlasvibe.md")
    if only_name_file and only_name_file.exists():
        content = only_name_file.read_text(encoding='utf-8')
        expected_content = "Content without target string."
        check(content == expected_content, "Content of 'only_name_atlasvibe.md' correct.",
              "Content of 'only_name_atlasvibe.md' INCORRECT.")

    excluded_file = exp_paths_after_rename.get("exclude_this_flojoy_file.txt")
    if excluded_file and excluded_file.exists(): 
        content = excluded_file.read_text(encoding='utf-8')
        expected_content = "flojoy content in excluded file"
        check(content == expected_content, "Content of excluded file correct.",
              "Content of excluded file INCORRECT.")
    else: 
        if not (temp_dir / "exclude_this_flojoy_file.txt").exists():
             check(False, "", "Excluded file 'exclude_this_flojoy_file.txt' MISSING.")
    
    binary_file_renamed = exp_paths_after_rename.get("binary_atlasvibe_file.bin")
    if binary_file_renamed and binary_file_renamed.exists():
        original_binary_content = b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04"
        actual_content = binary_file_renamed.read_bytes()
        check(actual_content == original_binary_content, "Binary file content UNTOUCHED as expected.",
              f"Binary file content MODIFIED. Expected: {original_binary_content!r}, Got: {actual_content!r}")
        check(is_likely_binary_file(binary_file_renamed), "Renamed binary file still detected as binary.",
              "Renamed binary file NOT detected as binary.")


    transactions = load_transactions(original_transaction_file)
    if transactions:
        all_completed_or_skipped = True
        for tx in transactions:
            if "exclude_this_flojoy_file.txt" in tx["PATH"]:
                if tx["STATUS"] == TransactionStatus.COMPLETED.value and tx["TYPE"] != TransactionType.FILE_NAME.value:
                     if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
                        all_completed_or_skipped = False
                        print(f"FAIL: Transaction {tx['id']} for excluded file content (Path: {tx['PATH']}) has status {tx['STATUS']}.")
                        break
            elif tx["STATUS"] not in [TransactionStatus.COMPLETED.value, TransactionStatus.SKIPPED.value]:
                all_completed_or_skipped = False
                print(f"FAIL: Transaction {tx['id']} (Type: {tx['TYPE']}, Path: {tx['PATH']}) has status {tx['STATUS']}.")
                break
        check(all_completed_or_skipped, "All processed transactions are COMPLETED or SKIPPED.",
              "Not all processed transactions are COMPLETED or SKIPPED.")
    else:
        check(False, "", f"Could not load transaction file {original_transaction_file} for status verification.")

    print(f"--- Self-Test Verification Summary: {passed_checks} PASSED, {failed_checks} FAILED ---")
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

    test_excluded_dirs: List[str] = [] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt"]
    test_extensions = [".txt", ".py", ".md"] 

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
                if not args.dry_run:
                     print("Self-test PASSED.")
                else:
                     print("Self-test dry run scan complete.")
            except AssertionError as e:
                print(f"Self-test FAILED: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"Self-test ERRORED: {e}")
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

