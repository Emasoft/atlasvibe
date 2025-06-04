#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Consolidated redundant empty map checks into a single check in main_flow.
# - Removed unused skip_scan parameter from execute_all_transactions call.
# - Added explicit flushing of Prefect's log handler after subprocess output printing to avoid Prefect shutdown logging errors.
# - Replaced bare except with except Exception to comply with linting rules.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import logging
import sys
import time
from pathlib import Path
from typing import Any, Optional

import replace_logic
from file_system_operations import (
    load_transactions, save_transactions, TransactionStatus,
    TRANSACTION_FILE_BACKUP_EXT, BINARY_MATCHES_LOG_FILE, COLLISIONS_ERRORS_LOG_FILE
)

SCRIPT_NAME = "MFR - Mass Find Replace - A script to safely rename things in your project"
MAIN_TRANSACTION_FILE_NAME = "planned_transactions.json"
DEFAULT_REPLACEMENT_MAPPING_FILE = "replacement_mapping.json"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
DIM = "\033[2m"

def _get_logger(verbose_mode: bool = False) -> logging.Logger:
    """Get logger with appropriate configuration."""
    import logging
    try:
        # Try to get Prefect's context logger
        from prefect import get_run_logger
        from prefect.exceptions import MissingContextError
        try:
            logger = get_run_logger()
            if verbose_mode:
                logger.setLevel(logging.DEBUG)
            return logger
        except MissingContextError:
            pass
    except ImportError:
        pass
    
    # Create standard logger
    logger = logging.getLogger('mass_find_replace')
    logger.setLevel(logging.DEBUG if verbose_mode else logging.INFO)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


def _print_mapping_table(mapping: dict[str, str], logger: logging.Logger) -> None:
    """Print the replacement mapping as a formatted table."""
    if not mapping:
        logger.info("Replacement mapping is empty.")
        return
        
    # Calculate column widths
    max_key_len = max(len(k) for k in mapping.keys())
    max_val_len = max(len(v) for v in mapping.values())
    col1_width = max(max_key_len, 15)
    col2_width = max(max_val_len, 15)
    
    # Unicode box drawing characters
    top_left = "┏"
    top_right = "┓"
    bottom_left = "┗"
    bottom_right = "┛"
    horizontal = "━"
    vertical = "┃"
    cross = "╋"
    t_down = "┳"
    t_up = "┻"
    
    # Print table
    print(f"\n{top_left}{horizontal * (col1_width + 2)}{t_down}{horizontal * (col2_width + 2)}{top_right}")
    print(f"{vertical} {'Search'.center(col1_width)} {vertical} {'Replace'.center(col2_width)} {vertical}")
    print(f"{vertical}{horizontal * (col1_width + 2)}{cross}{horizontal * (col2_width + 2)}{vertical}")
    
    for key, value in mapping.items():
        print(f"{vertical} {key.ljust(col1_width)} {vertical} {value.ljust(col2_width)} {vertical}")
    
    print(f"{bottom_left}{horizontal * (col1_width + 2)}{t_up}{horizontal * (col2_width + 2)}{bottom_right}")


def _get_operation_description(skip_file: bool, skip_folder: bool, skip_content: bool) -> str:
    """Get human-readable description of operations to be performed."""
    operations = []
    if not skip_folder:
        operations.append("folder names")
    if not skip_file:
        operations.append("file names")
    if not skip_content:
        operations.append("file contents")
    
    if not operations:
        return "nothing (all operations skipped)"
    elif len(operations) == 1:
        return operations[0]
    elif len(operations) == 2:
        return f"{operations[0]} and {operations[1]}"
    else:
        return f"{', '.join(operations[:-1])}, and {operations[-1]}"


def _check_existing_transactions(directory: Path, logger: logging.Logger) -> tuple[bool, int]:
    """Check for existing transaction file and calculate progress."""
    txn_file = directory / MAIN_TRANSACTION_FILE_NAME
    if not txn_file.exists():
        return False, 0
    
    try:
        transactions = load_transactions(txn_file, logger=logger)
        if not transactions:
            return False, 0
            
        total = len(transactions)
        completed = sum(1 for tx in transactions if tx.get("STATUS") == TransactionStatus.COMPLETED.value)
        progress = int((completed / total) * 100) if total > 0 else 0
        
        # Check if all are completed
        if completed == total:
            return False, 100
            
        return True, progress
    except Exception:
        return False, 0


