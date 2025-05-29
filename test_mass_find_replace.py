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
    temp_test_dir: Path, map_file: Path, extensions: list[str] | None = DEFAULT_EXTENSIONS,
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
        directory=str(temp_test_dir), mapping_file=str(map_file), extensions=extensions,
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
def test_dry_run_behavior(temp_test_dir: Path, default_map_file: Path, assert_file_content):
    # Get reference to test file before changes
    orig_deep_file_path = temp_test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    original_content = orig_deep_file_path.read_text(encoding='utf-8')
    
    # Run the dry run operation
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True)
    
    # Verify original file remains unchanged
    assert orig_deep_file_path.exists()
    assert_file_content(orig_deep_file_path, original_content)
    
    # Verify no actual renaming occurred
    assert not (temp_test_dir / "atlasvibe_root").exists()
    
    # Load and validate transactions
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    
    # Count different transaction types
    name_txs = [tx for tx in transactions if tx["TYPE"] in (TransactionType.FILE_NAME.value, TransactionType.FOLDER_NAME.value)]
    content_txs = [tx for tx in transactions if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value]
    
    # Should have 2 name transactions (folder and file)
    assert len(name_txs) == 2
    # Should have 3 content transactions (3 lines in file)
    assert len(content_txs) == 3
    
    # Verify all transactions are marked completed with dry run flag
    for tx in transactions:
        if tx["STATUS"] == TransactionStatus.COMPLETED.value:
            assert tx.get("ERROR_MESSAGE") == "DRY_RUN"
        else:
            pytest.fail(f"Transaction {tx['id']} in unexpected state {tx['STATUS']}")
def test_interactive_mode_approval(temp_test_dir: Path, default_map_file: Path, monkeypatch):
    # Mock user input to approve first transaction then quit
    monkeypatch.setattr(builtins, "input", lambda _: "a\nq\n")
    
    # Run in interactive mode
    run_main_flow_for_test(
        temp_test_dir, 
        default_map_file,
        interactive_mode=True,
        quiet_mode=False  # Need to see prompts
    )
    
    # Load transactions
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    
    # Verify first transaction was completed
    first_tx = transactions[0]
    assert first_tx["STATUS"] == TransactionStatus.COMPLETED.value
    
    # Verify at least one transaction was skipped due to quit
    skipped_txs = [tx for tx in transactions if tx["STATUS"] == TransactionStatus.SKIPPED.value]
    assert len(skipped_txs) > 0

def test_resume_behavior(temp_test_dir: Path, default_map_file: Path):
    # First run - do partial execution
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=False, force_execution=True)
    
    # Simulate interrupted state by modifying transactions file
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_file)
    assert transactions is not None
    
    # Mark first 2 transactions as completed and next 1 as failed
    for i in range(2):
        update_transaction_status_in_list(transactions, transactions[i]["id"], TransactionStatus.COMPLETED)
    update_transaction_status_in_list(transactions, transactions[2]["id"], TransactionStatus.FAILED, "Simulated failure")
    save_transactions(transactions, txn_file)
    
    # Resume operation
    run_main_flow_for_test(temp_test_dir, default_map_file, resume=True)
    
    # Verify final state
    final_transactions = load_transactions(txn_file)
    completed = [t for t in final_transactions if t["STATUS"] == TransactionStatus.COMPLETED.value]
    assert len(completed) > 2  # Should have completed more than initial 2

def test_skip_operations(temp_test_dir: Path, default_map_file: Path):
    # Test skipping file renaming
    run_main_flow_for_test(temp_test_dir, default_map_file, 
                         skip_file_renaming=True, dry_run=True)
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_file)
    file_renames = [t for t in transactions if t["TYPE"] == TransactionType.FILE_NAME.value]
    assert len(file_renames) == 0
    
    # Test skipping folder renaming
    run_main_flow_for_test(temp_test_dir, default_map_file,
                         skip_folder_renaming=True, dry_run=True)
    transactions = load_transactions(txn_file)
    folder_renames = [t for t in transactions if t["TYPE"] == TransactionType.FOLDER_NAME.value]
    assert len(folder_renames) == 0
    
    # Test skipping content
    run_main_flow_for_test(temp_test_dir, default_map_file,
                         skip_content=True, dry_run=True)
    transactions = load_transactions(txn_file)
    content_changes = [t for t in transactions if t["TYPE"] == TransactionType.FILE_CONTENT_LINE.value]
    assert len(content_changes) == 0

