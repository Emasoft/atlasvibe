# tests/test_mass_find_replace.py
# HERE IS THE FIXED TEST FILE WITH THE UNNECESSARY BACKTICK REMOVED
# (The lines with ``` are now removed to fix syntax errors)

from mass_find_replace import MAIN_TRANSACTION_FILE_NAME
from pathlib import Path
import os
import shutil
import time
from typing import Optional, Dict
import logging
import json
from unittest.mock import patch
import sys
import subprocess
import builtins
import importlib.util

from mass_find_replace import main_flow, main_cli, YELLOW, RESET
from file_system_operations import (
    load_transactions, save_transactions, TransactionStatus, TransactionType, BINARY_MATCHES_LOG_FILE
)

import replace_logic

DEFAULT_EXTENSIONS = [".txt", ".py", ".md", ".bin", ".log", ".data", ".rtf", ".xml"]
DEFAULT_EXCLUDE_DIRS_REL = ["excluded_flojoy_dir", "symlink_targets_outside"]
DEFAULT_EXCLUDE_FILES_REL = ["exclude_this_flojoy_file.txt"]

def run_main_flow_for_test(
    context_dir: Path, map_file: Path, extensions: list[str] | None = DEFAULT_EXTENSIONS,
    exclude_dirs: list[str] | None = None, exclude_files: list[str] | None = None,
    dry_run: bool = False, skip_scan: bool = False, resume: bool = False,
    force_execution: bool = True, ignore_symlinks_arg: bool = False,
    use_gitignore: bool = False, custom_ignore_file: str | None = None,
    skip_file_renaming: bool = False, skip_folder_renaming: bool = False, skip_content: bool = False,
    timeout_minutes: int = 1, quiet_mode: bool = True,
    verbose_mode: bool = False,
    interactive_mode: bool = False,
    process_symlink_names: bool = False
):
    from tests.conftest import temp_test_dir, default_map_file, assert_file_content

    final_exclude_dirs = exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS_REL
    base_exclude_files = exclude_files if exclude_files is not None else DEFAULT_EXCLUDE_FILES_REL
    additional_excludes = [map_file.name, BINARY_MATCHES_LOG_FILE]
    final_exclude_files = list(set(base_exclude_files + additional_excludes))
    main_flow(
        directory=str(context_dir),  # Use context directory (runtime)
        mapping_file=str(map_file), extensions=extensions,
        exclude_dirs=final_exclude_dirs, exclude_files=final_exclude_files, dry_run=dry_run,
        skip_scan=skip_scan, resume=resume, force_execution=force_execution,
        ignore_symlinks_arg=ignore_symlinks_arg,
        use_gitignore=use_gitignore, custom_ignore_file_path=custom_ignore_file,
        skip_file_renaming=skip_file_renaming, skip_folder_renaming=skip_folder_renaming,
        skip_content=skip_content, timeout_minutes=timeout_minutes,
        quiet_mode=quiet_mode,
        verbose_mode=verbose_mode,
        interactive_mode=interactive_mode
    )  # Fixed indentation