def main_flow(
    directory: str, mapping_file: str, extensions: list[str] | None,
    exclude_dirs: list[str], exclude_files: list[str],
    dry_run: bool, skip_scan: bool, resume: bool, force_execution: bool,
    ignore_symlinks_arg: bool, use_gitignore: bool, custom_ignore_file_path: str | None,
    skip_file_renaming: bool, skip_folder_renaming: bool, skip_content: bool,
    timeout_minutes: int, 
    quiet_mode: bool,
    verbose_mode: bool,
    interactive_mode: bool
):
    import logging
    from pathlib import Path
    import pathspec
    from typing import Any

    logger = _get_logger(verbose_mode)

    from file_system_operations import (
        scan_directory_for_occurrences, execute_all_transactions
    )

    if verbose_mode:
        logger.debug("Verbose mode enabled.")
    
    # Explicitly reset replace_logic module state before any operations for this flow run
    replace_logic.reset_module_state()

    # Validate and normalize the directory path
    try:
        abs_root_dir = Path(directory).resolve(strict=False)
    except Exception as e:
        logger.error(f"Error: Invalid directory path '{directory}': {e}")
        return
        
    if not abs_root_dir.exists():
        logger.error(f"Error: Root directory '{abs_root_dir}' not found.")
        return
    if not abs_root_dir.is_dir(): 
        logger.error(f"Error: Path '{abs_root_dir}' is not a directory.")
        return

    # Check for existing incomplete transactions
    if not quiet_mode and not resume and not skip_scan:
        has_existing, progress = _check_existing_transactions(abs_root_dir, logger)
        if has_existing:
            print(f"\n{YELLOW}An incomplete previous run was detected ({progress}% completed).{RESET}")
            choice = input("Do you want to resume it? (y/n): ").strip().lower()
            if choice == 'y':
                resume = True
                logger.info("Resuming previous run...")
            else:
                # Clear the existing transaction file
                txn_file = abs_root_dir / MAIN_TRANSACTION_FILE_NAME
                try:
                    if txn_file.exists():
                        txn_file.unlink()
                        logger.info("Previous transaction file cleared.")
                except Exception as e:
                    logger.error(f"Error clearing transaction file: {e}")
                    return

    if skip_file_renaming and skip_folder_renaming and skip_content:
        logger.info("All processing types (file rename, folder rename, content) are skipped. Nothing to do.")
        return

    try:
        if not any(abs_root_dir.iterdir()):
            logger.info(f"Target directory '{abs_root_dir}' is empty. Nothing to do.")
            return
    except FileNotFoundError: 
        logger.error(f"Error: Root directory '{abs_root_dir}' disappeared before empty check.")
        return
    except OSError as e: 
        logger.error(f"Error accessing directory '{abs_root_dir}' for empty check: {e}")
        return

    # Validate mapping file path
    try:
        map_file_path = Path(mapping_file).resolve(strict=False)
    except Exception as e:
        logger.error(f"Error: Invalid mapping file path '{mapping_file}': {e}")
        return
        
    if not map_file_path.is_file():
        logger.error(f"Error: Mapping file '{map_file_path}' not found or is not a file.")
        return
        
    if not replace_logic.load_replacement_map(map_file_path, logger=logger): 
        logger.error(f"Aborting due to issues with replacement mapping file: {map_file_path}")
        return
    
    # Type-safety reinforcement
    if not isinstance(replace_logic._RAW_REPLACEMENT_MAPPING, dict):
        logger.error("Critical Error: Replacement mapping has invalid type!")
        return
        
    if not replace_logic._MAPPING_LOADED: 
        logger.error(f"Critical Error: Map {map_file_path} not loaded by replace_logic.")
        return

    # Display mapping table and get confirmation (unless in quiet mode or force mode)
    if not quiet_mode and not force_execution and replace_logic._RAW_REPLACEMENT_MAPPING:
        _print_mapping_table(replace_logic._RAW_REPLACEMENT_MAPPING, logger)
        
        operations_desc = _get_operation_description(skip_file_renaming, skip_folder_renaming, skip_content)
        print(f"\n{BLUE}This will replace the strings in the 'Search' column with those in the 'Replace' column.{RESET}")
        print(f"{BLUE}Operations will be performed on: {operations_desc}{RESET}")
        
        if dry_run:
            print(f"{DIM}(DRY RUN - no actual changes will be made){RESET}")
        
        confirm = input("\nDo you want to proceed? (y/n): ").strip().lower()
        if confirm != 'y':
            logger.info("Operation cancelled by user.")
            return

    # Consolidated empty map check
    if not replace_logic._RAW_REPLACEMENT_MAPPING:
        if not (skip_file_renaming or skip_folder_renaming or skip_content):
            logger.info("Map is empty and no operations are configured that would proceed without map rules. Nothing to execute.")
            return
        else:
            logger.info("Map is empty. No string-based replacements will occur.")

    elif not replace_logic.get_scan_pattern() and replace_logic._RAW_REPLACEMENT_MAPPING :
         logger.error("Critical Error: Map loaded but scan regex pattern compilation failed or resulted in no patterns.")
         return
    
    txn_json_path: Path = abs_root_dir / MAIN_TRANSACTION_FILE_NAME
    final_ignore_spec: pathspec.PathSpec | None = None
    raw_patterns_list: list[str] = []
    if use_gitignore:
        gitignore_path = abs_root_dir / ".gitignore"
        if gitignore_path.is_file():
            if not quiet_mode:
                print(f"{GREEN}✓ Found .gitignore file - exclusion patterns will be applied{RESET}")
            logger.info(f"Using .gitignore file: {gitignore_path}")
            try:
                with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f_git:
                    raw_patterns_list.extend(p for p in (line.strip() for line in f_git) if p and not p.startswith('#'))
            except Exception as e:
                logger.warning(f"{YELLOW}Warning: Could not read .gitignore file {gitignore_path}: {e}{RESET}")
        elif not quiet_mode:
            logger.info(".gitignore not found in root, skipping.") 
    if custom_ignore_file_path and use_gitignore:
        custom_ignore_abs_path = Path(custom_ignore_file_path).resolve()
        if custom_ignore_abs_path.is_file():
            logger.info(f"Using custom ignore file: {custom_ignore_abs_path}")
            try:
                with open(custom_ignore_abs_path, 'r', encoding='utf-8', errors='ignore') as f_custom:
                    raw_patterns_list.extend(p for p in (line.strip() for line in f_custom) if p and not p.startswith('#'))
            except Exception as e:
                logger.warning(f"{YELLOW}Warning: Could not read custom ignore file {custom_ignore_abs_path}: {e}{RESET}")
        else:
            logger.error(f"Ignore file not found: {custom_ignore_abs_path}. Aborting")
            return
    if raw_patterns_list:
        try: 
            final_ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', raw_patterns_list)
            logger.info(f"Loaded {len(raw_patterns_list)} ignore patterns rules from specified files.")
        except Exception as e: 
            logger.error(f"Error compiling combined ignore patterns: {e}")
            final_ignore_spec = None 

    # Confirmation prompt. Suppressed by dry_run, force_execution, resume, quiet_mode, or interactive_mode.
    if not dry_run and not force_execution and not resume and not quiet_mode and not interactive_mode: 
        print(f"{BLUE}--- Proposed Operation ---{RESET}")
        print(f"Root Directory: {abs_root_dir}")
        print(f"Replacement Map File: {map_file_path}")
        if replace_logic._RAW_REPLACEMENT_MAPPING:
            print(f"Loaded {len(replace_logic._RAW_REPLACEMENT_MAPPING)} replacement rules.")
        else:
            print("Replacement map is empty. No string replacements will occur.")
        print(f"File Extensions for content scan: {extensions if extensions else 'All non-binary (heuristic)'}")
        print(f"Exclude Dirs (explicit): {exclude_dirs}")
        print(f"Exclude Files (explicit): {exclude_files}")
        if use_gitignore:
            print(f"Using .gitignore: Yes (if found at {abs_root_dir / '.gitignore'})")
        if custom_ignore_file_path:
            print(f"Custom Ignore File: {custom_ignore_file_path}")
        if final_ignore_spec:
            print(f"Effective ignore patterns: {len(final_ignore_spec.patterns)} compiled from ignore files.") # type: ignore
        
        symlink_processing_message = "Symlinks will be ignored (names not renamed, targets not processed for content)." if ignore_symlinks_arg else "Symlink names WILL BE PROCESSED for renaming; targets not processed for content."
        print(f"Symlink Handling: {symlink_processing_message}")

        print(f"Skip File Renaming: {skip_file_renaming}")
        print(f"Skip Folder Renaming: {skip_folder_renaming}")
        print(f"Skip Content Modification: {skip_content}")
        print(f"Retry Timeout: {timeout_minutes} minutes (0 for indefinite retries)")
        print(f"{BLUE}-------------------------{RESET}")
        import sys
        sys.stdout.flush()
        if not replace_logic._RAW_REPLACEMENT_MAPPING and (skip_file_renaming or not extensions) and (skip_folder_renaming or not extensions) and skip_content:
                 print(f"{YELLOW}Warning: No replacement rules and no operations enabled that don't require rules. Likely no operations will be performed.{RESET}")
        
        confirm = input("Proceed with these changes? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled by user.")
            logger.info("Operation cancelled by user via prompt.")
            return

    if not skip_scan:
        logger.info(f"Scanning '{abs_root_dir}'...")
        current_txns_for_resume: list[dict[str, Any]] | None = None
        paths_to_force_rescan: set[str] = set()
        if resume and txn_json_path.exists(): 
            logger.info(f"Resume: Loading existing txns from {txn_json_path}...")
            current_txns_for_resume = load_transactions(txn_json_path, logger=logger) 
            if not skip_scan and dry_run:
                # Always force rescan when resuming dry run
                logger.info("Resume+dry_run: Forcing full rescan of modified files")
                paths_to_force_rescan = set("*")  # Rescan everything
            if current_txns_for_resume is None:
                logger.warning(f"{YELLOW}Warn: Could not load txns. Fresh scan.{RESET}")
            elif not current_txns_for_resume:
                logger.warning(f"{YELLOW}Warn: Txn file empty. Fresh scan.{RESET}")
            else:
                logger.info("Checking for files modified since last processing...")
                path_last_processed_time: dict[str, float] = {} 
                for tx in current_txns_for_resume: 
                    tx_ts = tx.get("timestamp_processed", 0.0)
                    if tx.get("STATUS") in [TransactionStatus.COMPLETED.value, TransactionStatus.FAILED.value] and tx_ts > 0:
                         path_last_processed_time[tx["PATH"]] = max(path_last_processed_time.get(tx["PATH"],0.0), tx_ts)
                
                for item_fs in abs_root_dir.rglob("*"):
                    try: 
                        if item_fs.is_file() and not item_fs.is_symlink():
                            rel_p = str(item_fs.relative_to(abs_root_dir)).replace("\\","/")
                            if final_ignore_spec and final_ignore_spec.match_file(rel_p): 
                                continue 
                            mtime = item_fs.stat().st_mtime
                            if rel_p in path_last_processed_time and mtime > path_last_processed_time[rel_p]:
                                logger.info(f"File '{rel_p}' (mtime:{mtime:.0f}) modified after last process (ts:{path_last_processed_time[rel_p]:.0f}). Re-scan.")
                                paths_to_force_rescan.add(rel_p)
                    except OSError as e: 
                        logger.warning(f"Could not access or stat {item_fs} during resume check: {e}")
                    except Exception as e: 
                        logger.warning(f"Unexpected error processing {item_fs} during resume check: {e}")
        
        found_txns = scan_directory_for_occurrences(
            root_dir=abs_root_dir, excluded_dirs=exclude_dirs, excluded_files=exclude_files,
            file_extensions=extensions, ignore_symlinks=ignore_symlinks_arg,
            ignore_spec=final_ignore_spec, 
            resume_from_transactions=current_txns_for_resume if resume else None,
            paths_to_force_rescan=paths_to_force_rescan if resume else None,
            skip_file_renaming=skip_file_renaming, skip_folder_renaming=skip_folder_renaming, skip_content=skip_content,
            logger=logger 
        )
        
        save_transactions(found_txns or [], txn_json_path, logger=logger) 
        logger.info(f"Scan complete. {len(found_txns or [])} transactions planned in '{txn_json_path}'")
        if not found_txns:
            logger.info("No actionable occurrences found by scan." if replace_logic._RAW_REPLACEMENT_MAPPING else "Map empty and no scannable items found, or all items ignored.")
            return
    elif not txn_json_path.exists(): 
        logger.error(f"Error: --skip-scan used, but '{txn_json_path}' not found.")
        return
    else: 
        logger.info(f"Using existing transaction file: '{txn_json_path}'. Ensure it was generated with compatible settings.")


    txns_for_exec = load_transactions(txn_json_path, logger=logger) 
    if not txns_for_exec: 
        logger.info(f"No transactions found in {txn_json_path} to execute. Exiting.")
        return
    
    # Validate transaction structure
    required_fields = ["id", "TYPE", "PATH", "STATUS"]
    for tx in txns_for_exec:
        missing_fields = [f for f in required_fields if f not in tx]
        if missing_fields:
            logger.error(f"Invalid transaction missing fields {missing_fields}: {tx}")
            return

    # Reset DRY_RUN completed transactions to PENDING for resume
    for tx in txns_for_exec:
        if tx["STATUS"] == TransactionStatus.COMPLETED.value and tx.get("ERROR_MESSAGE") == "DRY_RUN":
            tx["STATUS"] = TransactionStatus.PENDING.value
            tx.pop("ERROR_MESSAGE", None)

    op_type = "Dry run" if dry_run else "Execution"
    logger.info(f"{op_type}: Simulating execution of transactions..." if dry_run else "Starting execution phase...")
    stats = execute_all_transactions(txn_json_path, abs_root_dir, dry_run, resume, timeout_minutes,
                                     skip_file_renaming, skip_folder_renaming, skip_content,
                                     interactive_mode, logger=logger) 
    logger.info(f"{op_type} phase complete. Stats: {stats}")
    logger.info(f"Review '{txn_json_path}' for a detailed log of changes and their statuses.")
    
    binary_log = abs_root_dir / BINARY_MATCHES_LOG_FILE
    if binary_log.exists() and binary_log.stat().st_size > 0:
        logger.info(f"{YELLOW}Note: Matches were found in binary files. See '{binary_log}' for details. Binary file content was NOT modified.{RESET}")
    
    collisions_log = abs_root_dir / COLLISIONS_ERRORS_LOG_FILE
    if collisions_log.exists() and collisions_log.stat().st_size > 0:
        logger.info(f"{RED}Warning: File/folder rename collisions were detected. See '{collisions_log}' for details. These renames were skipped.{RESET}")


