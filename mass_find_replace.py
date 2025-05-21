#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `main_flow`: Changed type hint for `path_last_processed_time` from `Dict[str, float]` to `dict[str, float]`.
# - `main_flow`: Added `verbose_mode` parameter. If True, the Prefect run logger's level is set to `logging.DEBUG`.
# - `main_cli`: Passed `args.verbose` to `main_flow` for the new `verbose_mode` parameter.
# - `main_cli`: Added a comment to clarify that `quiet_mode` also suppresses the confirmation prompt.
# - Removed commented-out `import logging` and `import prefect.runtime`.
# - Passed the Prefect logger from `main_flow` to `replace_logic.load_replacement_map`
#   and to `file_system_operations` functions (`scan_directory_for_occurrences`,
#   `load_transactions`, `save_transactions`, `execute_all_transactions`).
# - Changed `argparse` type for `--timeout` from `int` to `float` to allow inputs like "0.5".
# - Added `int()` casting for `args.timeout` before passing to `main_flow` if it's not 0.
# - Moved import checks from `if __name__ == "__main__":` block to the beginning of `main_cli()`.
# - Removed redundant import checks for `prefect`, `chardet`, `pathspec`, `striprtf`, `isbinary`
#   from `main_cli` because these are already handled by top-level imports in `mass_find_replace.py`
#   or `file_system_operations.py`. If these modules are missing, an `ImportError` will occur
#   when the script is first loaded, before `main_cli` is even called.
# - Corrected F821 Undefined name error: `abs_r_dir` changed to `abs_root_dir` in `main_flow` when calling `execute_all_transactions`.
# - `main_flow`: Added try-except OSError around file checking loop in resume logic to handle stat errors gracefully.
# - `main_cli`: Re-added import checks for critical dependencies (`prefect`, `chardet`) at the beginning of the function.
# - `main_flow`: Added call to `replace_logic.reset_module_state()` before loading map.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import argparse
from pathlib import Path
import sys
import logging # Added for setting logger level
from typing import Any # Keep Any if specifically needed
import json
import traceback
import time 
import pathspec 

from prefect import flow, get_run_logger

from file_system_operations import (
    scan_directory_for_occurrences, save_transactions, load_transactions,
    execute_all_transactions, TransactionStatus, TransactionType,
    TRANSACTION_FILE_BACKUP_EXT, BINARY_MATCHES_LOG_FILE,
    load_ignore_patterns 
)
import replace_logic

SCRIPT_NAME = "MFR - Mass Find Replace - A script to safely rename things in your project"
MAIN_TRANSACTION_FILE_NAME = "planned_transactions.json"
DEFAULT_REPLACEMENT_MAPPING_FILE = "replacement_mapping.json"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
YELLOW = "\033[93m"
BLUE = "\033[94m"

