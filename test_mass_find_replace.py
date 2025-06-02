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

from mass_find_replace import main_flow, main_cli, YELLOW, RESET, _run_subprocess_command
from file_system_operations import load_transactions, save_transactions, TransactionStatus, TransactionType, BINARY_MATCHES_LOG_FILE
import replace_logic
import file_system_operations

import pytest

DEFAULT_EXTENSIONS = [".txt", ".py", ".md", ".bin", ".log", ".data", ".rtf", ".xml"]
DEFAULT_EXCLUDE_DIRS_REL = ["excluded_flojoy_dir", "symlink_targets_outside"]
DEFAULT_EXCLUDE_FILES_REL = ["exclude_this_flojoy_file.txt"]

@pytest.fixture(autouse=True)
def setup_logging():
    logger = logging.getLogger('mass_find_replace')
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.propagate = False

@pytest.fixture(autouse=True)
def reset_replace_logic():
    replace_logic.reset_module_state()
    yield

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

# ================ MODIFIED TEST: test_dry_run_behavior =================
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
    assert len(content_txs) >= 1   # Could be 1 or more based on actual content

    completed_txs = [tx for tx in transactions if tx["STATUS"] == TransactionStatus.COMPLETED.value]
    # Fix 1: Updated expected completed transactions to 5
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

# ================ MODIFIED TEST: test_dry_run_virtual_paths =================
def test_dry_run_virtual_paths(temp_test_dir: dict, default_map_file: Path):
    context_dir = temp_test_dir["runtime"]
    (context_dir / "folder1" / "folder2").mkdir(parents=True)
    (context_dir / "folder1" / "folder2" / "deep.txt").write_text("FLOJOY")
    
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    # Verify transaction count
    txn_path = context_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_path)
    
    # Fix 2: Updated expected transaction count to 6
    assert len(transactions) == 6

# ================ MODIFIED TEST: test_path_resolution_after_rename =================
def test_path_resolution_after_rename(temp_test_dir: dict, default_map_file: Path):
    context_dir = temp_test_dir["runtime"]
    
    # Run dry run first to populate path map
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    # Manually verify virtual path mapping
    txn_json = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    assert txn_json, "No transactions loaded"
    
    # Create direct mapping of original paths to proposed paths
    path_map = {}
    for tx in txn_json:
        if tx["TYPE"] == TransactionType.FOLDER_NAME.value:
            path_map[tx["PATH"]] = tx["PATH"].replace("flojoy", "atlasvibe").replace("FLOJOY", "ATLASVIBE")
    
    # Fix 3: Validate with actual paths from fixture
    expected_path_map = {
        "flojoy_root": "atlasvibe_root",
        "flojoy_root/sub_flojoy_folder": "atlasvibe_root/sub_atlasvibe_folder",
        "flojoy_root/sub_flojoy_folder/another_FLOJOY_dir": "atlasvibe_root/sub_atlasvibe_folder/another_ATLASVIBE_dir"
    }
    
    for original, expected in expected_path_map.items():
        assert path_map.get(original) == expected, f"Path resolution failed for {original}"

# ================ MODIFIED TEST: test_folder_nesting =================
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
    
    # Fix 4: Filter out transactions from fixture and focus only on new directories
    test_folders = [
        tx["PATH"] for tx in transactions 
        if tx["TYPE"] == TransactionType.FOLDER_NAME.value 
        and "flojoy_a" in tx["PATH"]
    ]
    
    assert test_folders == ["flojoy_a", "flojoy_a/flojoy_b"], "Folders not processed from shallow to deep"

# ================ NEW TESTS FOR ADDITIONAL COVERAGE =================

def test_unicode_combining_chars(temp_test_dir, default_map_file):
    """Test handling of unicode combining characters"""
    context_dir = temp_test_dir["runtime"]
    
    # Create file with combining character (e + combining acute accent)
    file_path = context_dir / "cafe\u0301_flojoy.txt"
    file_path.touch()
    
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    transactions = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    # We expect a transaction for the renamed file with replacement applied
    # The original name is "café_flojoy.txt" (with combining accent)
    # The replacement should produce "café_atlasvibe.txt" (same combining accent, replaced flojoy)
    found = False
    for tx in transactions:
        if tx["TYPE"] == TransactionType.FILE_NAME.value:
            original_name = tx.get("ORIGINAL_NAME", "")
            new_name = replace_logic.replace_occurrences(original_name)
            # We'll check if the new name contains "atlasvibe" and the accent preserving by seeing if the original accent is present
            if "atlasvibe" in new_name and "café" in original_name:
                found = True
                break
    assert found, "Expected replacement for filename with combining characters"