def test_binary_file_handling(temp_test_dir: Path, default_map_file: Path):
    # Create test binary file
    bin_file = temp_test_dir / "flojoy_root" / "test.bin"
    bin_content = b"FLOJOY\x00\xff" + b"\x00" * 1000  # Valid UTF-8 match followed by invalid bytes
    bin_file.write_bytes(bin_content)
    
    run_main_flow_for_test(temp_test_dir, default_map_file)
    
    # Verify binary file wasn't modified
    assert bin_file.read_bytes() == bin_content
    
    # Verify match was logged
    log_file = temp_test_dir / BINARY_MATCHES_LOG_FILE
    assert log_file.exists()
    assert "test.bin" in log_file.read_text()

def test_symlink_handling(temp_test_dir: Path, default_map_file: Path):
    # Create symlink
    target_dir = temp_test_dir / "symlink_targets_outside"
    target_dir.mkdir()
    symlink = temp_test_dir / "flojoy_root" / "symlink_to_external"
    symlink.symlink_to(target_dir)
    
    # Run with default symlink handling (ignore)
    run_main_flow_for_test(temp_test_dir, default_map_file)
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    symlink_txs = [t for t in transactions if "symlink_to_external" in t["PATH"]]
    assert len(symlink_txs) == 0
    
    # Run with symlink processing enabled
    run_main_flow_for_test(temp_test_dir, default_map_file, ignore_symlinks_arg=False)
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    symlink_txs = [t for t in transactions if "symlink_to_external" in t["PATH"]]
    assert len(symlink_txs) > 0

def test_mixed_encoding_preservation(temp_test_dir: Path, default_map_file: Path, assert_file_content):
    # Create test file with mixed encodings
    test_file = temp_test_dir / "encoding_test.txt"
    content = (
        b"Flojoy in UTF-8\n"
        b"Flojoy in latin-1: \xae\n"  # ® symbol
        b"Flojoy in cp1252: \x99\n"   # ™ symbol
    )
    test_file.write_bytes(content)
    
    run_main_flow_for_test(temp_test_dir, default_map_file)
    
    # Verify replacements while preserving encoding
    expected_content = (
        "Atlasvibe in UTF-8\n"
        "Atlasvibe in latin-1: ®\n"
        "Atlasvibe in cp1252: ™\n"
    )
    assert_file_content(test_file, expected_content)

# Additional tests for deeper validation

def test_complex_surgical_replacement(temp_test_dir, default_map_file, assert_file_content):
    # File with mixed encodings, formatting and special cases
    content = (
        "Line1: FLOJOY normal\n"
        "Line2: •FloJoy• bullet point\n"
        "Line3: Fl\u00f6joy unicode char\n"  # "ö" is normalized to "o"
        "Line4: <<CONTROL>>Flojoy\x08<<CONTROL>>\n"
    )
    test_file = temp_test_dir / "complex.txt"
    test_file.write_text(content, encoding='utf-8')
    
    run_main_flow_for_test(temp_test_dir, default_map_file)
    
    # Verify changes preserved structure exactly
    expected = (
        "Line1: ATLASVIBE normal\n"
        "Line2: •atlasVibe• bullet point\n"
        "Line3: Flojoy unicode char\n"  # Not replaced due to ö->o normalization
        "Line4: <<CONTROL>>Atlasvibe<<CONTROL>>\n"
    )
    assert_file_content(test_file, expected)

def test_encoding_layer_preservation(temp_test_dir, default_map_file):
    # Test all supported encodings
    for enc in ['utf-8', 'latin1', 'cp1252']:
        content = f"Flojoy content in {enc} encoding"
        test_file = temp_test_dir / f"test_{enc}.txt"
        # Write with encoding including special chars
        special_char = "é" if enc != 'cp1252' else "™"
        content += f"\nSpecial: {special_char}"
        test_file.write_bytes(content.encode(enc))
        
        run_main_flow_for_test(temp_test_dir, default_map_file)
        
        # Verify byte preservation except replacements
        new_content = test_file.read_bytes()
        decoded_orig = content.replace("Flojoy", "Atlasvibe").encode(enc)
        assert new_content == decoded_orig

def test_transaction_validation_system(temp_test_dir, default_map_file):
    # Create file that changes between scan and execution
    test_file = temp_test_dir / "volatile.txt"
    test_file.write_text("Original Flojoy line\n")
    
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True)
    
    # Alter file before execution
    test_file.write_text("Modified unrelated line\n", encoding='utf-8')
    
    # Execute with resume
    run_main_flow_for_test(temp_test_dir, default_map_file, resume=True)
    
    # Verify transaction failed validation
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_file)
    content_tx = [t for t in transactions if t["TYPE"] == "FILE_CONTENT_LINE"]
    assert len(content_tx) == 1
    assert content_tx[0]["STATUS"] == "FAILED"
    assert "content changed" in content_tx[0]["ERROR_MESSAGE"]

