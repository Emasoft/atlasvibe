# tests/test_mass_find_replace.py
# HERE IS THE FIXED TEST FILE WITH THE UNNECESSARY BACKTICK REMOVED
# (The lines with ``` are now removed to fix syntax errors)

import pytest
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
import chardet

from mass_find_replace import main_flow, main_cli, MAIN_TRANSACTION_FILE_NAME, YELLOW, RESET
from file_system_operations import (
    load_transactions, TransactionStatus, TransactionType,
    BINARY_MATCHES_LOG_FILE, save_transactions, get_file_encoding,
    update_transaction_status_in_list
)
import replace_logic
import conftest

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
    interactive_mode: bool = False
):
    # No environment setup here; rely on fixture
    final_exclude_dirs = exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS_REL
    base_exclude_files = exclude_files if exclude_files is not None else DEFAULT_EXCLUDE_FILES_REL
    additional_excludes = [map_file.name, BINARY_MATCHES_LOG_FILE]
    final_exclude_files = list(set(base_exclude_files + additional_excludes))
    main_flow(
        directory=str(context_dir),  # Use runtime directory for processing
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
    )

# Example test updated to remove environment setup
def test_dry_run_behavior(temp_test_dir: dict, default_map_file: Path, assert_file_content):
    context_dir = temp_test_dir["runtime"]
    # Get reference to test file before changes
    orig_deep_file_path = context_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    original_content = orig_deep_file_path.read_text(encoding='utf-8')
    
    # Run the dry run operation
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    # Verify original file remains unchanged
    assert orig_deep_file_path.exists()
    assert_file_content(orig_deep_file_path, original_content)
    
    # Verify no actual renaming occurred
    assert not (context_dir / "atlasvibe_root").exists()
    
    # Load and validate transactions
    transactions = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    
    # Count different transaction types
    name_txs = [tx for tx in transactions if tx["TYPE"] in (TransactionType.FILE_NAME.value, TransactionType.FOLDER_NAME.value)]
    content_txs = [tx for tx in transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value]
    
    # Should have 4 name transactions: 
    # - flojoy_root (folder)
    # - sub_flojoy_folder (folder)
    # - another_FLOJOY_dir (folder)
    # - deep_flojoy_file.txt (file)
    assert len(name_txs) == 4
    
    # Only file has 1 content transaction
    assert len(content_txs) == 1
    
    # Verify all five transactions are handled as dry_run
    completed_txs = [tx for tx in transactions if tx["STATUS"] == TransactionStatus.COMPLETED.value]
    assert len(completed_txs) == 5
    for tx in completed_txs:
        assert tx.get("ERROR_MESSAGE") == "DRY_RUN"

def test_multibyte_content_handling(temp_test_dir: dict, default_map_file: Path, assert_file_content):
    context_dir = temp_test_dir["runtime"]
    # Create GB2312 encoded file with matching content
    gb_content = "FLOJOY测试Flojoy" 
    gb_file = context_dir / "gb2312_flojoy.txt"
    gb_file.write_text(gb_content, encoding='gb2312')
    
    # Run actual execution (not dry run)
    run_main_flow_for_test(context_dir, default_map_file, dry_run=False, force_execution=True)
    
    # Verify file renamed and content changed
    new_path = context_dir / "gb2312_atlasvibe.txt"
    assert new_path.exists()
    
    # Check encoding preserved
    raw_bytes = new_path.read_bytes()
    detected = chardet.detect(raw_bytes)
    assert detected['encoding'] == 'GB2312'
    
    content = new_path.read_text(encoding='gb2312')
    assert "ATLASVIBE测试Atlasvibe" in content
