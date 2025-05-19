# tests/test_mass_find_replace.py

import pytest
from pathlib import Path
import os
import shutil
import time
from typing import List, Dict, Any, Optional, Union
import logging 
from unittest.mock import patch, MagicMock 

from mass_find_replace import main_flow, MAIN_TRANSACTION_FILE_NAME, SCRIPT_NAME
from file_system_operations import (
    load_transactions, TransactionStatus, TransactionType, 
    BINARY_MATCHES_LOG_FILE, SELF_TEST_ERROR_FILE_BASENAME,
    save_transactions, _is_retryable_os_error 
)
import replace_logic 
import file_system_operations # For mocking its functions

from .conftest_mass_find_replace import (
    create_test_environment_content, assert_file_content, 
    VERY_LARGE_FILE_NAME_ORIG, VERY_LARGE_FILE_NAME_REPLACED, VERY_LARGE_FILE_LINES
)

DEFAULT_EXTENSIONS = [".txt", ".py", ".md", ".bin", ".log", ".data", ".rtf"] 
DEFAULT_EXCLUDE_DIRS_REL = ["excluded_flojoy_dir", "symlink_targets_outside"] 
DEFAULT_EXCLUDE_FILES_REL = ["exclude_this_flojoy_file.txt"] 

def run_main_flow_for_test(
    temp_test_dir: Path, map_file: Path, extensions: Optional[list[str]] = DEFAULT_EXTENSIONS,
    exclude_dirs: Optional[list[str]] = None, exclude_files: Optional[list[str]] = None,
    dry_run: bool = False, skip_scan: bool = False, resume: bool = False,
    force_execution: bool = True, ignore_symlinks_arg: bool = False,
    use_gitignore: bool = False, custom_ignore_file: Optional[str] = None,
    skip_file_renaming: bool = False, skip_folder_renaming: bool = False, skip_content: bool = False,
    timeout_minutes: int = 1, quiet_mode: bool = True # Default to quiet for tests
):
    load_map_success = replace_logic.load_replacement_map(map_file)
    if map_file.name != "empty_mapping.json": 
        assert load_map_success, f"Failed to load map {map_file} for test"
        assert replace_logic._RAW_REPLACEMENT_MAPPING, f"Map {map_file} loaded but no rules processed."
    elif not load_map_success and map_file.name == "empty_mapping.json" and replace_logic._RAW_REPLACEMENT_MAPPING :
         pytest.fail(f"Empty map file {map_file} failed to load but rules were processed.")
    
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
        quiet_mode=quiet_mode
    )