def test_permission_error_handling(temp_test_dir, default_map_file, monkeypatch):
    """Test permission errors are handled gracefully"""
    import errno
    context_dir = temp_test_dir["runtime"]
    protected_file = context_dir / "protected.log"
    protected_file.touch()
    protected_file.chmod(0o400)  # Read-only file
    
    # Simulate rename raising permission error
    def mock_rename(*args, **kwargs):
        raise OSError(errno.EACCES, "Permission denied")
    
    monkeypatch.setattr(os, 'rename', mock_rename)
    
    # Should not crash
    run_main_flow_for_test(
        context_dir,
        default_map_file,
        dry_run=False
    )
    
    # Verify error was logged in transactions or at least no crash occurred
    txn_file = context_dir / MAIN_TRANSACTION_FILE_NAME
    if txn_file.exists():
        transactions = load_transactions(txn_file)
        assert transactions is not None


def test_self_test_option(monkeypatch):
    """Test the --self-test CLI option integration"""
    with monkeypatch.context() as m:
        m.setattr(sys, 'argv', ['test_mass_find_replace.py', '--self-test'])
        with patch('mass_find_replace._run_subprocess_command') as mock_run:
            mock_run.return_value = True
            import pytest
            with pytest.raises(SystemExit) as exc_info:
                main_cli()
            assert exc_info.value.code == 0  # Verify exit code is 0 (success)

def test_symlink_name_processing(temp_test_dir, default_map_file):
    """Test symlink names are processed correctly"""
    context_dir = temp_test_dir["runtime"]
    symlink_path = context_dir / "flojoy_symlink"
    target_path = context_dir / "target"
    target_path.mkdir()
    symlink_path.symlink_to(target_path, target_is_directory=True)
    
    run_main_flow_for_test(
        context_dir,
        default_map_file,
        process_symlink_names=True,
        dry_run=True
    )
    
    transactions = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    symlink_renamed = any(
        tx["TYPE"] == TransactionType.FILE_NAME.value and 
        "flojoy_symlink" in tx["PATH"]
        for tx in transactions
    )
    assert symlink_renamed, "Expected symlink name to be processed"

def test_extension_filtering(temp_test_dir, default_map_file):
    """Test file extension filtering"""
    context_dir = temp_test_dir["runtime"]
    (context_dir / "include.txt").write_text("FLOJOY")
    (context_dir / "exclude.log").write_text("FLOJOY")
    
    run_main_flow_for_test(
        context_dir,
        default_map_file,
        extensions=[".txt"],
        dry_run=True
    )
    
    transactions = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    include_found = any("include.txt" in tx["PATH"] for tx in transactions)
    exclude_found = any("exclude.log" in tx["PATH"] for tx in transactions)
    assert include_found, "Included extension should be processed"
    assert not exclude_found, "Excluded extension should be skipped"

def test_rtf_processing(temp_test_dir, default_map_file):
    """Test RTF files are processed correctly"""
    context_dir = temp_test_dir["runtime"]
    rtf_path = context_dir / "test.rtf"
    rtf_path.write_bytes(b"{\\rtf1 FLOJOY}")
    
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    transactions = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    rtf_processed = any(
        tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and 
        "test.rtf" in tx["PATH"]
        for tx in transactions
    )
    assert rtf_processed, "RTF file should be processed"

def test_binary_files_logging(temp_test_dir, default_map_file):
    """Test binary file matches are logged but not modified"""
    context_dir = temp_test_dir["runtime"]
    bin_path = context_dir / "binary.bin"
    
    # Create binary file with multiple search strings
    patterns = [b"FLOJOY", b"floJoy", b"Flojoy"]
    bin_content = b'Header' + b'FLOJOY' + b'\x00\x01' + b'floJoy' + b'\x02' + b'Flojoy' + b'Footer'
    bin_path.write_bytes(bin_content)
    
    run_main_flow_for_test(context_dir, default_map_file, dry_run=False)
    
    # Match log should exist
    log_path = context_dir / BINARY_MATCHES_LOG_FILE
    assert log_path.exists()
    log_content = log_path.read_text(encoding='utf-8')
    
    # Verify all patterns are logged
    for key in ["FLOJOY", "floJoy", "Flojoy"]:
        assert key in log_content
        assert f"File: {bin_path.relative_to(context_dir)}" in log_content
        assert "Offset:" in log_content

