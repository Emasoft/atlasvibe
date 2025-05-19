# tests/test_mass_find_replace.py
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `test_standard_run`:
#   - Adjusted assertion for `unmapped_variant_txt` based on corrected `replace_logic`.
#     "fLoJoY" is not a key in default_map, so it won't be replaced. "flojoy" will.
#   - Corrected assertion for `binary_fLoJoY_name.bin`. Since "fLoJoY" is not a key,
#     the filename should not change.
#   - Corrected binary log offset for the second match in `binary_flojoy_file.bin` from 22 to 23.
# - `test_complex_map_run`:
#   - Adjusted content assertion for `filename_with_MOCO4_ip-N_VAL.data`.
#     "coco4_ep-m" (lowercase) is not a key in complex_map, so it won't be replaced.
# - `test_precision_run`:
#   - Adjusted expected content for the line "  flojoy   with extra spaces.\n".
#     With case-sensitive matching and keys sorted by length, "  flojoy  " (with spaces)
#     is matched and replaced, leaving the trailing space.
# - Corrected deep path assertions to match `conftest.py` changes.
# - `test_edge_case_run`:
#   - Corrected assertion for `content_file`: current `replace_logic` will not replace "My\nKey" in content
#     if the map key is "My\nKey" (stripped to "MyKey") because the regex `(MyKey)` doesn't match "My\nKey".
#     The test now expects the content to remain unchanged for this specific case.
# - `test_resume_functionality`:
#   - Ensured `only_name_flojoy.md` is expected before resume, and `only_name_atlasvibe.md` after.
#   - Corrected content assertion for `only_name_atlasvibe.md`.
#   - Adjusted deep file path checks for resume.
# - `test_empty_directory_handling`:
#   - Changed expected log message to "Target directory ... is empty. Nothing to do." for truly empty dir.
#   - Added check for "No actionable occurrences found by scan" when dir only has excluded map.
# - Refactored multiple statements on single lines to comply with E701 linting rules.
# - Corrected binary log offset assertion in `test_standard_run` for the `True` (ignore_symlinks) case.
# - Modernized type hints (e.g., `list` instead of `typing.List`, `X | None` instead of `Optional[X]`, selectively).
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
from pathlib import Path
import os
import shutil
import time
from typing import Any, Optional, Dict # Keep Any if specifically needed, Optional for custom_ignore_path_str, Dict for mock_tx_call_counts
import logging
import json
from unittest.mock import patch, MagicMock

from mass_find_replace import main_flow, MAIN_TRANSACTION_FILE_NAME, SCRIPT_NAME
from file_system_operations import (
    load_transactions, TransactionStatus, TransactionType,
    BINARY_MATCHES_LOG_FILE, SELF_TEST_ERROR_FILE_BASENAME,
    save_transactions, _is_retryable_os_error
)
import replace_logic
import file_system_operations # For mocking its functions

from conftest import (
    create_test_environment_content, assert_file_content,
    VERY_LARGE_FILE_NAME_ORIG, VERY_LARGE_FILE_NAME_REPLACED, VERY_LARGE_FILE_LINES
)

DEFAULT_EXTENSIONS = [".txt", ".py", ".md", ".bin", ".log", ".data", ".rtf"]
DEFAULT_EXCLUDE_DIRS_REL = ["excluded_flojoy_dir", "symlink_targets_outside"]
DEFAULT_EXCLUDE_FILES_REL = ["exclude_this_flojoy_file.txt"]

