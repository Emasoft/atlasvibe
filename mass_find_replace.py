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

    for name, path in exp_paths_after_rename.items():
        record_test(f"Path exists: '{path.relative_to(temp_dir)}' (for '{name}')", 
                    path.exists(), 
                    f"Path '{path.relative_to(temp_dir)}' MISSING for '{name}'")

    record_test("Old 'flojoy_root' base directory removed", 
                not (temp_dir / "flojoy_root").exists(),
                "Old 'flojoy_root' base directory STILL EXISTS")

    # Content checks helper
    def check_file_content(file_path: Optional[Path], expected_content: Union[str, bytes], test_description_base: str, is_binary: bool = False):
        if not file_path or not file_path.exists():
            record_test(f"Content: '{test_description_base}'", False, f"File MISSING at '{file_path}'")
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
                details = f"Expected: {expected_content!r}, Got: {actual_content!r}"
            else: 
                details = f"Expected:\n{expected_content}\nGot:\n{actual_content}"
        record_test(f"Content: '{test_description_base}'", condition, details)

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
    
    check_file_content(exp_paths_after_rename.get("binary_atlasvibe_file.bin"),
                       b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04",
                       "binary_atlasvibe_file.bin (content untouched)", is_binary=True)
    check_file_content(exp_paths_after_rename.get("binary_fLoJoY_name.bin"),
                       b"unmapped_variant_binary_content" + b"\x00\xff",
                       "binary_fLoJoY_name.bin (content untouched)", is_binary=True)

    binary_file_renamed = exp_paths_after_rename.get("binary_atlasvibe_file.bin")
    if binary_file_renamed and binary_file_renamed.exists():
        record_test(f"File type: '{binary_file_renamed.name}' still binary",
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
        record_test("Exclusion: No transactions for excluded items",
                    not found_tx_for_excluded,
                    "Transactions WERE generated for items that should have been excluded by scan.")

        if not found_tx_for_excluded:
            all_non_excluded_processed_correctly = True
            for tx_idx, tx in enumerate(transactions): 
                 if not ("excluded_flojoy_dir/" in tx["PATH"] or tx["PATH"] == "exclude_this_flojoy_file.txt"):
                    if tx["STATUS"] not in [TransactionStatus.COMPLETED.value, TransactionStatus.SKIPPED.value]:
                        all_non_excluded_processed_correctly = False
                        record_test(f"Transaction status (ID: {tx['id']})", False,
                                    f"Path: {tx['PATH']}, Status is {tx['STATUS']}, expected COMPLETED or SKIPPED.")
                        break 
            if all_non_excluded_processed_correctly: 
                 record_test("Transaction statuses: All non-excluded are COMPLETED or SKIPPED", True)
    else:
        record_test(f"Transaction file load: '{original_transaction_file.name}'", False, "Could not load for status verification.")

    # --- Table Formatting ---
    term_width, _ = shutil.get_terminal_size(fallback=(80, 24))
    padding = 1
    
    id_col_content_width = len(str(test_counter)) if test_counter > 0 else 3 # Max width for test ID
    id_col_total_width = id_col_content_width + 2 * padding
    
    outcome_text_pass = f"{PASS_SYMBOL} PASS"
    outcome_text_fail = f"{FAIL_SYMBOL} FAIL"
    outcome_col_content_width = max(len(outcome_text_pass), len(outcome_text_fail))
    outcome_col_total_width = outcome_col_content_width + 2 * padding

    # 4 vertical bars "│"
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
    sys.stdout.write(BLUE + "┌" + "─" * id_col_total_width + "┬" + "─" * desc_col_total_width + "┬" + "─" * outcome_col_total_width + "┐" + RESET + "\n")
    sys.stdout.write(BLUE + f"│{' ' * padding}{header_id}{' ' * padding}│{' ' * padding}{header_desc}{' ' * padding}│{' ' * padding}{header_outcome}{' ' * padding}│" + RESET + "\n")
    sys.stdout.write(BLUE + "├" + "─" * id_col_total_width + "┼" + "─" * desc_col_total_width + "┼" + "─" * outcome_col_total_width + "┤" + RESET + "\n")

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
            id_cell_content = id_text_content if i == 0 else ""
            id_cell_str = f"{' ' * padding}{id_cell_content:>{id_col_content_width}}{' ' * padding}" # Right-align ID
            
            desc_cell_str = f"{' ' * padding}{line_frag:<{desc_col_content_width}}{' ' * padding}"
            
            outcome_cell_content_colored = ""
            if i == 0:
                padded_outcome_text = f"{outcome_text_content:<{outcome_col_content_width}}"
                outcome_cell_content_colored = f"{color}{padded_outcome_text}{RESET}"
            
            if i == 0:
                 outcome_cell_str = f"{' ' * padding}{color}{outcome_text_content:<{outcome_col_content_width}}{RESET}{' ' * padding}"
            else:
                 outcome_cell_str = f"{' ' * padding}{'':<{outcome_col_content_width}}{' ' * padding}"


            sys.stdout.write(BLUE + f"│{id_cell_str}│{desc_cell_str}│{outcome_cell_str}│" + RESET + "\n")

        if result["status"] == "FAIL" and result["details"]:
            failed_test_details.append({"id": result['id'], "description": result['description'], "details": result['details']})
    
    sys.stdout.write(BLUE + "└" + "─" * id_col_total_width + "┴" + "─" * desc_col_total_width + "┴" + "─" * outcome_col_total_width + "┘" + RESET + "\n")

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
    temp_dir_str: str, # This will be the path to SELF_TEST_SANDBOX_DIR
    dry_run_for_test: bool
) -> None:
    temp_dir = Path(temp_dir_str) 
    _create_self_test_environment(temp_dir)

    test_excluded_dirs: List[str] = ["excluded_flojoy_dir"] 
    test_excluded_files: List[str] = ["exclude_this_flojoy_file.txt"]
    test_extensions = [".txt", ".py", ".md", ".bin", ".log"] 

    transaction_file = temp_dir / SELF_TEST_PRIMARY_TRANSACTION_FILE

    # These print statements will be logged by Prefect due to log_prints=True
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
        
        # _verify_self_test_results_task is now a regular function.
        # Its sys.stdout.write calls will go directly to console.
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
        # For CLI utilities, direct print to stderr for early errors is often clearer.
        sys.stderr.write(f"Error: Root directory '{root_dir}' does not exist or is not a directory.\n")
        return

    transaction_json_path = root_dir / MAIN_TRANSACTION_FILE_NAME

    if not dry_run and not force_execution and not resume: 
        # Direct print for interactive parts
        sys.stdout.write("--- Proposed Operation ---\n")
        sys.stdout.write(f"Root Directory: {root_dir}\n")
        sys.stdout.write("Operation: Replace 'flojoy' and its variants with 'atlasvibe' equivalents.\n")
        sys.stdout.write(f"File Extensions for content scan: {extensions if extensions else 'All non-binary (heuristic)'}\n")
        sys.stdout.write(f"Exclude Dirs: {exclude_dirs}\n")
        sys.stdout.write(f"Exclude Files: {exclude_files}\n")
        sys.stdout.write("-------------------------\n")
        sys.stdout.flush() # Ensure prompt appears before input
        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes':
            sys.stdout.write("Operation cancelled by user.\n")
            return

    # Messages below will be captured by Prefect's log_prints=True
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
        # Use direct print for self-test setup messages as they occur before Prefect flow might capture them fully.
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
        
        sys.stdout.flush() # Ensure setup messages are printed before flow starts
            
        try:
            # For self_test_flow, log_prints=True will handle its internal print statements.
            self_test_flow(
                temp_dir_str=str(self_test_sandbox), 
                dry_run_for_test=args.dry_run
            )
            if not args.dry_run:
                 # Success message for non-dry run is part of _verify_self_test_results_task
                 pass
            else:
                 # Message for dry run completion
                 sys.stdout.write(YELLOW + "Self-test dry run scan complete." + RESET + "\n")
        except AssertionError: 
            # The _verify_self_test_results_task already prints detailed failure info.
            # Exiting with 1 indicates failure.
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
    except (FileNotFoundError, ValueError): # Handle cases where paths might not exist yet or are not relative
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
        # Critical errors printed directly to stderr
        sys.stderr.write(f"CRITICAL ERROR: A required dependency is missing: {e}.\n")
        sys.stderr.write("Please ensure 'prefect' and 'chardet' are installed in your Python environment.\n")
        sys.stderr.write("You can typically install them using pip: pip install prefect chardet\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