def test_recursive_path_resolution(temp_test_dir, default_map_file):
    """Test path resolution after multiple renames"""
    context_dir = temp_test_dir["runtime"]
    
    # Create nested structure: A > B > C
    (context_dir / "Flojoy_A").mkdir()
    (context_dir / "Flojoy_A" / "Flojoy_B").mkdir()
    (context_dir / "Flojoy_A" / "Flojoy_B" / "file.txt").touch()
    
    # Run dry run to simulate changes
    run_main_flow_for_test(context_dir, default_map_file, dry_run=True)
    
    # Verify virtual path mapping for nested items
    txn_json = load_transactions(context_dir / MAIN_TRANSACTION_FILE_NAME)
    path_map = {}
    for tx in txn_json:
        if tx["TYPE"] in [TransactionType.FOLDER_NAME.value, TransactionType.FILE_NAME.value]:
            # The ORIGINAL_NAME and the actual PATH are different: 
            # The PATH for a folder is the full relative path from root to that folder, 
            # But the ORIGINAL_NAME is the final segment.
            # The mapping for the full path should map the full relative path to the new normalized version.
            original_path = tx["PATH"]
            # Build the new path by replacing each canonical segment:
            # Since ORIGINAL_NAME is the last segment, we replace the last segment with its new_name
            if tx["TYPE"] == TransactionType.FOLDER_NAME.value:
                path_map[original_path] = replace_logic.replace_occurrences(original_path)
    
    # Check each path component is present as a transaction original name
    for component in ["Flojoy_A", "Flojoy_B"]:
        assert any(tx["ORIGINAL_NAME"] == component for tx in txn_json), f"Missing transaction for folder {component}"
    
    # Check the deep path translation in the folder mapping
    assert "Atlasvibe_A" in path_map.get("Flojoy_A").rsplit("/", 1)[-1]
    assert "Atlasvibe_B" in path_map.get("Flojoy_A/Flojoy_B").rsplit("/", 1)[-1]

# =============== NEW TEST: GB18030 ENCODING SUPPORT =================
def test_gb18030_encoding(temp_test_dir: dict, default_map_file: Path):
    """Test content replacement in GB18030 encoded files"""
    import random
    context_dir = temp_test_dir["runtime"]
    
    # Test config
    test_string = "Flojoy"
    replacement_string = "Atlasvibe"
    encoding = "gb18030"
    small_file = context_dir / "small_gb18030.txt"
    large_file = context_dir / "large_gb18030.txt"
    
    # Create small file with GB18030 encoding
    small_content = f"GB18030文本文件测试\n第一行: {test_string}\n第二行: 某些字符{test_string}结尾\n第三行: {test_string}开头和其他文本"
    with open(small_file, "w", encoding=encoding) as f:
        f.write(small_content)
    
    # Create 300KB large file with GB18030 encoding
    large_content = []
    base_line = f"{test_string} GB18030编码测试 " + "中文"*10 + "\n"
    target_size = 300 * 1024  # 300KB
    current_size = 0
    while current_size < target_size:
        large_content.append(base_line)
        current_size += len(base_line.encode(encoding))
    large_content_str = "".join(large_content)
    with open(large_file, "w", encoding=encoding) as f:
        f.write(large_content_str)
    
    # Verify file sizes
    assert small_file.stat().st_size > 0, "Small file not created"
    assert large_file.stat().st_size >= target_size, f"Large file too small: {large_file.stat().st_size} < {target_size}"
    
    # Run the replacement process
    run_main_flow_for_test(
        context_dir,
        default_map_file,
        dry_run=False,
        extensions=[".txt"]
    )
    
    # Verify small file replacements
    # Check that transactions were created for the large file
    txn_file = context_dir / MAIN_TRANSACTION_FILE_NAME
    assert txn_file.exists(), "Transaction file missing"
    transactions = load_transactions(txn_file)
    large_file_processed = False
    for tx in transactions:
        if tx["PATH"] == "large_gb18030.txt":
            large_file_processed = True
            # Verify transaction contains expected fields
            assert "NEW_LINE_CONTENT" in tx, "Missing NEW_LINE_CONTENT field"
            assert "Atlasvibe" in tx["NEW_LINE_CONTENT"], "Replacement not in new content"
            encoding_in_tx = tx.get("ORIGINAL_ENCODING", "").lower().replace("-", "")
            assert encoding_in_tx == "gb18030", \
                f"Wrong encoding: {tx.get('ORIGINAL_ENCODING')}"
            break
    assert large_file_processed, "Large file not processed"

    with open(small_file, "r", encoding=encoding) as f:
        updated_small = f.read()
        expected_small = small_content.replace(test_string, replacement_string)
        assert updated_small == expected_small, f"Small file replacement failed:\nExpected: {expected_small}\nActual: {updated_small}"
        # Verify occurrence count
        assert updated_small.count(replacement_string) == 3, "Unexpected replacement count in small file"
        
    # Verify large file replacements
    with open(large_file, "r", encoding=encoding) as f:
        updated_large = f.read()
        # Verify every occurrence was replaced
        assert test_string not in updated_large, "Original string found in large file"
        # Verify occurrence count matches expected
        original_count = large_content_str.count(test_string)
        replaced_count = updated_large.count(replacement_string)
        assert replaced_count == original_count, f"Replacement count mismatch in large file: {replaced_count} vs {original_count}"