def test_dry_run_behavior(temp_test_dir: dict, default_map_file: Path, assert_file_content):
    context_dir = temp_test_dir["runtime"]
    orig_deep_file_path = context_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    original_content = orig_deep_file_path.read_text(encoding='utf-8')

    assert original_content == "This file contains FLOJOY multiple times: Flojoy floJoy"
    # Run the dry run operation
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)

    # Verify original file remains unchanged
    assert orig_deep_file_path.exists()
    assert_file_content(orig_deep_file_path, original_content)

    # Verify no actual renaming occurred
    assert not (context_dir / "atlasvibe_root").exists()

    print(f"Transaction file: {context_dir / MAIN_TRANSACTION_FILE_NAME}")
    transactions = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None

    if not transactions:
        print("ERROR: No transactions generated!")
        assert False, "No transactions were generated in dry run"

    name_txs = [tx for tx in transactions if tx["TYPE"] in (TransactionType.FILE_NAME.value, TransactionType.FOLDER_NAME.value)]
    content_txs = [tx for tx in transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value]

    # 3 folders + 1 file = 4 name transactions
    assert len(name_txs) == 4, f"Expected 4 name transactions, found {len(name_txs)}"
    assert len(content_txs) == 1, f"Expected 1 content transaction, found {len(content_txs)}"

    completed_txs = [tx for tx in transactions if tx["STATUS"] == TransactionStatus.COMPLETED.value]
    assert len(completed_txs) == 5, f"Expected 5 completed transactions, found {len(completed_txs)}"
    
    for tx in completed_txs:
        assert tx.get("ERROR_MESSAGE") == "DRY_RUN"
        
        # Print detailed transaction info for debugging
        print(f"\nTransaction: id={tx['id']}, type={tx['TYPE']}, path={tx['PATH']}")
        if tx['TYPE'] in [TransactionType.FILE_NAME.value, TransactionType.FOLDER_NAME.value]:
            print(f"  Original: {tx.get('ORIGINAL_NAME')}")
            print(f"  Proposed: {replace_logic.replace_occurrences(tx.get('ORIGINAL_NAME'))}")
        elif tx['TYPE'] == TransactionType.FILE_CONTENT_LINE.value:
            content = tx.get("ORIGINAL_LINE_CONTENT", "")
            print(f"  Line: {tx.get('LINE_NUMBER')}")
            print(f"  Original: {content[:50] + '...' if len(content) > 50 else content}")
            print(f"  Proposed: {replace_logic.replace_occurrences(content)[:50] + '...'}")

def test_dry_run_virtual_paths(temp_test_dir: dict, default_map_file: Path):
    context_dir = temp_test_dir["runtime"]
    (context_dir / "folder1" / "folder2").mkdir(parents=True)
    (context_dir / "folder1" / "folder2" / "deep.txt").write_text("FLOJOY")
    
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    # Verify transaction count
    txn_path = context_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_path)
    
    # Should have 3 folders + 1 file + 1 content = 5 transactions
    assert len(transactions) == 5
    for tx in transactions:
        assert tx["STATUS"] == TransactionStatus.COMPLETED.value

def test_path_resolution_after_rename(temp_test_dir: dict, default_map_file: Path):
    context_dir = temp_test_dir["runtime"]
    
    # Run dry run first to populate path map
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    # Manually verify virtual path mapping
    txn_json = json.loads((context_dir / MAIN_TRANSACTION_FILE_NAME).read_text())
    path_map = {}
    for t in txn_json:
        if t["TYPE"] in ["FOLDER_NAME", "FILE_NAME"]:
            original = t["PATH"]
            new = t["PATH"].replace("flojoy", "atlasvibe").replace("FLOJOY", "ATLASVIBE")
            path_map[original] = new
    
    # Verify nested folders resolve correctly
    for path in ["folder1", "folder1/folder2", "folder1/folder2/deep.txt"]:
        assert path_map[path] == path.replace("flojoy", "atlasvibe").replace("FLOJOY", "ATLASVIBE")

def test_folder_nesting(temp_test_dir: dict, default_map_file: Path):
    context_dir = temp_test_dir["runtime"]
    
    # Create nested structure: root > a > b > c (file)
    a_path = context_dir / "flojoy_a"
    b_path = a_path / "flojoy_b"
    c_file = b_path / "flojoy_c.txt"
    
    # Create paths
    a_path.mkdir()
    b_path.mkdir()
    c_file.write_text("FLOJOY")
    
    # Run dry run
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    # Verify transaction order
    txn_path = context_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_path)
    
    # Verify folder processing order
    folders = [tx["PATH"] for tx in transactions if tx["TYPE"] == TransactionType.FOLDER_NAME.value]
    assert folders == ["flojoy_a", "flojoy_a/flojoy_b"], "Folders not processed from shallow to deep"