@flow(name="Mass Find and Replace Orchestration Flow", log_prints=True)
def main_flow(
    directory: str, mapping_file: str, extensions: list[str] | None,
    exclude_dirs: list[str], exclude_files: list[str],
    dry_run: bool, skip_scan: bool, resume: bool, force_execution: bool,
    ignore_symlinks_arg: bool, use_gitignore: bool, custom_ignore_file_path: str | None,
    skip_file_renaming: bool, skip_folder_renaming: bool, skip_content: bool,
    timeout_minutes: int, 
    quiet_mode: bool,
    verbose_mode: bool # Added for controlling logger verbosity
):
    logger = get_run_logger()
    if verbose_mode:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled. Logger set to DEBUG level.")
    
    # Explicitly reset replace_logic module state before any operations for this flow run
    replace_logic.reset_module_state()

    abs_root_dir = Path(directory).resolve(strict=False) 
    if not abs_root_dir.is_dir(): 
        logger.error(f"Error: Root directory '{abs_root_dir}' not found or not a directory.")
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

    map_file_path = Path(mapping_file).resolve()
    if not replace_logic.load_replacement_map(map_file_path, logger=logger): 
        logger.error(f"Aborting due to issues with replacement mapping file: {map_file_path}")
        return
    if not replace_logic._MAPPING_LOADED: 
        logger.error(f"Critical Error: Map {map_file_path} not loaded by replace_logic.")
        return
    if not replace_logic._RAW_REPLACEMENT_MAPPING: 
        logger.warning(f"{YELLOW}Warning: Map {map_file_path} is empty. No string replacements will occur based on map keys.{RESET}")
    elif not replace_logic.get_scan_pattern() and replace_logic._RAW_REPLACEMENT_MAPPING :
         logger.error("Critical Error: Map loaded but scan regex pattern compilation failed or resulted in no patterns.")
         return
    
    txn_json_path: Path = abs_root_dir / MAIN_TRANSACTION_FILE_NAME
    final_ignore_spec: pathspec.PathSpec | None = None
    raw_patterns_list: list[str] = []
    if use_gitignore:
        gitignore_path = abs_root_dir / ".gitignore"
        if gitignore_path.is_file():
            logger.info(f"Using .gitignore file: {gitignore_path}")
            try:
                with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f_git:
                    raw_patterns_list.extend(p for p in (line.strip() for line in f_git) if p and not p.startswith('#'))
            except Exception as e:
                logger.warning(f"{YELLOW}Warning: Could not read .gitignore file {gitignore_path}: {e}{RESET}")
        elif not quiet_mode:
            logger.info(".gitignore not found in root, skipping.") 
    if custom_ignore_file_path:
        custom_ignore_abs_path = Path(custom_ignore_file_path).resolve()
        if custom_ignore_abs_path.is_file():
            logger.info(f"Using custom ignore file: {custom_ignore_abs_path}")
            try:
                with open(custom_ignore_abs_path, 'r', encoding='utf-8', errors='ignore') as f_custom:
                    raw_patterns_list.extend(p for p in (line.strip() for line in f_custom) if p and not p.startswith('#'))
            except Exception as e:
                logger.warning(f"{YELLOW}Warning: Could not read custom ignore file {custom_ignore_abs_path}: {e}{RESET}")
        else:
            logger.warning(f"{YELLOW}Warning: Custom ignore file '{custom_ignore_abs_path}' not found.{RESET}")
    if raw_patterns_list:
        try: 
            final_ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', raw_patterns_list)
            logger.info(f"Loaded {len(raw_patterns_list)} ignore patterns rules from specified files.")
        except Exception as e: 
            logger.error(f"Error compiling combined ignore patterns: {e}")
            final_ignore_spec = None 

    # Confirmation prompt. Suppressed by dry_run, force_execution, resume, or quiet_mode.
    # Note: quiet_mode suppressing an interactive prompt is a specific design choice here.
    if not dry_run and not force_execution and not resume and not quiet_mode: 
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
        print(f"Ignore Symlinks: {ignore_symlinks_arg}")
        print(f"Skip File Renaming: {skip_file_renaming}")
        print(f"Skip Folder Renaming: {skip_folder_renaming}")
        print(f"Skip Content Modification: {skip_content}")
        print(f"Retry Timeout: {timeout_minutes} minutes (0 for indefinite)")
        print(f"{BLUE}-------------------------{RESET}")
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
        current_txns_for_resume: list[dict[str,Any]] | None = None
        paths_to_force_rescan: set[str] = set()
        if resume and txn_json_path.exists(): 
            logger.info(f"Resume: Loading existing txns from {txn_json_path}...")
            current_txns_for_resume = load_transactions(txn_json_path, logger=logger) 
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
        logger.error(f"Error: --skip-scan was used, but '{txn_json_path}' not found.")
        return
    else: 
        logger.info(f"Using existing transaction file: '{txn_json_path}'. Ensure it was generated with compatible settings.")

    if not replace_logic._RAW_REPLACEMENT_MAPPING and not skip_file_renaming and not skip_folder_renaming and not skip_content:
        logger.info("Map is empty and no operations are configured that would proceed without map rules. Nothing to execute.")
        if not (skip_file_renaming and skip_folder_renaming and skip_content):
             logger.info("Map is empty. No string-based replacements will occur.")

    txns_for_exec = load_transactions(txn_json_path, logger=logger) 
    if not txns_for_exec: 
        logger.info(f"No transactions found in {txn_json_path} to execute. Exiting.")
        return

    op_type = "Dry run" if dry_run else "Execution"
    logger.info(f"{op_type}: Simulating execution of transactions..." if dry_run else "Starting execution phase...")
    stats = execute_all_transactions(txn_json_path, abs_root_dir, dry_run, resume, timeout_minutes,
                                     skip_file_renaming, skip_folder_renaming, skip_content,
                                     skip_scan, logger=logger) 
    logger.info(f"{op_type} phase complete. Stats: {stats}")
    logger.info(f"Review '{txn_json_path}' for a detailed log of changes and their statuses.")
    
    binary_log = abs_root_dir / BINARY_MATCHES_LOG_FILE
    if binary_log.exists() and binary_log.stat().st_size > 0:
        logger.info(f"{YELLOW}Note: Matches were found in binary files. See '{binary_log}' for details. Binary file content was NOT modified.{RESET}")


