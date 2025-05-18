#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Changelog:
# - Added --skip-file-renaming, --skip-folder-renaming, --skip-content CLI options.
# - Added --timeout and --quiet CLI options.
# - Script prints its name on startup (unless --quiet).
# - Early exit if all skip options are true or if target directory is empty.
# - Help text updated for new options and binary log info.
# - `main_flow` passes skip flags and timeout to `execute_all_transactions`.
# - `main_flow` now explicitly checks and reports if BINARY_MATCHES_LOG_FILE was created and has content.
# - Robust binary detection (using `isbinary` library) and RTF text extraction integrated via file_system_operations.

import argparse
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional, Set
import json
import traceback
# import logging # Prefect logger is used primarily
import time 
import pathspec 

from prefect import flow, get_run_logger
# import prefect.runtime # Not strictly needed

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

GREEN = "\033[92m"; RED = "\033[91m"; RESET = "\033[0m"; YELLOW = "\033[93m"; BLUE = "\033[94m"

@flow(name="Mass Find and Replace Orchestration Flow", log_prints=True)
def main_flow(
    directory: str, mapping_file: str, extensions: Optional[List[str]], 
    exclude_dirs: List[str], exclude_files: List[str], 
    dry_run: bool, skip_scan: bool, resume: bool, force_execution: bool, 
    ignore_symlinks_arg: bool, use_gitignore: bool, custom_ignore_file_path: Optional[str],
    skip_file_renaming: bool, skip_folder_renaming: bool, skip_content: bool,
    timeout_minutes: int
):
    logger = get_run_logger()
    abs_root_dir = Path(directory).resolve(strict=False) 
    if not abs_root_dir.is_dir(): 
        logger.error(f"Error: Root directory '{abs_root_dir}' not found or not a directory."); return

    if skip_file_renaming and skip_folder_renaming and skip_content:
        logger.info("All processing types (file rename, folder rename, content) are skipped. Nothing to do.")
        return

    try:
        if not any(abs_root_dir.iterdir()): # Check if dir is physically empty
            # This check is before ignore patterns are applied.
            # scan_directory_for_occurrences will return [] if it's effectively empty post-ignores.
            logger.info(f"Target directory '{abs_root_dir}' appears empty. Nothing to do.")
            return
    except FileNotFoundError: 
        logger.error(f"Error: Root directory '{abs_root_dir}' disappeared before empty check."); return
    except OSError as e: 
        logger.error(f"Error accessing directory '{abs_root_dir}' for empty check: {e}"); return

    map_file_path = Path(mapping_file).resolve()
    if not replace_logic.load_replacement_map(map_file_path):
        logger.error(f"Aborting due to issues with replacement mapping file: {map_file_path}"); return
    if not replace_logic._MAPPING_LOADED: 
        logger.error(f"Critical Error: Map {map_file_path} not loaded by replace_logic."); return
    if not replace_logic._RAW_REPLACEMENT_MAPPING: 
        logger.warning(f"{YELLOW}Warning: Map {map_file_path} is empty. No string replacements will occur based on map keys.{RESET}")
    elif not replace_logic.get_scan_pattern() and replace_logic._RAW_REPLACEMENT_MAPPING : # Should not happen if _RAW_REPLACEMENT_MAPPING is populated
         logger.error("Critical Error: Map loaded but scan regex pattern compilation failed or resulted in no patterns."); return
    
    txn_json_path = abs_root_dir / MAIN_TRANSACTION_FILE_NAME
    final_ignore_spec: Optional[pathspec.PathSpec] = None
    raw_patterns_list: List[str] = []
    if use_gitignore:
        gitignore_path = abs_root_dir / ".gitignore"
        if gitignore_path.is_file():
            logger.info(f"Using .gitignore file: {gitignore_path}")
            try:
                with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f_git:
                    raw_patterns_list.extend(p for p in (line.strip() for line in f_git) if p and not p.startswith('#'))
            except Exception as e:
                logger.warning(f"{YELLOW}Warning: Could not read .gitignore file {gitignore_path}: {e}{RESET}")
        else: logger.info(".gitignore not found in root, skipping.")
    if custom_ignore_file_path:
        custom_ignore_abs_path = Path(custom_ignore_file_path).resolve()
        if custom_ignore_abs_path.is_file():
            logger.info(f"Using custom ignore file: {custom_ignore_abs_path}")
            try:
                with open(custom_ignore_abs_path, 'r', encoding='utf-8', errors='ignore') as f_custom:
                    raw_patterns_list.extend(p for p in (line.strip() for line in f_custom) if p and not p.startswith('#'))
            except Exception as e:
                logger.warning(f"{YELLOW}Warning: Could not read custom ignore file {custom_ignore_abs_path}: {e}{RESET}")
        else: logger.warning(f"{YELLOW}Warning: Custom ignore file '{custom_ignore_abs_path}' not found.{RESET}")
    if raw_patterns_list:
        try: 
            final_ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', raw_patterns_list)
            logger.info(f"Loaded {len(raw_patterns_list)} ignore patterns rules from specified files.")
        except Exception as e: 
            logger.error(f"Error compiling combined ignore patterns: {e}")
            final_ignore_spec = None 

    if not dry_run and not force_execution and not resume:
        print(f"{BLUE}--- Proposed Operation ---{RESET}")
        print(f"Root Directory: {abs_root_dir}")
        print(f"Replacement Map File: {map_file_path}")
        if replace_logic._RAW_REPLACEMENT_MAPPING: print(f"Loaded {len(replace_logic._RAW_REPLACEMENT_MAPPING)} replacement rules.")
        else: print("Replacement map is empty. No string replacements will occur.")
        print(f"File Extensions for content scan: {extensions if extensions else 'All non-binary (heuristic)'}")
        print(f"Exclude Dirs (explicit): {exclude_dirs}")
        print(f"Exclude Files (explicit): {exclude_files}")
        if use_gitignore: print(f"Using .gitignore: Yes (if found at {abs_root_dir / '.gitignore'})")
        if custom_ignore_file_path: print(f"Custom Ignore File: {custom_ignore_file_path}")
        if final_ignore_spec: print(f"Effective ignore patterns: {len(final_ignore_spec.patterns)} compiled from ignore files.")
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
        if confirm.lower() != 'yes': print("Operation cancelled by user."); return

    if not skip_scan:
        logger.info(f"Scanning '{abs_root_dir}'...")
        current_txns_for_resume: Optional[List[Dict[str,Any]]] = None; paths_to_force_rescan: Set[str] = set()
        if resume and txn_json_path.exists():
            logger.info(f"Resume: Loading existing txns from {txn_json_path}...")
            current_txns_for_resume = load_transactions(txn_json_path)
            if current_txns_for_resume is None: logger.warning(f"{YELLOW}Warn: Could not load txns. Fresh scan.{RESET}")
            elif not current_txns_for_resume: logger.warning(f"{YELLOW}Warn: Txn file empty. Fresh scan.{RESET}")
            else:
                logger.info("Checking for files modified since last processing...")
                path_last_processed_time: Dict[str, float] = {}
                for tx in current_txns_for_resume:
                    tx_ts = tx.get("timestamp_processed", 0.0)
                    if tx.get("STATUS") in [TransactionStatus.COMPLETED.value, TransactionStatus.FAILED.value] and tx_ts > 0:
                         path_last_processed_time[tx["PATH"]] = max(path_last_processed_time.get(tx["PATH"],0.0), tx_ts)
                
                for item_fs in abs_root_dir.rglob("*"):
                    if item_fs.is_file() and not item_fs.is_symlink():
                        try:
                            rel_p = str(item_fs.relative_to(abs_root_dir)).replace("\\","/")
                            if final_ignore_spec and final_ignore_spec.match_file(rel_p): continue
                            mtime = item_fs.stat().st_mtime
                            if rel_p in path_last_processed_time and mtime > path_last_processed_time[rel_p]:
                                logger.info(f"File '{rel_p}' (mtime:{mtime:.0f}) modified after last process (ts:{path_last_processed_time[rel_p]:.0f}). Re-scan.")
                                paths_to_force_rescan.add(rel_p)
                        except Exception as e: logger.warning(f"Could not stat {item_fs} for resume: {e}")
        
        found_txns = scan_directory_for_occurrences(
            root_dir=abs_root_dir, excluded_dirs=exclude_dirs, excluded_files=exclude_files,
            file_extensions=extensions, ignore_symlinks=ignore_symlinks_arg,
            ignore_spec=final_ignore_spec, 
            resume_from_transactions=current_txns_for_resume if resume else None,
            paths_to_force_rescan=paths_to_force_rescan if resume else None,
            skip_file_renaming=skip_file_renaming, skip_folder_renaming=skip_folder_renaming, skip_content=skip_content
        )
        
        save_transactions(found_txns or [], txn_json_path)
        logger.info(f"Scan complete. {len(found_txns or [])} transactions planned in '{txn_json_path}'")
        if not found_txns:
            logger.info("No actionable occurrences found by scan." if replace_logic._RAW_REPLACEMENT_MAPPING else "Map empty and no scannable items found, or all items ignored."); return
    elif not txn_json_path.exists(): 
        logger.error(f"Error: --skip-scan was used, but '{txn_json_path}' not found."); return
    else: 
        logger.info(f"Using existing transaction file: '{txn_json_path}'. Ensure it was generated with compatible settings.")

    # If all operations that could use the map are skipped, and map is empty, no string-based changes will happen.
    # This check is slightly different from the one before scan, as here we *have* a transaction list (or skipped scan).
    if not replace_logic._RAW_REPLACEMENT_MAPPING and \
       (skip_file_renaming or skip_folder_renaming) and \
       skip_content:
        logger.info("Map is empty and all relevant operations (renaming, content) are skipped or would rely on an empty map. No string-based changes will occur.")
        # We might still have transactions if --skip-scan was used with an old non-empty map's transaction file.
        # The execution phase will then skip them based on the current empty map.

    txns_for_exec = load_transactions(txn_json_path)
    if not txns_for_exec: 
        logger.info(f"No transactions found in {txn_json_path} to execute. Exiting."); return

    op_type = "Dry run" if dry_run else "Execution"
    logger.info(f"{op_type}: Simulating execution of transactions..." if dry_run else "Starting execution phase...")
    stats = execute_all_transactions(txn_json_path, abs_root_dir, dry_run, resume, timeout_minutes,
                                     skip_file_renaming, skip_folder_renaming, skip_content)
    logger.info(f"{op_type} phase complete. Stats: {stats}")
    logger.info(f"Review '{txn_json_path}' for a detailed log of changes and their statuses.")
    
    binary_log = abs_root_dir / BINARY_MATCHES_LOG_FILE
    if binary_log.exists() and binary_log.stat().st_size > 0:
        logger.info(f"{YELLOW}Note: Matches were found in binary files. See '{binary_log}' for details. Binary file content was NOT modified.{RESET}")