def _run_subprocess_command(command: list[str], description: str) -> bool:
    """Helper to run a subprocess command and print status."""
    import subprocess
    print(f"{BLUE}Running: {' '.join(command)}{RESET}")
    try:
        process = subprocess.run(command, check=False, capture_output=True, text=True)
        if process.stdout:
            print(f"{GREEN}Output from {description}:{RESET}\n{process.stdout}")
        if process.stderr: 
            print(f"{YELLOW}Errors/Warnings from {description}:{RESET}\n{process.stderr}")
        if process.returncode != 0:
            print(f"{RED}Error: {description} failed with return code {process.returncode}.{RESET}")
            return False
        print(f"{GREEN}{description} completed successfully.{RESET}")
        return True
    except FileNotFoundError:
        print(f"{RED}Error: Command for {description} not found. Is it installed and in PATH? ({command[0]}){RESET}")
        return False
    except Exception as e:
        print(f"{RED}An unexpected error occurred while running {description}: {e}{RESET}")
        return False


def main_cli() -> None:
    import sys
    import traceback
    import importlib.util
    import argparse
    # Imports moved to top of file

    # Check required dependencies
    required_deps = [("prefect", "prefect"), ("chardet", "chardet")]
    for module_name, display_name in required_deps:
        try:
            if importlib.util.find_spec(module_name) is None:
                sys.stderr.write(f"{RED}CRITICAL ERROR: Missing core dependency: {display_name}. "
                               f"Please install all required packages (e.g., via 'uv sync').{RESET}\n")
                sys.exit(1)
        except ImportError:
            sys.stderr.write(f"{RED}CRITICAL ERROR: Missing core dependency: {display_name} "
                           f"(import error during check). Please install all required packages.{RESET}\n")
            sys.exit(1)

    parser = argparse.ArgumentParser(
        description=f"{SCRIPT_NAME}\nFind and replace strings in files and filenames/foldernames within a project directory. "
                    "It operates in three phases: Scan, Plan (creating a transaction log), and Execute. "
                    "The process is designed to be resumable and aims for surgical precision in replacements. "
                    f"Binary file content is NOT modified; matches within them are logged to '{BINARY_MATCHES_LOG_FILE}'.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("directory", nargs='?', default=".", help="Root directory to process (default: current directory).")
    parser.add_argument("--mapping-file", default=DEFAULT_REPLACEMENT_MAPPING_FILE, help=f"Path to the JSON file with replacement mappings (default: ./{DEFAULT_REPLACEMENT_MAPPING_FILE}).")
    parser.add_argument("--extensions", nargs="+", help="List of file extensions for content scan (e.g. .py .txt .rtf). Default: attempts to process recognized text-like files.")
    parser.add_argument("--exclude-dirs", nargs="+", default=[".git",".venv","venv","node_modules","__pycache__"], help="Directory names to exclude (space-separated). Default: .git .venv etc.")
    parser.add_argument("--exclude-files", nargs="+", default=[], help="Specific files or relative paths to exclude (space-separated).")
    
    ignore_group = parser.add_argument_group('Ignore File Options')
    ignore_group.add_argument("--no-gitignore", action="store_false", dest="use_gitignore", default=True,
                             help="Disable using .gitignore file for exclusions. Custom ignore files will also be skipped.")
    ignore_group.add_argument("--ignore-file", dest="custom_ignore_file", metavar="PATH", help="Path to a custom .gitignore-style file for additional exclusions.")
    
    symlink_group = parser.add_argument_group('Symlink Handling')
    symlink_group.add_argument("--process-symlink-names", action="store_true", 
                               help="If set, symlink names WILL BE PROCESSED for renaming. "
                                    "Default: symlink names are NOT processed for renaming. "
                                    "Symlink targets are never followed for content modification by this script.")
    
    skip_group = parser.add_argument_group('Skip Operation Options')
    skip_group.add_argument("--skip-file-renaming", action="store_true", help="Skip all file renaming operations.")
    skip_group.add_argument("--skip-folder-renaming", action="store_true", help="Skip all folder renaming operations.")
    skip_group.add_argument("--skip-content", action="store_true", help="Skip all file content modifications. If all three --skip-* options are used, the script will exit with 'nothing to do'.")

    execution_group = parser.add_argument_group('Execution Control')
    execution_group.add_argument("--dry-run", action="store_true", help="Scan and plan changes, but do not execute them. Reports what would be changed.")
    execution_group.add_argument("--skip-scan", action="store_true", help=f"Skip scan phase; use existing '{MAIN_TRANSACTION_FILE_NAME}' in the root directory for execution.")
    execution_group.add_argument("--resume", action="store_true", help="Resume operation from existing transaction file, attempting to complete pending/failed items and scan for new/modified ones.")
    execution_group.add_argument("--force", "--yes", "-y", action="store_true", help="Force execution without confirmation prompt (use with caution).")
    execution_group.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode, prompting for approval before each change.")
    parser.add_argument("--timeout", type=float, default=10.0, metavar="MINUTES",
                        help="Maximum minutes for the retry phase when files are locked/inaccessible. "
                             "Set to 0 for indefinite retries (until CTRL-C). Minimum 1 minute if not 0. Default: 10 minutes.")
    
    output_group = parser.add_argument_group('Output Control')
    output_group.add_argument("--quiet", "-q", action="store_true", help="Suppress initial script name print and some informational messages from direct print statements (Prefect logs are separate). Also suppresses the confirmation prompt, implying 'yes'.")
    output_group.add_argument("--verbose", action="store_true", help="Enable more verbose output, setting Prefect logger to DEBUG level.")
    
    dev_group = parser.add_argument_group('Developer Options')
    dev_group.add_argument("--self-test", action="store_true", help="Run automated tests for this script.")

    args = parser.parse_args()

    if args.self_test:
        print(f"{BLUE}--- Running Self-Tests ---{RESET}")
        
        # Try installing with uv first, then fallback to pip
        install_cmd_uv = [sys.executable, "-m", "uv", "pip", "install", "-e", ".[dev]"]
        install_cmd_pip = [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]
        
        print(f"{BLUE}Attempting to install/update dev dependencies using 'uv'...{RESET}")
        install_success = _run_subprocess_command(install_cmd_uv, "uv dev dependency installation")
        
        if not install_success:
            print(f"{YELLOW}'uv' command failed or not found. Attempting with 'pip'...{RESET}")
            install_success = _run_subprocess_command(install_cmd_pip, "pip dev dependency installation")

        if not install_success:
            print(f"{RED}Failed to install dev dependencies. Aborting self-tests.{RESET}")
            sys.exit(1)
            
        pytest_cmd = ["pytest", "test_mass_find_replace.py"]  # Use system pytest
        print(f"{BLUE}Running pytest...{RESET}")
        test_passed = _run_subprocess_command(pytest_cmd, "pytest execution")
        sys.exit(0 if test_passed else 1)

    if not args.quiet:
        print(f"{BLUE}{SCRIPT_NAME}{RESET}")

    timeout_val_for_flow: int
    if args.timeout < 0:
        parser.error("--timeout cannot be negative.") 
    if args.timeout == 0:
        timeout_val_for_flow = 0
    elif args.timeout < 1.0:
        if not args.quiet:
            print(f"{YELLOW}Warning: --timeout value {args.timeout} increased to minimum 1 minute.{RESET}")
        timeout_val_for_flow = 1
    else:
        timeout_val_for_flow = int(args.timeout)

    # Validate ignore file if gitignore is enabled
    if args.custom_ignore_file and args.use_gitignore:
        ignore_path = Path(args.custom_ignore_file)
        if not ignore_path.exists() or not ignore_path.is_file():
            sys.stderr.write(f"{RED}Error: Ignore file not found: {args.custom_ignore_file}{RESET}\n")
            sys.exit(1)

    auto_exclude_basenames = [
        MAIN_TRANSACTION_FILE_NAME,
        Path(args.mapping_file).name, 
        BINARY_MATCHES_LOG_FILE,
        COLLISIONS_ERRORS_LOG_FILE,
        MAIN_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT
    ]
    # Remove duplicates while preserving order
    seen = set()
    final_exclude_files = []
    for item in args.exclude_files + auto_exclude_basenames:
        if item not in seen:
            seen.add(item)
            final_exclude_files.append(item)
    
    if args.verbose and not args.quiet:
        print("Verbose mode requested. Prefect log level will be set to DEBUG if flow runs.")

    ignore_symlinks_param = not args.process_symlink_names

    main_flow(args.directory, args.mapping_file, args.extensions, args.exclude_dirs, final_exclude_files,
              args.dry_run, args.skip_scan, args.resume, args.force, ignore_symlinks_param,
              args.use_gitignore, args.custom_ignore_file,
              args.skip_file_renaming, args.skip_folder_renaming, args.skip_content, 
              timeout_val_for_flow, 
              args.quiet,
              args.verbose,
              args.interactive
             )

if __name__ == "__main__":
    import sys
    import traceback
    try:
        main_cli()
    except Exception as e: 
        sys.stderr.write(RED + f"An unexpected error occurred in __main__: {e}" + RESET + "\n")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
        