def test_rename_verification(temp_test_dir, default_map_file, mocker):
    # Simulate filesystem inconsistency
    mocker.patch('os.path.exists', side_effect=lambda x: "error_file" not in x)
    error_file = temp_test_dir / "error_file_flojoy.txt"
    error_file.write_text("Test")
    
    run_main_flow_for_test(temp_test_dir, default_map_file)
    
    txns = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    error_tx = next(t for t in txns if "error_file" in t["PATH"])
    assert error_tx["STATUS"] == "FAILED"
    assert "on-disk state invalid" in error_tx["ERROR_MESSAGE"]

def test_symlink_target_integrity(temp_test_dir, default_map_file):
    # Setup external symlink target
    external_dir = temp_test_dir.parent / "external_target"
    external_dir.mkdir(exist_ok=True)
    target_file = external_dir / "Flojoy_file.txt"
    target_file.write_text("Should not change")
    
    # Create symlink pointing outside repo
    symlink = temp_test_dir / "ext_link"
    symlink.symlink_to(external_dir)
    
    run_main_flow_for_test(temp_test_dir, default_map_file)
    
    # Verify external file untouched
    assert "Flojoy" in target_file.read_text()

def test_binary_protection(temp_test_dir, default_map_file):
    # PNG file with "FLOJOY" in header
    png_header = b'\x89PNG\r\n\x1a\nFLOJOY chunk'
    bin_file = temp_test_dir / "logo_flojoy.png"
    bin_file.write_bytes(png_header + b'\x00'*100)
    
    run_main_flow_for_test(temp_test_dir, default_map_file)
    
    # Verify no changes and logged
    assert bin_file.read_bytes() == png_header + b'\x00'*100
    log_content = (temp_test_dir / BINARY_MATCHES_LOG_FILE).read_text()
    assert "logo_flojoy.png" in log_content
    assert "FLOJOY" in log_content

def test_edge_case_handling(temp_test_dir, default_map_file):
    # Cases that previously caused issues
    cases = [
        ("empty_file", "", None, None),
        ("rtf_file", r"{\rtf1\ansi FLOJOY}", "rtf", "RTF skipped"),
        ("case_sensitive", "FLOJOY Flojoy flojoy", None, "ATLASVIBE Atlasvibe flojoy"),
    ]
    
    for name, content, ext, expected in cases:
        path = temp_test_dir / f"{name}.{ext if ext else 'txt'}"
        path.write_text(content)
        
        run_main_flow_for_test(temp_test_dir, default_map_file)
        
        if expected is not None:
            file_content = path.read_text()
            if expected == "RTF skipped":
                # RTF content modification is skipped, so original content remains
                assert content in file_content
            else:
                assert expected in file_content

def test_interactive_debugging(temp_test_dir, default_map_file, monkeypatch):
    # Mock user input for complex debugging
    inputs = iter([
        "a",  # Approve first change
        "n",  # Show context (invalid input, will reprompt)
        "s",  # Skip second
        "q"   # Quit
    ])
    def mock_input(prompt):
        val = next(inputs)
        # Accept 'n' as invalid, so it will reprompt until valid input
        if val == "n":
            return "invalid"
        return val
    monkeypatch.setattr('builtins.input', mock_input)
    
    # Create multi-change file
    content = "FLOJOY\nFlojoy\nflojoy"
    test_file = temp_test_dir / "variations.txt"
    test_file.write_text(content)
    
    run_main_flow_for_test(temp_test_dir, default_map_file, interactive_mode=True)
    
    # Verify partial processing
    txns = load_transactions(test_file.parent / MAIN_TRANSACTION_FILE_NAME)
    statuses = [t['STATUS'] for t in txns if t["PATH"] == "variations.txt" and t["TYPE"] == "FILE_CONTENT_LINE"]
    # The last line "flojoy" is not replaced (no mapping), so no transaction for it
    # So expect 2 transactions: first approved, second skipped, then quit
    assert "COMPLETED" in statuses
    assert "SKIPPED" in statuses
    assert "SKIPPED" in statuses or len(statuses) == 2  # The quit causes remaining to skip
    file_content = test_file.read_text()
    assert "ATLASVIBE" in file_content or "Atlasvibe" in file_content