def main_cli() -> None:
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
    execution_group.add_argument("--timeout", type=int, default=10, metavar="MINUTES", 
                        help="Maximum minutes for the retry phase when files are locked/inaccessible. "
                             "Set to 0 for indefinite retries (until CTRL-C). Minimum 1 minute if not 0. Default: 10 minutes.")
    
    output_group = parser.add_argument_group('Output Control')
    output_group.add_argument("--quiet", "-q", action="store_true", help="Suppress initial script name print and some informational messages from direct print statements (Prefect logs are separate).")
    output_group.add_argument("--verbose", action="store_true", help="Enable more verbose output during operation (currently has limited additional effect beyond standard logging).")
    args = parser.parse_args()

    if not args.quiet:
        print(f"{BLUE}{SCRIPT_NAME}{RESET}")

    if args.timeout < 0: parser.error("--timeout cannot be negative.")
    if args.timeout != 0 and args.timeout < 1 :
        if not args.quiet: print(f"{YELLOW}Warning: --timeout value increased to minimum 1 minute.{RESET}")
        args.timeout = 1 

    auto_exclude_basenames = [
        MAIN_TRANSACTION_FILE_NAME,
        Path(args.mapping_file).name, 
        BINARY_MATCHES_LOG_FILE,
        MAIN_TRANSACTION_FILE_NAME + TRANSACTION_FILE_BACKUP_EXT
    ]
    final_exclude_files = list(set(args.exclude_files + auto_exclude_basenames))
    
    if args.verbose and not args.quiet: print("Verbose mode enabled (effect on logging may vary).")

    main_flow(args.directory, args.mapping_file, args.extensions, args.exclude_dirs, final_exclude_files,
              args.dry_run, args.skip_scan, args.resume, args.force, args.ignore_symlinks,
              args.use_gitignore, args.custom_ignore_file,
              args.skip_file_renaming, args.skip_folder_renaming, args.skip_content, args.timeout)

if __name__ == "__main__":
    try:
        missing = []
        try: import prefect
        except ImportError: missing.append("prefect")
        try: import chardet
        except ImportError: missing.append("chardet")
        try: import pathspec
        except ImportError: missing.append("pathspec")
        try: from striprtf.striprtf import rtf_to_text
        except ImportError: missing.append("striprtf")
        try: from isbinary import is_binary_file
        except ImportError: missing.append("isbinary")

        if missing: raise ImportError(f"Missing dependencies: {', '.join(missing)}")
        main_cli()
    except ImportError as e:
        sys.stderr.write(f"CRITICAL ERROR: {e}.\nPlease ensure all dependencies are installed (e.g., pip install prefect chardet pathspec striprtf isbinary).\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(RED + f"An unexpected error occurred in __main__: {e}" + RESET + "\n")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
        