@pytest.mark.parametrize("ignore_symlinks", [False, True])
def test_standard_run(temp_test_dir: Path, default_map_file: Path, ignore_symlinks: bool):
    create_test_environment_content(temp_test_dir, include_very_large_file=True, include_symlink_tests=True)
    (temp_test_dir / "test_flojoy.rtf").write_text("{\\rtf1\\ansi an rtf with flojoy content here}", encoding='latin-1')

    run_main_flow_for_test(temp_test_dir, default_map_file, ignore_symlinks_arg=ignore_symlinks)

    root_renamed = temp_test_dir / "atlasvibe_root"
    assert root_renamed.is_dir()
    deep_folder = root_renamed / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir"
    assert deep_folder.is_dir()
    deep_file = deep_folder / "deep_atlasvibe_file.txt"
    assert deep_file.is_file()
    assert_file_content(deep_file, "Line 1: atlasvibe content.\nLine 2: More Atlasvibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project.")
    another_py = root_renamed / "another_atlasvibe_file.py"
    assert another_py.is_file()
    assert_file_content(another_py, "import atlasvibe_lib\n# class MyAtlasvibeClass: pass")
    only_name_md = temp_test_dir / "only_name_atlasvibe.md"
    assert only_name_md.is_file()
    assert_file_content(only_name_md, "Content without target string.")
    flojoy_lines_txt = temp_test_dir / "file_with_atlasVibe_lines.txt"
    assert flojoy_lines_txt.is_file()
    assert_file_content(flojoy_lines_txt, "First atlasVibe.\nSecond AtlasVibe.\natlasvibe and ATLASVIBE on same line.")
    unmapped_variant_txt = temp_test_dir / "unmapped_variant_atlasvibe_content.txt"
    assert unmapped_variant_txt.is_file()
    assert_file_content(unmapped_variant_txt, "This has fLoJoY content, and also atlasvibe.")
    
    gb18030_txt = temp_test_dir / "gb18030_atlasvibe_file.txt"
    assert gb18030_txt.is_file()
    actual_gb_bytes = gb18030_txt.read_bytes()
    expected_gb18030_bytes = "你好 atlasvibe 世界".encode('gb18030')
    expected_fallback_bytes = "fallback atlasvibe content".encode('utf-8')
    assert actual_gb_bytes == expected_gb18030_bytes or actual_gb_bytes == expected_fallback_bytes, "GB18030 content mismatch"

    bin_file1 = temp_test_dir / "binary_atlasvibe_file.bin"
    assert bin_file1.is_file()
    assert_file_content(bin_file1, b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04", is_binary=True)
    bin_file2_renamed = temp_test_dir / "binary_atlasvibe_name.bin"
    assert bin_file2_renamed.is_file(); assert not (temp_test_dir / "binary_fLoJoY_name.bin").exists()
    assert_file_content(bin_file2_renamed, b"unmapped_variant_binary_content" + b"\x00\xff", is_binary=True)
    
    large_file_renamed = temp_test_dir / "large_atlasvibe_file.txt"
    assert large_file_renamed.is_file()
    with open(large_file_renamed, 'r', encoding='utf-8') as f: first_line = f.readline().strip()
    assert first_line == "This atlasvibe line should be replaced 0"

    curr_deep_path = temp_test_dir
    deep_path_parts_after_rename = ["atlasvibe_root","depth1_atlasvibe","depth2","depth3_atlasvibe","depth4","depth5","depth6_atlasvibe","depth7","depth8","depth9_atlasvibe"]
    for part in deep_path_parts_after_rename:
        curr_deep_path /= part; assert curr_deep_path.is_dir(), f"Deep dir missing: {curr_deep_path}"
    curr_deep_path /= "depth10_file_atlasvibe.txt"; assert curr_deep_path.is_file()
    assert_file_content(curr_deep_path, "atlasvibe deep content")

    very_large_renamed = temp_test_dir / VERY_LARGE_FILE_NAME_REPLACED
    assert very_large_renamed.exists()
    with open(very_large_renamed, 'r', encoding='utf-8') as f: lines = f.readlines()
    assert lines[0].strip() == "Line 1: This is a atlasvibe line that should be replaced."
    assert lines[VERY_LARGE_FILE_LINES // 2].strip() == f"Line {VERY_LARGE_FILE_LINES // 2 + 1}: This is a atlasvibe line that should be replaced."
    assert lines[VERY_LARGE_FILE_LINES - 1].strip() == f"Line {VERY_LARGE_FILE_LINES}: This is a atlasvibe line that should be replaced."

    link_f_orig, link_d_orig = temp_test_dir/"link_to_file_flojoy.txt", temp_test_dir/"link_to_dir_flojoy"
    link_f_ren, link_d_ren = temp_test_dir/"link_to_file_atlasvibe.txt", temp_test_dir/"link_to_dir_atlasvibe"
    if ignore_symlinks:
        assert os.path.lexists(link_f_orig); assert not os.path.lexists(link_f_ren)
        assert os.path.lexists(link_d_orig); assert not os.path.lexists(link_d_ren)
    else:
        assert os.path.lexists(link_f_ren) and link_f_ren.is_symlink(); assert not os.path.lexists(link_f_orig)
        assert os.path.lexists(link_d_ren) and link_d_ren.is_symlink(); assert not os.path.lexists(link_d_orig)
    assert_file_content(temp_test_dir/"symlink_targets_outside"/"target_file_flojoy.txt", "flojoy in symlink target file")
    assert_file_content(temp_test_dir/"symlink_targets_outside"/"target_dir_flojoy"/"another_flojoy_file.txt", "flojoy content in symlinked dir target")

    binary_log = temp_test_dir / BINARY_MATCHES_LOG_FILE
    if binary_log.exists(): 
        log_content = binary_log.read_text()
        assert "File: binary_flojoy_file.bin, Key: 'flojoy', Offset: 7" in log_content
        assert "File: binary_flojoy_file.bin, Key: 'flojoy', Offset: 20" in log_content
    elif (temp_test_dir / "binary_atlasvibe_file.bin").exists(): 
         pytest.fail(f"{BINARY_MATCHES_LOG_FILE} should exist if binary_flojoy_file.bin was processed and had matches.")

    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_file); assert transactions is not None
    error_file_tx = next((tx for tx in transactions if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME), None)
    assert error_file_tx and error_file_tx["STATUS"] == TransactionStatus.FAILED.value
    assert (temp_test_dir / SELF_TEST_ERROR_FILE_BASENAME).exists()
    
    rtf_renamed_path = temp_test_dir / "test_atlasvibe.rtf"
    assert rtf_renamed_path.exists()
    rtf_content_tx = next((tx for tx in transactions if tx.get("PATH") == "test_flojoy.rtf" and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value), None)
    assert rtf_content_tx is not None, "RTF file content transaction should have been planned"
    assert rtf_content_tx["STATUS"] == TransactionStatus.SKIPPED.value, "RTF content transaction should be SKIPPED during execution"
    assert_file_content(rtf_renamed_path, "{\\rtf1\\ansi an rtf with flojoy content here}", encoding='latin-1')


def test_empty_map_run(temp_test_dir: Path, empty_map_file: Path):
    create_test_environment_content(temp_test_dir)
    run_main_flow_for_test(temp_test_dir, empty_map_file)
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None and len(transactions) == 0
    assert (temp_test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt").exists()

def test_complex_map_run(temp_test_dir: Path, complex_map_file: Path):
    create_test_environment_content(temp_test_dir, use_complex_map=True)
    run_main_flow_for_test(temp_test_dir, complex_map_file)
    assert (temp_test_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL").is_dir()
    file_in_diacritic = temp_test_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.txt"
    assert file_in_diacritic.is_file()
    assert_file_content(file_in_diacritic, "Content with dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL and also dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.\nAnd another Flojoy for good measure.")
    assert (temp_test_dir / "The control characters \n will be ignored_VAL.md").is_file()
    assert_file_content(temp_test_dir / "The control characters \n will be ignored_VAL.md", "This file has The control characters \n will be ignored_VAL in its name and content.")
    assert (temp_test_dir / "_My_Story&Love_VAL.log").is_file()
    assert_file_content(temp_test_dir / "_My_Story&Love_VAL.log", "Log for _My_Story&Love_VAL and _my_story&love_VAL. And My_Love&Story.")
    assert (temp_test_dir / "MOCO4_ip-N_VAL.data").is_file()
    assert_file_content(temp_test_dir / "MOCO4_ip-N_VAL.data", "Data for MOCO4_ip-N_VAL and Moco4_ip-N_VAL. Also coco4_ep-m.")
    special_chars_file = temp_test_dir / "special_chars_in_content_test.txt"
    assert special_chars_file.is_file()
    assert_file_content(special_chars_file, "This line contains SpecialCharsKeyMatched_VAL to be replaced.")
    control_chars_key_orig_filename = temp_test_dir / "complex_map_key_withcontrolchars_original_name.txt"
    assert control_chars_key_orig_filename.is_file()
    assert_file_content(control_chars_key_orig_filename, "Content for complex map control key filename test.")
    control_chars_key_content_file = temp_test_dir / "complex_map_content_with_key_with_controls.txt"
    assert control_chars_key_content_file.is_file()
    assert_file_content(control_chars_key_content_file, "Line with Value_for_key_with_controls_VAL to replace.")

def test_edge_case_run(temp_test_dir: Path, edge_case_map_file: Path):
    create_test_environment_content(temp_test_dir, use_edge_case_map=True)
    run_main_flow_for_test(temp_test_dir, edge_case_map_file)
    renamed_file = temp_test_dir / "edge_case_MyKeyValue_VAL_original_name.txt"
    assert renamed_file.is_file(); assert_file_content(renamed_file, "Initial content for control key name test (MyKey).")
    content_file = temp_test_dir / "edge_case_content_with_MyKey_controls.txt"
    assert content_file.is_file(); assert_file_content(content_file, "Line with MyKeyValue_VAL to replace.")
    priority_file = temp_test_dir / "edge_case_key_priority.txt"
    assert priority_file.is_file(); assert_file_content(priority_file, "test FooBar_VAL test and also Foo_VAL.")

def test_precision_run(temp_test_dir: Path, precision_map_file: Path):
    create_test_environment_content(temp_test_dir, include_precision_test_file=True)
    run_main_flow_for_test(temp_test_dir, precision_map_file)
    src_renamed = temp_test_dir / "precision_test_atlasvibe_plain_source.txt"
    name_renamed = temp_test_dir / "precision_name_atlasvibe_plain_test.md"
    assert src_renamed.is_file(); assert name_renamed.is_file()
    assert_file_content(name_renamed, "File for precision rename test.")
    exp_lines = ["Standard atlasvibe_plain here.\n","Another Atlasvibe_TitleCase for title case.\r\n",
                 "Test ATLASVIBE_DIACRITIC_VAL with mixed case.\n","  atlasvibe_spaced_val  with exact spaces.\n",
                 "  atlasvibe_plain   with extra spaces.\n", "value_for_control_key_val characters.\n",
                 "unrelated content\n","你好atlasvibe_plain世界 (Chinese chars).\n","emoji😊atlasvibe_plain test.\n"]
    exp_bytes_list = [l.encode('utf-8','surrogateescape') for l in exp_lines] + [b"malformed-\xff-atlasvibe_plain-bytes\n"]
    assert_file_content(src_renamed, b"".join(exp_bytes_list), is_binary=True)

def test_resume_functionality(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True) 
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    initial_txns = load_transactions(txn_file); assert initial_txns and len(initial_txns) > 0
    processed_time_sim = time.time() - 3600 
    name_tx_mod, content_tx_mod, error_tx_mod = False, False, False
    for tx in initial_txns:
        if tx["TYPE"] == TransactionType.FILE_NAME.value and not name_tx_mod: tx["STATUS"] = TransactionStatus.COMPLETED.value; tx["timestamp_processed"] = processed_time_sim; name_tx_mod = True
        if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and "large_flojoy_file.txt" in tx["PATH"] and not content_tx_mod : tx["STATUS"] = TransactionStatus.PENDING.value; content_tx_mod = True
        if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME and tx["TYPE"] == TransactionType.FILE_NAME.value: tx["STATUS"] = TransactionStatus.FAILED.value; tx["ERROR_MESSAGE"] = "Simulated initial fail"; tx["timestamp_processed"] = processed_time_sim; error_tx_mod = True
    assert name_tx_mod and error_tx_mod, "Resume setup failed"
    save_transactions(initial_txns, txn_file)
    create_test_environment_content(temp_test_dir, for_resume_test_phase_2=True, include_symlink_tests=True)
    deep_file_after_rename = temp_test_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file.txt"
    if deep_file_after_rename.exists():
        new_mtime = time.time() + 5 
        os.utime(deep_file_after_rename, (new_mtime, new_mtime))
        with open(deep_file_after_rename, "a", encoding="utf-8") as f_append: f_append.write("\n# Externally appended for resume.")
    run_main_flow_for_test(temp_test_dir, default_map_file, resume=True, dry_run=False)
    final_txns = load_transactions(txn_file); assert final_txns is not None
    new_file_renamed = temp_test_dir / "newly_added_atlasvibe_for_resume.txt"
    assert new_file_renamed.exists(); assert_file_content(new_file_renamed, "This atlasvibe content is new for resume.")
    assert any(tx["PATH"] == "newly_added_atlasvibe_for_resume.txt" and tx["STATUS"] == TransactionStatus.COMPLETED.value for tx in final_txns)
    only_name_mod = temp_test_dir / "only_name_atlasvibe.md"
    assert only_name_mod.exists(); assert_file_content(only_name_mod, "Content without target string, but now with atlasvibe.")
    assert any(tx["PATH"] == "only_name_atlasvibe.md" and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and tx["STATUS"] == TransactionStatus.COMPLETED.value for tx in final_txns)
    err_file_tx = next((tx for tx in final_txns if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME), None)
    assert err_file_tx and err_file_tx["STATUS"] == TransactionStatus.FAILED.value
    assert (temp_test_dir / SELF_TEST_ERROR_FILE_BASENAME).exists()
    if deep_file_after_rename.exists():
        assert "# Externally appended for resume." in deep_file_after_rename.read_text()
        assert any(tx["PATH"] == str(deep_file_after_rename.relative_to(temp_test_dir)).replace("\\","/") and \
                   tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and \
                   tx["STATUS"] == TransactionStatus.COMPLETED.value and \
                   "# Externally appended for resume." in tx.get("PROPOSED_LINE_CONTENT","")
                   for tx in final_txns), "Externally modified file content not re-processed correctly"

def test_dry_run_behavior(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    orig_deep_file_path = temp_test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    original_content = orig_deep_file_path.read_text()
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True)
    assert orig_deep_file_path.exists(); assert_file_content(orig_deep_file_path, original_content)
    assert not (temp_test_dir / "atlasvibe_root").exists()
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME); assert transactions is not None
    for tx in transactions:
        if tx["STATUS"] == TransactionStatus.COMPLETED.value: assert tx.get("ERROR_MESSAGE") == "DRY_RUN" or tx.get("PROPOSED_LINE_CONTENT") is not None
        elif tx["STATUS"] == TransactionStatus.PENDING.value: pytest.fail(f"Tx {tx['id']} PENDING after dry run")

def test_skip_scan_behavior(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True) 
    file_to_delete_orig_path = temp_test_dir / "flojoy_root" / "another_flojoy_file.py"
    assert file_to_delete_orig_path.exists(); file_to_delete_orig_path.unlink()
    run_main_flow_for_test(temp_test_dir, default_map_file, skip_scan=True, dry_run=False)
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME); assert transactions is not None
    deleted_file_txns_found = False
    for tx in transactions:
        if "another_flojoy_file.py" in tx["PATH"]: 
            deleted_file_txns_found = True
            assert tx["STATUS"] in [TransactionStatus.SKIPPED.value, TransactionStatus.FAILED.value]
    assert deleted_file_txns_found
    assert (temp_test_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file.txt").exists()

GITIGNORE_CONTENT = """
# This is a comment
*.log
build/
/docs/specific_file.txt
!important.log
"""
CUSTOM_IGNORE_CONTENT = """
*.tmp
temp_data/
"""
@pytest.mark.parametrize("use_gitignore_cli, custom_ignore_name, expected_ignored_files, expected_processed_files", [
    (True, None, ["no_target_here.log", "build/ignored_build_file.txt", "docs/specific_file.txt"], ["important.log", "src/main.py"]),
    (False, ".customignore", ["data.tmp", "temp_data/file.dat"], ["other_file.log", "src/main.py"]),
    (True, ".customignore", ["no_target_here.log", "build/ignored_build_file.txt", "docs/specific_file.txt", "data.tmp", "temp_data/file.dat"], ["important.log", "src/main.py"]),
])
def test_ignore_file_logic(temp_test_dir: Path, default_map_file: Path,
                           use_gitignore_cli, custom_ignore_name, expected_ignored_files, expected_processed_files):
    create_test_environment_content(temp_test_dir)
    (temp_test_dir / "build").mkdir(exist_ok=True); (temp_test_dir / "build" / "ignored_build_file.txt").write_text("flojoy in build")
    (temp_test_dir / "docs").mkdir(exist_ok=True); (temp_test_dir / "docs" / "specific_file.txt").write_text("flojoy in specific doc")
    (temp_test_dir / "important.log").write_text("flojoy important log")
    (temp_test_dir / "src").mkdir(exist_ok=True); (temp_test_dir / "src" / "main.py").write_text("flojoy in main.py")
    (temp_test_dir / "data.tmp").write_text("flojoy in data.tmp")
    (temp_test_dir / "temp_data").mkdir(exist_ok=True); (temp_test_dir / "temp_data" / "file.dat").write_text("flojoy in temp_data")
    (temp_test_dir / "other_file.log").write_text("flojoy in other_file.log")
    if use_gitignore_cli: (temp_test_dir / ".gitignore").write_text(GITIGNORE_CONTENT)
    custom_ignore_path_str: Optional[str] = None
    if custom_ignore_name:
        custom_ignore_path = temp_test_dir / custom_ignore_name
        custom_ignore_path.write_text(CUSTOM_IGNORE_CONTENT); custom_ignore_path_str = str(custom_ignore_path)
    run_main_flow_for_test(temp_test_dir, default_map_file, use_gitignore=use_gitignore_cli, custom_ignore_file=custom_ignore_path_str)
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME); assert transactions is not None
    processed_paths_in_tx = {tx["PATH"] for tx in transactions}
    for ignored_file_rel_path in expected_ignored_files:
        assert ignored_file_rel_path not in processed_paths_in_tx, f"File '{ignored_file_rel_path}' expected to be ignored."
        assert (temp_test_dir / ignored_file_rel_path).exists(), f"Ignored file '{ignored_file_rel_path}' should still exist."
    for processed_file_rel_path in expected_processed_files:
        original_path_abs = temp_test_dir / processed_file_rel_path
        related_tx_exists = any(tx["PATH"] == processed_file_rel_path or \
                               (tx.get("ORIGINAL_NAME") == Path(processed_file_rel_path).name and \
                                Path(tx["PATH"]).parent == Path(processed_file_rel_path).parent) \
                               for tx in transactions)
        assert related_tx_exists, f"File '{processed_file_rel_path}' expected to be processed."
        if "flojoy" in original_path_abs.name.lower(): 
            assert not original_path_abs.exists(), f"File '{original_path_abs}' should have been renamed."
        elif original_path_abs.exists() and "flojoy" in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower(): 
             assert "flojoy" not in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower(), f"File '{original_path_abs}' content should have changed."

@pytest.mark.parametrize("filename, content_bytes, is_binary_expected_by_lib, contains_flojoy_bytes", [
    ("text_file.txt", b"This is a plain text file with flojoy.", False, True),
    ("utf16_file.txt", "UTF-16 text with flojoy".encode('utf-16'), True, True),
    ("binary_file.bin", b"\x00\x01\x02flojoy_data\x03\x04\xDE\xAD\xBE\xEF", True, True),
    ("image.jpg", b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01flojoy_marker", True, True),
    ("control_char_heavy.txt", b"text" + b"\x01\x02\x03\x04\x05" * 200 + b"flojoy", True, True),
    ("mostly_nulls.dat", b"\x00" * 500 + b"flojoy" + b"\x00" * 500, True, True),
    ("valid_utf8.txt", "Valid UTF-8 string with flojoy and éàçüö.".encode('utf-8'), False, True),
    ("corrupt_utf8.txt", b"Corrupt UTF-8 with flojoy \xff\xfe some more.", True, True),
    ("empty_file.txt", b"", False, False), 
    ("rtf_file.rtf", b"{\\rtf1\\ansi This is flojoy rtf text.}", False, True), 
    ("svg_file.svg", b"<svg><text>flojoy</text></svg>", False, True),
    ("no_match_binary.dat", b"\xDE\xAD\xBE\xEF\xCA\xFE\xBA\xBE", True, False),
    ("no_match_text.txt", b"Simple text file.", False, False),
])
def test_binary_detection_and_processing_with_isbinary_lib(temp_test_dir: Path, default_map_file: Path, filename, content_bytes, is_binary_expected_by_lib, contains_flojoy_bytes):
    from isbinary import is_binary_file as lib_is_binary

    file_path = temp_test_dir / filename
    file_path.write_bytes(content_bytes)

    detected_as_binary_lib = False
    try:
        detected_as_binary_lib = lib_is_binary(str(file_path))
    except FileNotFoundError: 
        if len(content_bytes) == 0: detected_as_binary_lib = False 
        else: raise
    
    assert detected_as_binary_lib == is_binary_expected_by_lib, \
        f"File {filename} lib_is_binary detection mismatch. Expected binary: {is_binary_expected_by_lib}, Detected binary: {detected_as_binary_lib}"

    script_treats_as_binary_for_content_mod = detected_as_binary_lib and not filename.endswith(".rtf")

    run_main_flow_for_test(temp_test_dir, default_map_file, skip_file_renaming=True, skip_folder_renaming=True)

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME); assert transactions is not None
    content_tx_found = any(tx["PATH"] == filename and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value for tx in transactions)
    binary_log_path = temp_test_dir / BINARY_MATCHES_LOG_FILE
    binary_log_has_match = False
    if binary_log_path.exists(): binary_log_has_match = filename in binary_log_path.read_text()

    if not script_treats_as_binary_for_content_mod: 
        if contains_flojoy_bytes:
            assert content_tx_found, f"Expected content transaction for text-like file {filename}."
            if file_path.suffix.lower() != '.rtf': 
                changed_content_str = file_path.read_text(encoding='utf-8', errors='surrogateescape')
                assert "flojoy" not in changed_content_str.lower(), f"Text file {filename} content not replaced."
        assert not binary_log_has_match, f"Text-like file {filename} should not have matches in binary log."
    else: 
        assert not content_tx_found, f"Binary file {filename} should not have content transactions."
        if contains_flojoy_bytes:
             assert binary_log_has_match, f"Binary file {filename} expected in binary log."

@pytest.mark.slow 
def test_timeout_behavior_and_retries_mocked(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir)
    file_to_lock_rel = "file_with_floJoy_lines.txt" 
    
    original_execute_content = file_system_operations._execute_content_line_transaction
    mock_call_counts = { "count": 0 } 
    max_fails_for_mock = 2

    def mock_execute_content_with_retry(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        is_target_file = (tx_item["PATH"] == file_to_lock_rel or \
                          Path(tx_item["PATH"]).name == "file_with_atlasVibe_lines.txt") and \
                         tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value

        if is_target_file:
            mock_call_counts["count"] += 1
            if mock_call_counts["count"] <= max_fails_for_mock:
                print(f"DEBUG MOCK: Simulating retryable OSError for {tx_item['PATH']} (attempt {mock_call_counts['count']})")
                return TransactionStatus.RETRY_LATER, f"Mocked OS error (retryable), attempt {mock_call_counts['count']}", True
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run)

    with patch('file_system_operations._execute_content_line_transaction', mock_execute_content_with_retry):
        run_main_flow_for_test(temp_test_dir, default_map_file, timeout_minutes=1) 

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    
    target_tx_found_and_checked = False
    for tx in transactions:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == "file_with_atlasVibe_lines.txt") and \
           tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            target_tx_found_and_checked = True
            assert tx["STATUS"] == TransactionStatus.COMPLETED.value, f"Transaction for {tx['PATH']} should have eventually completed."
            assert tx.get("retry_count", 0) == max_fails_for_mock, f"Transaction for {tx['PATH']} should have {max_fails_for_mock} retries."
            break
    assert target_tx_found_and_checked, "Did not find the targeted content transaction for retry test."
    assert mock_call_counts["count"] == max_fails_for_mock + 1, "Mocked function not called expected number of times."

    mock_call_counts["count"] = 0 
    # Default max_overall_retry_attempts for timeout=0 is 500. We'll mock fewer to test the mock limit.
    indef_max_mock_calls = 7 
    
    def mock_always_retryable_error_indef(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        nonlocal mock_call_counts 
        is_target_file = (tx_item["PATH"] == file_to_lock_rel or \
                          Path(tx_item["PATH"]).name == "file_with_atlasVibe_lines.txt") and \
                         tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value
        if is_target_file:
            mock_call_counts["count"] += 1
            if mock_call_counts["count"] < indef_max_mock_calls : 
                return TransactionStatus.RETRY_LATER, f"Mocked persistent OS error (retryable), attempt {mock_call_counts['count']}", True
            else: 
                return TransactionStatus.FAILED, "Mocked persistent error, exceeded test call limit", False
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run)

    transactions_for_indef_retry = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    for tx in transactions_for_indef_retry:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == "file_with_atlasVibe_lines.txt") and \
           tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            tx["STATUS"] = TransactionStatus.PENDING.value 
            tx["retry_count"] = 0
            tx.pop("timestamp_next_retry", None)
            tx.pop("timestamp_processed", None)
            tx.pop("ERROR_MESSAGE", None)
    save_transactions(transactions_for_indef_retry, temp_test_dir / MAIN_TRANSACTION_FILE_NAME)

    with patch('file_system_operations._execute_content_line_transaction', mock_always_retryable_error_indef):
        run_main_flow_for_test(temp_test_dir, default_map_file, timeout_minutes=0, resume=True) 

    final_transactions_indef = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert final_transactions_indef is not None
    target_tx_indef = None
    for tx in final_transactions_indef:
         if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == "file_with_atlasVibe_lines.txt") and \
            tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            target_tx_indef = tx
            break
    assert target_tx_indef is not None
    assert target_tx_indef["STATUS"] == TransactionStatus.FAILED.value 
    # The number of retries will be indef_max_mock_calls - 1 because the last call results in FAILED, not RETRY_LATER
    assert target_tx_indef.get("retry_count", 0) == (indef_max_mock_calls -1) , \
        f"Should have retried {indef_max_mock_calls -1} times with indefinite timeout. Got {target_tx_indef.get('retry_count',0)}"


def test_empty_directory_handling(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)
    for item in temp_test_dir.iterdir(): 
        if item.is_dir(): shutil.rmtree(item)
        else: item.unlink()
    
    run_main_flow_for_test(temp_test_dir, default_map_file) 
    
    assert any("Target directory" in record.message and "is empty" in record.message for record in caplog.records), \
        "Expected 'directory is empty' log message."
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    assert not txn_file.exists() or txn_file.stat().st_size == 0 or (load_transactions(txn_file) == [])
    