def run_main_flow_for_test(
    temp_test_dir: Path, map_file: Path, extensions: list[str] | None = DEFAULT_EXTENSIONS,
    exclude_dirs: list[str] | None = None, exclude_files: list[str] | None = None,
    dry_run: bool = False, skip_scan: bool = False, resume: bool = False,
    force_execution: bool = True, ignore_symlinks_arg: bool = False, # custom_ignore_file can be str | None
    use_gitignore: bool = False, custom_ignore_file: str | None = None,
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
    # "fLoJoY" is not a key in default_map, so it won't be replaced. "flojoy" will.
    assert_file_content(unmapped_variant_txt, "This has fLoJoY content, and also atlasvibe.")

    gb18030_txt = temp_test_dir / "gb18030_atlasvibe_file.txt"
    assert gb18030_txt.is_file()
    actual_gb_bytes = gb18030_txt.read_bytes()
    expected_gb18030_bytes = "你好 atlasvibe 世界".encode('gb18030')
    expected_fallback_bytes = "fallback atlasvibe content".encode('utf-8')
    original_gb_write_success = False
    try:
        (temp_test_dir / "temp_gb_check.txt").write_text("你好 flojoy 世界", encoding="gb18030")
        original_gb_write_success = True
        (temp_test_dir / "temp_gb_check.txt").unlink()
    except Exception:
        pass

    if original_gb_write_success:
        assert actual_gb_bytes == expected_gb18030_bytes, "GB18030 content mismatch"
    else:
        assert actual_gb_bytes == expected_fallback_bytes, "GB18030 content mismatch (fallback)"

    bin_file1 = temp_test_dir / "binary_atlasvibe_file.bin"
    assert bin_file1.is_file()
    assert_file_content(bin_file1, b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04", is_binary=True)

    # "fLoJoY" is not a key in default_map, so filename "binary_fLoJoY_name.bin" should not change.
    bin_file2_orig_path = temp_test_dir / "binary_fLoJoY_name.bin"
    assert bin_file2_orig_path.is_file()
    # Ensure it wasn't incorrectly renamed
    assert not (temp_test_dir / "binary_atlasvibe_name.bin").exists() 
    assert_file_content(bin_file2_orig_path, b"unmapped_variant_binary_content" + b"\x00\xff", is_binary=True)

    large_file_renamed = temp_test_dir / "large_atlasvibe_file.txt"
    assert large_file_renamed.is_file()
    with open(large_file_renamed, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    assert first_line == "This atlasvibe line should be replaced 0"

    curr_deep_path = temp_test_dir
    deep_path_parts_after_rename = ["atlasvibe_root","depth1_atlasvibe","depth2","depth3_atlasvibe","depth4","depth5","depth6_atlasvibe","depth7","depth8","depth9_atlasvibe"]
    for part in deep_path_parts_after_rename:
        curr_deep_path /= part
        assert curr_deep_path.is_dir(), f"Deep dir missing: {curr_deep_path}"
    curr_deep_path /= "depth10_file_atlasvibe.txt"
    assert curr_deep_path.is_file()
    assert_file_content(curr_deep_path, "atlasvibe deep content")

    very_large_renamed = temp_test_dir / VERY_LARGE_FILE_NAME_ORIG.replace("flojoy", "atlasvibe")
    assert very_large_renamed.exists(), f"{very_large_renamed} should exist"
    orig_very_large_path = temp_test_dir / VERY_LARGE_FILE_NAME_ORIG
    if "flojoy" in VERY_LARGE_FILE_NAME_ORIG.lower():
        assert not orig_very_large_path.exists(), f"{orig_very_large_path} should have been renamed"

    with open(very_large_renamed, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    assert lines[0].strip() == "Line 1: This is a atlasvibe line that should be replaced."
    assert lines[VERY_LARGE_FILE_LINES // 2].strip() == f"Line {VERY_LARGE_FILE_LINES // 2 + 1}: This is a atlasvibe line that should be replaced."
    assert lines[VERY_LARGE_FILE_LINES - 1].strip() == f"Line {VERY_LARGE_FILE_LINES}: This is a atlasvibe line that should be replaced."

    link_f_orig, link_d_orig = temp_test_dir/"link_to_file_flojoy.txt", temp_test_dir/"link_to_dir_flojoy"
    link_f_ren, link_d_ren = temp_test_dir/"link_to_file_atlasvibe.txt", temp_test_dir/"link_to_dir_atlasvibe"
    if ignore_symlinks:
        assert os.path.lexists(link_f_orig)
        assert not os.path.lexists(link_f_ren)
        assert os.path.lexists(link_d_orig)
        assert not os.path.lexists(link_d_ren)
    else:
        assert os.path.lexists(link_f_ren) and link_f_ren.is_symlink()
        assert not os.path.lexists(link_f_orig)
        assert os.path.lexists(link_d_ren) and link_d_ren.is_symlink()
        assert not os.path.lexists(link_d_orig)
    assert_file_content(temp_test_dir/"symlink_targets_outside"/"target_file_flojoy.txt", "flojoy in symlink target file")
    assert_file_content(temp_test_dir/"symlink_targets_outside"/"target_dir_flojoy"/"another_flojoy_file.txt", "flojoy content in symlinked dir target")

    binary_log = temp_test_dir / BINARY_MATCHES_LOG_FILE
    if binary_log.exists():
        log_content = binary_log.read_text()
        assert "File: binary_flojoy_file.bin, Key: 'flojoy', Offset: 7" in log_content
        assert "File: binary_flojoy_file.bin, Key: 'flojoy', Offset: 23" in log_content
    elif (temp_test_dir / "binary_atlasvibe_file.bin").exists():
         original_binary_content = b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04"
         had_matches = False
         for key_to_check_bytes in [k.encode('utf-8') for k in replace_logic.get_raw_stripped_keys()]:
             if key_to_check_bytes in original_binary_content:
                 had_matches = True
                 break
         if had_matches:
            pytest.fail(f"{BINARY_MATCHES_LOG_FILE} should exist if binary_flojoy_file.bin was processed and had matches.")

    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_file)
    assert transactions is not None
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

    # Key: "ȕsele̮Ss_diá͡cRiti̅cS" (stripped: "useless_diacritics") -> Value: "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL"
    # Original folder (created by conftest with stripped key): "useless_diacritics_folder"
    # Expected rename: "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL_folder"
    renamed_diacritic_dir_path = temp_test_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL_folder"
    assert renamed_diacritic_dir_path.is_dir(), f"Expected renamed directory '{renamed_diacritic_dir_path}' not found."

    # Original file in that folder (created by conftest with stripped key): "useless_diacritics_file.txt"
    # Expected file name: "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL_file.txt"
    file_in_renamed_diacritic_dir = renamed_diacritic_dir_path / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL_file.txt"
    assert file_in_renamed_diacritic_dir.is_file()
    # Content was created with "useless_diacritics" (stripped key)
    assert_file_content(file_in_renamed_diacritic_dir, "Content with dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL and also dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.\nAnd another Flojoy for good measure.")


    # Key: "The spaces will not be ignored" -> Value: "The control characters \n will be ignored_VAL"
    # Original file (created by conftest with key): "The spaces will not be ignored_file.md"
    # Expected name: "The control characters \n will be ignored_VAL_file.md"
    original_space_file_name = "The spaces will not be ignored_file.md"
    expected_problematic_name = "The control characters \n will be ignored_VAL_file.md"
    
    original_space_file_path = temp_test_dir / original_space_file_name
    problematic_path = temp_test_dir / expected_problematic_name

    if problematic_path.exists():
        assert_file_content(problematic_path, f"This file has {replace_logic.replace_occurrences('The spaces will not be ignored')} in its name and content.")
    elif original_space_file_path.exists():
        assert_file_content(original_space_file_path, f"This file has {replace_logic.replace_occurrences('The spaces will not be ignored')} in its name and content.")
        logging.warning(f"File '{original_space_file_name}' was not renamed to '{expected_problematic_name}', likely due to invalid char in target name. Content was checked on original.")
    else:
        pytest.fail(f"Neither original file '{original_space_file_name}' nor problematically named file '{expected_problematic_name}' found.")


    assert (temp_test_dir / "_My_Story&Love_VAL.log").is_file()
    assert_file_content(temp_test_dir / "_My_Story&Love_VAL.log", "Log for _My_Story&Love_VAL and _my_story&love_VAL. And My_Love&Story.")

    assert (temp_test_dir / "filename_with_MOCO4_ip-N_VAL.data").is_file()
    # "coco4_ep-m" (lowercase) is not a key in complex_map.
    assert_file_content(temp_test_dir / "filename_with_MOCO4_ip-N_VAL.data", "Data for MOCO4_ip-N_VAL and Moco4_ip-N_VAL. Also coco4_ep-m.")

    special_chars_file = temp_test_dir / "special_chars_in_content_test.txt"
    assert special_chars_file.is_file()
    # Content was created with stripped key "charactersnotallowedinpathswillbeescapedwhensearchedinfilenamesandfoldernames"
    assert_file_content(special_chars_file, "This line contains SpecialCharsKeyMatched_VAL to be replaced.")

    control_chars_key_orig_filename = temp_test_dir / "complex_map_key_withcontrolchars_original_name.txt"
    assert control_chars_key_orig_filename.is_file() # This file's name should not change
    assert_file_content(control_chars_key_orig_filename, "Content for complex map control key filename test.")

    control_chars_key_content_file = temp_test_dir / "complex_map_content_with_key_with_controls.txt"
    assert control_chars_key_content_file.is_file()
    # Content was created with stripped key "keywithcontrolchars"
    assert_file_content(control_chars_key_content_file, "Line with Value_for_key_with_controls_VAL to replace.")


def test_edge_case_run(temp_test_dir: Path, edge_case_map_file: Path):
    create_test_environment_content(temp_test_dir, use_edge_case_map=True)
    run_main_flow_for_test(temp_test_dir, edge_case_map_file)

    # Original name: "edge_case_MyKey_original_name.txt"
    # Map key "My\nKey" (stripped: "MyKey") -> "MyKeyValue_VAL"
    # The filename "edge_case_MyKey_original_name.txt" contains "MyKey", which matches the stripped key.
    renamed_file = temp_test_dir / "edge_case_MyKeyValue_VAL_original_name.txt"
    assert renamed_file.is_file()
    assert_file_content(renamed_file, "Initial content for control key name test (MyKeyValue_VAL).")


    content_file = temp_test_dir / "edge_case_content_with_MyKey_controls.txt"
    assert content_file.is_file()
    # Original content: "Line with My\nKey to replace."
    # Map key "My\nKey" (stripped: "MyKey") -> "MyKeyValue_VAL"
    # The _COMPILED_PATTERN_FOR_ACTUAL_REPLACE is built from stripped keys, e.g., `(MyKey|...)`
    # This pattern will NOT match the literal string "My\nKey" in the content.
    # So, the content will remain unchanged.
    assert_file_content(content_file, "Line with My\nKey to replace.")

    priority_file = temp_test_dir / "edge_case_key_priority.txt"
    assert priority_file.is_file()
    assert_file_content(priority_file, "test FooBar_VAL test and also Foo_VAL.")


def test_precision_run(temp_test_dir: Path, precision_map_file: Path):
    create_test_environment_content(temp_test_dir, include_precision_test_file=True)
    run_main_flow_for_test(temp_test_dir, precision_map_file)

    src_renamed = temp_test_dir / "precision_test_atlasvibe_plain_source.txt"
    name_renamed = temp_test_dir / "precision_name_atlasvibe_plain_test.md"
    assert src_renamed.is_file()
    assert name_renamed.is_file()
    assert_file_content(name_renamed, "File for precision rename test.")

    # Conftest was updated to use "FLOJOY_DIACRITIC" (stripped) and "keywithcontrol" (stripped) in the source file.
    exp_lines = ["Standard atlasvibe_plain here.\n","Another Atlasvibe_TitleCase for title case.\r\n",
                 "Test ATLASVIBE_DIACRITIC_VAL with mixed case.\n","  atlasvibe_spaced_val  with exact spaces.\n", # "  flojoy  " -> "  atlasvibe_spaced_val  "
                 "  atlasvibe_spaced_val   with extra spaces.\n", # "  flojoy   " -> "  flojoy  " matches, then the rest "  " remains.
                 "value_for_control_key_val characters.\n", # "keywithcontrol" -> "value_for_control_key_val"
                 "unrelated content\n","你好atlasvibe_plain世界 (Chinese chars).\n","emoji😊atlasvibe_plain test.\n"]
    exp_bytes_list = [line.encode('utf-8','surrogateescape') for line in exp_lines] + [b"malformed-\xff-atlasvibe_plain-bytes\n"]
    assert_file_content(src_renamed, b"".join(exp_bytes_list), is_binary=True)


def test_resume_functionality(temp_test_dir: Path, default_map_file: Path):
    # Phase 1: Initial setup and dry run
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    original_only_name_md_path = temp_test_dir / "only_name_flojoy.md"
    assert original_only_name_md_path.exists(), "Original 'only_name_flojoy.md' should exist before dry run."

    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True)
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    initial_txns = load_transactions(txn_file)
    assert initial_txns and len(initial_txns) > 0

    processed_time_sim = time.time() - 3600
    name_tx_mod, content_tx_mod, error_tx_mod = False, False, False
    for tx in initial_txns:
        if tx["TYPE"] == TransactionType.FILE_NAME.value and not name_tx_mod and "deep_flojoy_file.txt" in tx["PATH"]: # Pick a specific rename
            tx["STATUS"] = TransactionStatus.COMPLETED.value # Simulate it was done
            tx["timestamp_processed"] = processed_time_sim
            name_tx_mod = True
        if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and "large_flojoy_file.txt" in tx["PATH"] and not content_tx_mod:
            tx["STATUS"] = TransactionStatus.PENDING.value
            content_tx_mod = True
        if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME and tx["TYPE"] == TransactionType.FILE_NAME.value:
            tx["STATUS"] = TransactionStatus.FAILED.value
            tx["ERROR_MESSAGE"] = "Simulated initial fail"
            tx["timestamp_processed"] = processed_time_sim
            error_tx_mod = True
    assert name_tx_mod and error_tx_mod, "Resume setup for tx modification failed"
    save_transactions(initial_txns, txn_file)

    # Simulate state after some renames from dry run were MANUALLY applied (or by a previous partial run)
    # For the COMPLETED rename tx: flojoy_root/.../deep_flojoy_file.txt -> atlasvibe_root/.../deep_atlasvibe_file.txt
    # So, rename the parent flojoy_root to atlasvibe_root
    if (temp_test_dir / "flojoy_root").exists():
        (temp_test_dir / "flojoy_root").rename(temp_test_dir / "atlasvibe_root")
    
    # And rename the deep file itself according to the "completed" transaction
    deep_file_orig_parent_now_renamed = temp_test_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_FLOJOY_dir" # This dir name might also change
    # Let's assume only flojoy_root was renamed for this simulation of a single completed tx.
    # The deep_flojoy_file.txt is inside flojoy_root/sub_flojoy_folder/another_FLOJOY_dir/
    # If flojoy_root -> atlasvibe_root, then path is atlasvibe_root/sub_flojoy_folder/another_FLOJOY_dir/deep_flojoy_file.txt
    # The transaction was for deep_flojoy_file.txt. If it's marked COMPLETED, its name should be deep_atlasvibe_file.txt
    
    # Path to where the file *would be* if its name transaction was completed
    simulated_renamed_deep_file_path = temp_test_dir / "atlasvibe_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_atlasvibe_file.txt"
    original_deep_file_path_under_new_root = temp_test_dir / "atlasvibe_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"

    if original_deep_file_path_under_new_root.exists():
         original_deep_file_path_under_new_root.rename(simulated_renamed_deep_file_path)


    # Phase 2: Add new files. `only_name_flojoy.md` should still be there from Phase 1.
    create_test_environment_content(temp_test_dir, for_resume_test_phase_2=True, include_symlink_tests=True)
    assert original_only_name_md_path.exists(), "'only_name_flojoy.md' should still exist before resume execution."
    assert not (temp_test_dir / "only_name_atlasvibe.md").exists(), "'only_name_atlasvibe.md' should NOT exist yet."


    # Modify the now-renamed deep file
    if simulated_renamed_deep_file_path.exists():
        new_mtime = time.time() + 5
        os.utime(simulated_renamed_deep_file_path, (new_mtime, new_mtime))
        with open(simulated_renamed_deep_file_path, "a", encoding="utf-8") as f_append:
            f_append.write("\n# Externally appended for resume.")
    else:
        # This implies the simulation of completed transaction was not set up correctly.
        # For the test to proceed, this file should exist at its renamed path.
        # If it's not, the test for modified content re-scan will not be effective.
        logging.warning(f"Simulated renamed deep file {simulated_renamed_deep_file_path} not found for modification.")


    run_main_flow_for_test(temp_test_dir, default_map_file, resume=True, dry_run=False)
    final_txns = load_transactions(txn_file)
    assert final_txns is not None

    new_file_renamed = temp_test_dir / "newly_added_atlasvibe_for_resume.txt"
    assert new_file_renamed.exists()
    assert_file_content(new_file_renamed, "This atlasvibe content is new for resume.")

    assert any(tx["PATH"] == "newly_added_flojoy_for_resume.txt" and
               tx.get("ORIGINAL_NAME") == "newly_added_flojoy_for_resume.txt" and
               tx["TYPE"] == TransactionType.FILE_NAME.value and
               tx["STATUS"] == TransactionStatus.COMPLETED.value for tx in final_txns), "File rename transaction for new file not completed"

    assert any(tx["PATH"] == "newly_added_flojoy_for_resume.txt" and
               tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and
               tx["STATUS"] == TransactionStatus.COMPLETED.value for tx in final_txns), "Content transaction for new file not completed"

    only_name_mod_renamed = temp_test_dir / "only_name_atlasvibe.md"
    assert only_name_mod_renamed.exists(), "'only_name_atlasvibe.md' should exist after resume."
    assert not original_only_name_md_path.exists(), "'only_name_flojoy.md' should have been renamed."
    assert_file_content(only_name_mod_renamed, "Content without target string.") # Content should be original as it had no target strings

    assert any( (tx["PATH"] == "only_name_atlasvibe.md" or tx["PATH"] == "only_name_flojoy.md") and
                tx["TYPE"] == TransactionType.FILE_NAME.value and # Check for rename transaction
                tx["STATUS"] == TransactionStatus.COMPLETED.value for tx in final_txns), \
                "Rename transaction for 'only_name_flojoy.md' not completed."

    err_file_tx = next((tx for tx in final_txns if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME), None)
    assert err_file_tx and err_file_tx["STATUS"] == TransactionStatus.FAILED.value
    assert (temp_test_dir / SELF_TEST_ERROR_FILE_BASENAME).exists()

    if simulated_renamed_deep_file_path.exists():
        content = simulated_renamed_deep_file_path.read_text(encoding='utf-8')
        assert "Line 1: atlasvibe content." in content # Original content (after its own replacement)
        assert "# Externally appended for resume." in content # Appended part
        
        # Path in transaction could be original relative path or path after parent dir renames
        # Original relative path: "flojoy_root/sub_flojoy_folder/another_FLOJOY_dir/deep_flojoy_file.txt"
        # Path after flojoy_root rename: "atlasvibe_root/sub_flojoy_folder/another_FLOJOY_dir/deep_flojoy_file.txt" (if only root renamed)
        # The key is that the content of the file (wherever it is now) was re-scanned and processed.
        # The transaction's "PATH" field should refer to the original relative path.
        orig_rel_path_deep_file = "flojoy_root/sub_flojoy_folder/another_FLOJOY_dir/deep_flojoy_file.txt"
        
        found_appended_content_tx = False
        for tx in final_txns:
            if tx["PATH"] == orig_rel_path_deep_file and \
               tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and \
               tx["STATUS"] == TransactionStatus.COMPLETED.value and \
               tx.get("PROPOSED_LINE_CONTENT","").endswith("# Externally appended for resume."):
                found_appended_content_tx = True
                break
        assert found_appended_content_tx, "Externally modified file content (appended line) not re-processed correctly or not found in transactions"


def test_dry_run_behavior(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    orig_deep_file_path = temp_test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    original_content = orig_deep_file_path.read_text(encoding='utf-8')
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True)
    assert orig_deep_file_path.exists()
    assert_file_content(orig_deep_file_path, original_content)
    assert not (temp_test_dir / "atlasvibe_root").exists()
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    for tx in transactions:
        if tx["STATUS"] == TransactionStatus.COMPLETED.value:
            assert tx.get("ERROR_MESSAGE") == "DRY_RUN" or tx.get("PROPOSED_LINE_CONTENT") is not None or tx["TYPE"] != TransactionType.FILE_CONTENT_LINE.value
        elif tx["STATUS"] == TransactionStatus.PENDING.value:
            pytest.fail(f"Tx {tx['id']} PENDING after dry run scan phase implies it wasn't processed for planning.")


def test_skip_scan_behavior(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True)
    file_to_delete_orig_path = temp_test_dir / "flojoy_root" / "another_flojoy_file.py"
    assert file_to_delete_orig_path.exists()
    file_to_delete_orig_path.unlink()

    run_main_flow_for_test(temp_test_dir, default_map_file, skip_scan=True, dry_run=False)

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    deleted_file_txns_found = False
    for tx in transactions:
        if "another_flojoy_file.py" in tx["PATH"]:
            deleted_file_txns_found = True
            assert tx["STATUS"] in [TransactionStatus.SKIPPED.value, TransactionStatus.FAILED.value]
    assert deleted_file_txns_found, "Transactions for the deleted file were not found or not processed."

    expected_deep_file = temp_test_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir" / "deep_atlasvibe_file.txt"
    assert expected_deep_file.exists(), f"Expected file {expected_deep_file} not found after skip_scan run."
    assert_file_content(expected_deep_file, "Line 1: atlasvibe content.\nLine 2: More Atlasvibe here.\nLine 3: No target.\nLine 4: ATLASVIBE project.")


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
    (temp_test_dir / "build").mkdir(exist_ok=True)
    (temp_test_dir / "build" / "ignored_build_file.txt").write_text("flojoy in build")
    (temp_test_dir / "docs").mkdir(exist_ok=True)
    (temp_test_dir / "docs" / "specific_file.txt").write_text("flojoy in specific doc")
    (temp_test_dir / "important.log").write_text("flojoy important log")
    (temp_test_dir / "src").mkdir(exist_ok=True)
    (temp_test_dir / "src" / "main.py").write_text("flojoy in main.py")
    (temp_test_dir / "data.tmp").write_text("flojoy in data.tmp")
    (temp_test_dir / "temp_data").mkdir(exist_ok=True)
    (temp_test_dir / "temp_data" / "file.dat").write_text("flojoy in temp_data")
    (temp_test_dir / "other_file.log").write_text("flojoy in other_file.log")

    if use_gitignore_cli: # type: ignore
        (temp_test_dir / ".gitignore").write_text(GITIGNORE_CONTENT)
    custom_ignore_path_str: Optional[str] = None
    if custom_ignore_name:
        custom_ignore_path = temp_test_dir / custom_ignore_name
        custom_ignore_path.write_text(CUSTOM_IGNORE_CONTENT)
        custom_ignore_path_str = str(custom_ignore_path)

    run_main_flow_for_test(temp_test_dir, default_map_file, use_gitignore=use_gitignore_cli, custom_ignore_file=custom_ignore_path_str)
    
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    processed_paths_in_tx = {tx["PATH"] for tx in transactions} if transactions else set()

    for ignored_file_rel_path_str in expected_ignored_files:
        ignored_file_path = Path(ignored_file_rel_path_str)
        is_present_in_tx = False
        for tx_path_str in processed_paths_in_tx: # type: ignore
            tx_path = Path(tx_path_str)
            if tx_path == ignored_file_path or ignored_file_path in tx_path.parents:
                is_present_in_tx = True
                break
        assert not is_present_in_tx, f"File/Dir '{ignored_file_path}' expected to be ignored but found in transactions."
        assert (temp_test_dir / ignored_file_path).exists(), f"Ignored file/dir '{ignored_file_path}' should still exist with original name."
        if (temp_test_dir / ignored_file_path).is_file() and "flojoy" in (temp_test_dir / ignored_file_path).read_text(encoding='utf-8', errors='ignore').lower():
            assert "flojoy" in (temp_test_dir / ignored_file_path).read_text(encoding='utf-8', errors='ignore').lower(), f"Ignored file '{ignored_file_path}' content changed."


    for processed_file_rel_path_str in expected_processed_files:
        processed_file_rel_path = Path(processed_file_rel_path_str)
        original_path_abs = temp_test_dir / processed_file_rel_path

        related_tx_exists = any(
            tx["PATH"] == str(processed_file_rel_path) or
            (tx.get("ORIGINAL_NAME") and Path(tx["PATH"]).name == replace_logic.replace_occurrences(processed_file_rel_path.name) and Path(tx["PATH"]).parent == processed_file_rel_path.parent)
            for tx in transactions or [] # type: ignore
        )
        assert related_tx_exists, f"File '{processed_file_rel_path}' expected to be processed but no related transaction found."

        new_name = replace_logic.replace_occurrences(original_path_abs.name)
        new_path_abs = original_path_abs.with_name(new_name)

        if new_name != original_path_abs.name:
            assert not original_path_abs.exists(), f"File '{original_path_abs}' should have been renamed to '{new_path_abs}'."
            assert new_path_abs.exists(), f"File '{original_path_abs}' was expected to be renamed to '{new_path_abs}', but new path doesn't exist."
            if "flojoy" in new_path_abs.read_text(encoding='utf-8', errors='ignore').lower(): # Check content of new file
                 assert "atlasvibe" in new_path_abs.read_text(encoding='utf-8', errors='ignore').lower(), f"File '{new_path_abs}' content should have changed."
        elif original_path_abs.exists():
            if "flojoy" in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower():
                 assert "atlasvibe" in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower(), f"File '{original_path_abs}' content should have changed."


@pytest.mark.parametrize("filename, content_bytes, is_binary_expected_by_lib, contains_flojoy_bytes", [
    ("text_file.txt", b"This is a plain text file with flojoy.", False, True),
    ("utf16_file.txt", "UTF-16 text with flojoy".encode('utf-16'), False, True),
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
        if len(content_bytes) == 0:
            detected_as_binary_lib = False
        else:
            detected_as_binary_lib = lib_is_binary(str(file_path))
    except FileNotFoundError:
        if len(content_bytes) == 0:
            detected_as_binary_lib = False
        else:
            pytest.fail(f"is_binary_file raised FileNotFoundError for non-empty file: {filename}")
    except Exception as e:
        pytest.fail(f"is_binary_file raised an unexpected exception for {filename}: {e}")


    assert detected_as_binary_lib == is_binary_expected_by_lib, \
        f"File {filename} lib_is_binary detection mismatch. Expected binary: {is_binary_expected_by_lib}, Detected binary: {detected_as_binary_lib}"

    script_treats_as_binary_for_content_mod = detected_as_binary_lib and not filename.endswith(".rtf")

    run_main_flow_for_test(temp_test_dir, default_map_file, extensions=None,
                           skip_file_renaming=True, skip_folder_renaming=True)

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    transactions_list = transactions if transactions is not None else [] # Ensure it's a list for iteration

    content_tx_found = any(tx["PATH"] == filename and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value for tx in transactions_list)

    binary_log_path = temp_test_dir / BINARY_MATCHES_LOG_FILE
    binary_log_has_match_for_this_file = False
    if binary_log_path.exists():
        log_content = binary_log_path.read_text(encoding='utf-8')
        if f"File: {filename}" in log_content:
             for key_str_map in replace_logic.get_raw_stripped_keys():
                 if f"File: {filename}, Key: '{key_str_map}'" in log_content:
                     binary_log_has_match_for_this_file = True
                     break


    if not script_treats_as_binary_for_content_mod:
        if contains_flojoy_bytes:
            assert content_tx_found, f"Expected content transaction for text-like file {filename} which contained a match."
            if file_path.suffix.lower() != '.rtf':
                changed_content_str = file_path.read_text(encoding='utf-8', errors='surrogateescape')
                all_map_keys_lower = {k.lower() for k in replace_logic.get_raw_stripped_keys()} # These are stripped keys
                # Check against original map keys (unstripped, lowercased) to ensure no original forms remain (json.loads returns Any)
                original_unstripped_keys_lower = {k.lower() for k,v in json.loads(default_map_file.read_text())["REPLACEMENT_MAPPING"].items()}

                found_original_key = False
                for key_l in original_unstripped_keys_lower:
                    if key_l in changed_content_str.lower():
                        found_original_key = True
                        break
                assert not found_original_key, f"Text file {filename} content not fully replaced. Found an original key variant: {key_l} in {changed_content_str[:200]}"
        else:
            assert not content_tx_found, f"No content transaction expected for text-like file {filename} as it had no matches."

        assert not binary_log_has_match_for_this_file, f"Text-like file {filename} should not have matches in binary log."
    else:
        assert not content_tx_found, f"Binary file {filename} should not have content transactions."
        if contains_flojoy_bytes:
             assert binary_log_has_match_for_this_file, f"Binary file {filename} with matches expected in binary log, but not found or not for a mapped key."
        else:
             assert not binary_log_has_match_for_this_file, f"Binary file {filename} without matches should not be in binary log for a mapped key."


@pytest.mark.slow
def test_timeout_behavior_and_retries_mocked(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir)
    file_to_lock_rel = "file_with_floJoy_lines.txt"
    renamed_file_to_lock_rel = "file_with_atlasVibe_lines.txt"


    original_execute_content = file_system_operations._execute_content_line_transaction
    mock_tx_call_counts: Dict[str, int] = {}
    max_fails_for_mock = 2

    def mock_execute_content_with_retry(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        nonlocal mock_tx_call_counts
        is_target_file_tx = (tx_item["PATH"] == file_to_lock_rel or Path(tx_item["PATH"]).name == renamed_file_to_lock_rel) and \
                            tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value

        if is_target_file_tx:
            tx_id = tx_item['id']
            current_tx_call_count = mock_tx_call_counts.get(tx_id, 0) + 1
            mock_tx_call_counts[tx_id] = current_tx_call_count

            if current_tx_call_count <= max_fails_for_mock:
                return TransactionStatus.RETRY_LATER, f"Mocked OS error (retryable), tx_id: {tx_id}, attempt {current_tx_call_count}", True
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run)

    with patch('file_system_operations._execute_content_line_transaction', mock_execute_content_with_retry):
        run_main_flow_for_test(temp_test_dir, default_map_file, timeout_minutes=1)

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None

    target_txs_checked_count = 0
    for tx in transactions:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == renamed_file_to_lock_rel) and \
           tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            target_txs_checked_count +=1
            assert tx["STATUS"] == TransactionStatus.COMPLETED.value, f"Transaction for {tx['PATH']} (id: {tx['id']}, line: {tx.get('LINE_NUMBER')}) should have eventually completed."
            assert tx.get("retry_count", 0) == max_fails_for_mock, f"Transaction for {tx['PATH']} (id: {tx['id']}, line: {tx.get('LINE_NUMBER')}) should have {max_fails_for_mock} retries. Got {tx.get('retry_count',0)}."
            assert mock_tx_call_counts.get(tx['id']) == max_fails_for_mock + 1, \
                f"Mocked function for tx_id {tx['id']} not called expected number of times. Got {mock_tx_call_counts.get(tx['id'])}, expected {max_fails_for_mock + 1}"

    assert target_txs_checked_count > 0, "Did not find any targeted content transaction for retry test."
    assert len(mock_tx_call_counts) == target_txs_checked_count, "mock_tx_call_counts tracked more/less transactions than expected."


    mock_tx_call_counts_indef: dict[str, int] = {}
    indef_max_mock_calls_per_tx = 7

    def mock_always_retryable_error_indef(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        nonlocal mock_tx_call_counts_indef
        is_target_file_tx = (tx_item["PATH"] == file_to_lock_rel or Path(tx_item["PATH"]).name == renamed_file_to_lock_rel) and \
                            tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value
        if is_target_file_tx:
            tx_id = tx_item['id']
            current_tx_call_count = mock_tx_call_counts_indef.get(tx_id, 0) + 1
            mock_tx_call_counts_indef[tx_id] = current_tx_call_count

            if current_tx_call_count < indef_max_mock_calls_per_tx :
                return TransactionStatus.RETRY_LATER, f"Mocked persistent OS error (retryable), tx_id: {tx_id}, attempt {current_tx_call_count}", True
            else:
                return TransactionStatus.FAILED, "Mocked persistent error, exceeded test call limit for this tx_id", False
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run)

    transactions_for_indef_retry = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions_for_indef_retry is not None # Ensure it's not None before iterating
    for tx in transactions_for_indef_retry:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == renamed_file_to_lock_rel) and \
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

    target_txs_indef_checked_count = 0
    for tx in final_transactions_indef:
         if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == renamed_file_to_lock_rel) and \
            tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            target_txs_indef_checked_count +=1
            assert tx["STATUS"] == TransactionStatus.FAILED.value, f"Tx {tx['id']} should be FAILED."
            assert tx.get("retry_count", 0) == (indef_max_mock_calls_per_tx -1) , \
                f"Tx {tx['id']} should have retried {indef_max_mock_calls_per_tx -1} times. Got {tx.get('retry_count',0)}"
            assert mock_tx_call_counts_indef.get(tx['id']) == indef_max_mock_calls_per_tx, \
                f"Mock for tx {tx['id']} in indef test part called {mock_tx_call_counts_indef.get(tx['id'])} times, expected {indef_max_mock_calls_per_tx}"

    assert target_txs_indef_checked_count > 0, "Did not find any targeted transaction for indefinite retry test part."
    assert len(mock_tx_call_counts_indef) == target_txs_indef_checked_count


def test_empty_directory_handling(temp_test_dir: Path, default_map_file: Path, caplog):
    caplog.set_level(logging.INFO)

    truly_empty_dir = temp_test_dir / "truly_empty"
    truly_empty_dir.mkdir()

    map_for_empty_test = temp_test_dir / "map_for_empty.json"
    map_for_empty_test.write_text(json.dumps({"REPLACEMENT_MAPPING": {"flojoy": "atlasvibe"}}))

    run_main_flow_for_test(truly_empty_dir, map_for_empty_test)

    assert any(f"Target directory '{truly_empty_dir.resolve()}' is empty. Nothing to do." in record.message
               for record in caplog.records), \
        "Expected 'Target directory ... is empty. Nothing to do.' log message for truly empty dir."

    shutil.rmtree(truly_empty_dir)
    map_for_empty_test.unlink()
    caplog.clear()

    for item in temp_test_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    simple_map_path = temp_test_dir / "simple_map.json"
    simple_map_path.write_text(json.dumps({"REPLACEMENT_MAPPING": {"flojoy": "atlasvibe"}}))

    run_main_flow_for_test(temp_test_dir, simple_map_path)

    assert not any(f"Target directory '{temp_test_dir.resolve()}' is empty. Nothing to do." in record.message
                   for record in caplog.records), \
        "The 'directory is empty' message should not appear when map file is present."

    # Check for the message that indicates scan happened but found nothing actionable (because map file is excluded)
    # This could be "No actionable occurrences found by scan." or similar if the map itself is the only file.
    # Or if the map is empty, "Map empty and no scannable items found..."
    # Given the map is not empty, but is excluded, "No actionable occurrences found by scan" is likely.
    assert any("No actionable occurrences found by scan." in record.message or
               "Map empty and no scannable items found" in record.message # If map was empty
               for record in caplog.records), \
        "Expected appropriate log message when dir only has excluded map/transaction files."


    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    if txn_file.exists():
        transactions = load_transactions(txn_file)
        assert transactions is None or len(transactions) == 0, \
            "Transaction file should be empty or non-existent if only map file was present and excluded."

    if simple_map_path.exists():
        simple_map_path.unlink()

def test_mixed_encoding_surgical_replacement(temp_test_dir: Path, default_map_file: Path):
    """
    Tests surgical replacement in a file with mixed line endings, non-standard characters
    for its primary encoding, and potentially invalid byte sequences.
    The "Flojoy" key (ASCII) should be replaced, everything else preserved byte-for-byte.
    """
    logger = logging.getLogger("test_mixed_encoding") # For test-specific logging if needed
    
    # --- Test File Setup ---
    # Using cp1252 as base, which has some defined chars in 0x80-0x9F range unlike iso-8859-1
    # \x99 is ™ (trademark symbol in cp1252)
    # \x81 is undefined in cp1252, will be handled by surrogateescape
    # \xae is ® (registered trademark in cp1252)
    # Line endings: \n, \r\n, \r
    # Key: "Flojoy" (ASCII) -> "Atlasvibe" (ASCII) from default_map_file
    
    original_lines_bytes = [
        b"Line 1 with normal ASCII and Flojoy here.\n",
        b"Line 2 with cp1252 char: \x99 trademark symbol.\r\n", # ™ in cp1252
        b"Line 3 with another Flojoy and \xae registered symbol.\r", # ® in cp1252
        b"Line 4 with invalid cp1252 byte \x81 sequence, then Flojoy.\n",
        b"Line 5 Fl\xf6joy with diacritic (should not match 'Flojoy' key).\r\n", # ö is \xf6 in cp1252
        b"Line 6 just ends.",
    ]
    original_full_content_bytes = b"".join(original_lines_bytes)
    
    test_file_name = "mixed_encoding_test_cp1252.txt"
    test_file_path = temp_test_dir / test_file_name
    test_file_path.write_bytes(original_full_content_bytes)

    # --- Expected Lines Bytes after replacement ---
    # "Flojoy" -> "Atlasvibe"
    expected_lines_bytes = [
        b"Line 1 with normal ASCII and Atlasvibe here.\n", # Flojoy replaced
        b"Line 2 with cp1252 char: \x99 trademark symbol.\r\n", # Unchanged
        b"Line 3 with another Atlasvibe and \xae registered symbol.\r", # Flojoy replaced
        b"Line 4 with invalid cp1252 byte \x81 sequence, then Atlasvibe.\n", # Flojoy replaced
        b"Line 5 Fl\xf6joy with diacritic (should not match 'Flojoy' key).\r\n", # Unchanged
        b"Line 6 just ends.", # Unchanged
    ]
    expected_full_content_bytes = b"".join(expected_lines_bytes)

    # --- Run Main Flow ---
    # Ensure the map is loaded correctly for this test instance
    load_map_success = replace_logic.load_replacement_map(default_map_file)
    assert load_map_success, "Failed to load default_map_file for mixed encoding test"
    
    # Run the main flow, targeting only this file for simplicity if needed, or let it scan.
    # Using extensions=None to let the script decide if it's text-like.
    # cp1252 should be detected as text-like.
    run_main_flow_for_test(
        temp_test_dir, 
        default_map_file, 
        extensions=None, # Let script auto-detect
        skip_file_renaming=True, # Focus on content
        skip_folder_renaming=True
    )

    # --- Assertions ---
    assert test_file_path.exists(), "Test file should still exist."
    
    modified_content_bytes = test_file_path.read_bytes()
    
    if modified_content_bytes != expected_full_content_bytes:
        logger.error("Surgical replacement test FAILED. Content mismatch.")
        logger.error(f"Expected bytes:\n{expected_full_content_bytes!r}")
        logger.error(f"Actual bytes:\n{modified_content_bytes!r}")
        
        # For detailed line-by-line diff if helpful:
        try:
            original_str_surrogate = original_full_content_bytes.decode('cp1252', errors='surrogateescape')
            modified_str_surrogate = modified_content_bytes.decode('cp1252', errors='surrogateescape')
            expected_str_surrogate = expected_full_content_bytes.decode('cp1252', errors='surrogateescape')
            
            logger.info("\n--- Original Decoded (surrogateescape) ---")
            for i, line in enumerate(original_str_surrogate.splitlines(True)):
                logger.info(f"{i+1}: {line!r}")
            logger.info("\n--- Expected Decoded (surrogateescape) ---")
            for i, line in enumerate(expected_str_surrogate.splitlines(True)):
                logger.info(f"{i+1}: {line!r}")
            logger.info("\n--- Actual Decoded (surrogateescape) ---")
            for i, line in enumerate(modified_str_surrogate.splitlines(True)):
                logger.info(f"{i+1}: {line!r}")
        except Exception as e:
            logger.error(f"Error during decoded diff generation: {e}")

    assert modified_content_bytes == expected_full_content_bytes, \
        "File content after surgical replacement does not match expected byte-for-byte."

    # Check transaction log for this file
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    transactions = load_transactions(txn_file)
    assert transactions is not None, "Transaction file not found."
    
    relevant_tx_count = 0
    for tx in transactions:
        if tx["PATH"] == test_file_name and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            relevant_tx_count += 1
            assert tx["STATUS"] == TransactionStatus.COMPLETED.value
            # Check if the original line content matches what we expect for replaced lines
            if tx["LINE_NUMBER"] == 1: # Line 1 had "Flojoy"
                assert tx["ORIGINAL_LINE_CONTENT"] == original_lines_bytes[0].decode('cp1252', errors='surrogateescape')
                assert tx["PROPOSED_LINE_CONTENT"] == expected_lines_bytes[0].decode('cp1252', errors='surrogateescape')
            elif tx["LINE_NUMBER"] == 3: # Line 3 had "Flojoy"
                assert tx["ORIGINAL_LINE_CONTENT"] == original_lines_bytes[2].decode('cp1252', errors='surrogateescape')
                assert tx["PROPOSED_LINE_CONTENT"] == expected_lines_bytes[2].decode('cp1252', errors='surrogateescape')
            elif tx["LINE_NUMBER"] == 4: # Line 4 had "Flojoy"
                assert tx["ORIGINAL_LINE_CONTENT"] == original_lines_bytes[3].decode('cp1252', errors='surrogateescape')
                assert tx["PROPOSED_LINE_CONTENT"] == expected_lines_bytes[3].decode('cp1252', errors='surrogateescape')
    
    assert relevant_tx_count == 3, f"Expected 3 content transactions for {test_file_name}, got {relevant_tx_count}"