def main_cli() -> None:
    try:
        import prefect 
        import chardet 
    except ImportError as e:
        sys.stderr.write(RED + f"CRITICAL ERROR: Missing core dependencies: {e}. Please install all required packages (e.g., via 'uv sync')." + RESET + "\n")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description=f"{SCRIPT_NAME}\nFind and replace strings in files and filenames/foldernames within a project directory. "
                    "It operates in three phases: Scan, Plan (creating a transaction log), and Execute. "
                    "The process is designed to be resumable and aims for surgical precision in replacements. "
                    f"Binary file contents are NOT modified; matches within them are logged to '{BINARY_MATCHES_LOG_FILE}'.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("directory", nargs='?', default=".", help="Root directory to process (default: current directory).")
    parser.add_argument("--mapping-file", default=DEFAULT_REPLACEMENT_MAPPING_FILE, help=f"Path to the JSON file with replacement mappings (default: ./{DEFAULT_REPLACEMENT_MAPPING_FILE}).")
    parser.add_argument("--extensions", nargs="+", help="List of file extensions for content scan (e.g. .py .txt .rtf). Default: attempts to process recognized text-like files.")
    parser.add_argument("--exclude-dirs", nargs="+", default=[".git",".venv","venv","node_modules","__pycache__"], help="Directory names to exclude (space-separated). Default: .git .venv etc.")
    parser.add_argument("--exclude-files", nargs="+", default=[], help="Specific files or relative paths to exclude (space-separated).")
    
    ignore_group = parser.add_argument_group('Ignore File Options')
    ignore_group.add_argument("--use-gitignore", action="store_true", help="Use .gitignore file in the root directory for exclusions.")
    ignore_group.add_argument("--ignore-file", dest="custom_ignore_file", metavar="PATH", help="Path to a custom .gitignore-style file for additional exclusions.")
    
    symlink_group = parser.add_argument_group('Symlink Handling')
    symlink_group.add_argument("--ignore-symlinks", action="store_true", help="If set, symlinks will be ignored (not renamed, targets not processed). Default is to rename symlink names but not follow them for content modification.")
    
    skip_group = parser.add_argument_group('Skip Operation Options')
    skip_group.add_argument("--skip-file-renaming", action="store_true", help="Skip all file renaming operations.")
    skip_group.add_argument("--skip-folder-renaming", action="store_true", help="Skip all folder renaming operations.")
    skip_group.add_argument("--skip-content", action="store_true", help="Skip all file content modifications. If all three --skip-* options are used, the script will exit with 'nothing to do'.")

    execution_group = parser.add_argument_group('Execution Control')
    execution_group.add_argument("--dry-run", action="store_true", help="Scan and plan changes, but do not execute them. Reports what would be changed.")
    execution_group.add_argument("--skip-scan", action="store_true", help=f"Skip scan phase; use existing '{MAIN_TRANSACTION_FILE_NAME}' in the root directory for execution.")
    execution_group.add_argument("--resume", action="store_true", help="Resume operation from existing transaction file, attempting to complete pending/failed items and scan for new/modified ones.")
    execution_group.add_argument("--force", "--yes", "-y", action="store_true", help="Force execution without confirmation prompt (use with caution).")
    parser.add_argument("--timeout", type=float, default=10.0, metavar="MINUTES",
                        help="Maximum minutes for the retry phase when files are locked/inaccessible. "
                             "Set to 0 for indefinite retries (until CTRL-C). Minimum 1 minute if not 0. Default: 10 minutes.")
    
    output_group = parser.add_argument_group('Output Control')
    output_group.add_argument("--quiet", "-q", action="store_true", help="Suppress initial script name print and some informational messages from direct print statements (Prefect logs are separate). Also suppresses the confirmation prompt, implying 'yes'.")
    output_group.add_argument("--verbose", action="store_true", help="Enable more verbose output, setting Prefect logger to DEBUG level.")
    args = parser.parse_args()

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


    auto_exclude_basenames = [
        MAIN_TRANSACTION_FILE_NAME,
        Path(args.mapping_file).name, 
        BINARY_MATCHES_LOG_FILE,
        MAIN_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT
    ]
    final_exclude_files = list(set(args.exclude_files + auto_exclude_basenames))
    
    if args.verbose and not args.quiet:
        # This print is for CLI verbosity; Prefect logger verbosity is handled in main_flow
        print("Verbose mode requested. Prefect log level will be set to DEBUG if flow runs.")

    main_flow(args.directory, args.mapping_file, args.extensions, args.exclude_dirs, final_exclude_files,
              args.dry_run, args.skip_scan, args.resume, args.force, args.ignore_symlinks,
              args.use_gitignore, args.custom_ignore_file,
              args.skip_file_renaming, args.skip_folder_renaming, args.skip_content, 
              timeout_val_for_flow, 
              args.quiet,
              args.verbose # Pass verbose flag to the flow
             )

if __name__ == "__main__":
    try:
        main_cli()
    except Exception as e: 
        sys.stderr.write(RED + f"An unexpected error occurred in __main__: {e}" + RESET + "\n")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
        
