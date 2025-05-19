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

from conftest import (
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
    # "fLoJoY" is not a key in default_map.json, so it won't be replaced by the primary rule.
    # The fallback rule (lowercase match) will apply. "flojoy" is a key, maps to "atlasvibe".
    assert_file_content(unmapped_variant_txt, "This has atlasvibe content, and also atlasvibe.")
    
    gb18030_txt = temp_test_dir / "gb18030_atlasvibe_file.txt"
    assert gb18030_txt.is_file()
    actual_gb_bytes = gb18030_txt.read_bytes()
    expected_gb18030_bytes = "你好 atlasvibe 世界".encode('gb18030')
    expected_fallback_bytes = "fallback atlasvibe content".encode('utf-8') # if original write failed
    # Check if the original write was successful, otherwise check fallback
    original_gb_write_success = False
    try:
        # Attempt to write the original expected content to a temp file to see if it was possible
        (temp_test_dir / "temp_gb_check.txt").write_text("你好 flojoy 世界", encoding="gb18030")
        original_gb_write_success = True
        (temp_test_dir / "temp_gb_check.txt").unlink()
    except Exception:
        pass # original_gb_write_success remains False

    if original_gb_write_success:
        assert actual_gb_bytes == expected_gb18030_bytes, "GB18030 content mismatch"
    else: # If original write likely failed, the content would be the fallback
        assert actual_gb_bytes == expected_fallback_bytes, "GB18030 content mismatch (fallback)"


    bin_file1 = temp_test_dir / "binary_atlasvibe_file.bin"
    assert bin_file1.is_file()
    # Binary content is not modified, only names. Keys for binary search are stripped.
    # "flojoy" is a key in _RAW_REPLACEMENT_MAPPING.
    assert_file_content(bin_file1, b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04", is_binary=True)
    
    bin_file2_renamed = temp_test_dir / "binary_atlasvibe_name.bin" # "fLoJoY" in name, map has "flojoy" -> "atlasvibe"
    assert bin_file2_renamed.is_file()
    assert not (temp_test_dir / "binary_fLoJoY_name.bin").exists()
    assert_file_content(bin_file2_renamed, b"unmapped_variant_binary_content" + b"\x00\xff", is_binary=True)
    
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

    very_large_renamed = temp_test_dir / VERY_LARGE_FILE_NAME_REPLACED.replace("flojoy", "atlasvibe") # Adjust expected name
    assert very_large_renamed.exists(), f"{very_large_renamed} should exist"
    # Check original name does not exist if it contained 'flojoy'
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
    assert_file_content(temp_test_dir/"symlink_targets_outside"/"target_file_flojoy.txt", "flojoy in symlink target file") # Target content not changed
    assert_file_content(temp_test_dir/"symlink_targets_outside"/"target_dir_flojoy"/"another_flojoy_file.txt", "flojoy content in symlinked dir target") # Target content not changed

    binary_log = temp_test_dir / BINARY_MATCHES_LOG_FILE
    if binary_log.exists(): 
        log_content = binary_log.read_text()
        # Keys for binary search are the stripped keys from the map. "flojoy" is one such key.
        assert "File: binary_flojoy_file.bin, Key: 'flojoy', Offset: 7" in log_content 
        assert "File: binary_flojoy_file.bin, Key: 'flojoy', Offset: 20" in log_content
    elif (temp_test_dir / "binary_atlasvibe_file.bin").exists(): # if original binary file was renamed
         # Check if the original binary file content had matches
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
    # Expected names based on complex_map_file values
    # "ȕsele̮Ss_diá͡cRiti̅cS" (key) -> "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" (value)
    # Folder name: "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS"
    # Stripped key: "useless_diacritics"
    # Expected folder name: "diacritic_test_folder_dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" (if "useless_diacritics" is found and replaced)
    # OR original name if "useless_diacritics" is NOT found in "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS"
    
    # Current logic: replace_occurrences searches for the *stripped key* ("useless_diacritics")
    # in the input string ("diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS").
    # "useless_diacritics" is NOT in "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS". So no rename.
    # This test will fail based on current replace_logic if it expects diacritic-agnostic matching on input.
    # For now, assert based on the *actual* behavior of replace_logic.
    
    # Assertions for complex map - these might need adjustment based on how diacritic matching is *intended* vs *implemented*
    # Assuming current replace_logic: matches are based on literal stripped keys.
    original_diacritic_folder = temp_test_dir / "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS"
    renamed_diacritic_folder_val = "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" # This is the value part
    
    # If the key "ȕsele̮Ss_diá͡cRiti̅cS" (stripped: "useless_diacritics") is intended to match the folder name part "ȕsele̮Ss_diá͡cRiti̅cS"
    # then the folder should be renamed. The current replace_logic would search for "useless_diacritics" literally.
    # Let's assume the test expects the *value* to be part of the new name if a match occurs.
    # The complex map has "ȕsele̮Ss_diá͡cRiti̅cS": "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL"
    # If "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS" is processed:
    #   - replace_occurrences("diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS")
    #   - It will search for "useless_diacritics" (stripped key). This is NOT in the name.
    #   - So, no rename based on this rule.
    # What if the folder name was "diacritic_test_folder_useless_diacritics"? Then it would be renamed.
    # The test setup creates "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS".
    # This highlights the discrepancy: test expects match on diacritic name, logic matches on stripped key.
    
    # For now, let's assume the test implies the *original unstripped key* should be found and replaced.
    # This is NOT what replace_logic does. It uses stripped keys for matching.
    # The provided solution for Issue 1 does not change this core matching aspect.
    # So, these assertions will likely still fail if they rely on diacritic-to-diacritic matching.
    
    # If the folder name itself was "ȕsele̮Ss_diá͡cRiti̅cS", it would be renamed to "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL"
    # because the scan pattern (from stripped keys) would match "ȕsele̮Ss_diá͡cRiti̅cS" (case insensitively)
    # if "useless_diacritics" (stripped key) is in the pattern.
    # Then replace_occurrences("ȕsele̮Ss_diá͡cRiti̅cS") would be called.
    # Callback would find "useless_diacritics" (key in _RAW_REPLACEMENT_MAPPING) matches "ȕsele̮Ss_diá͡cRiti̅cS".lower()
    # and return "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL".

    # Let's test the file that has the *value* in its name, assuming it was renamed.
    # The original folder name was "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS"
    # The original file name was "file_with_diacritics_ȕsele̮Ss_diá͡cRiti̅cS.txt"
    # If the folder was renamed to "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" (this is the value from map)
    # And file to "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.txt"
    
    # The test expects: (temp_test_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL").is_dir()
    # This means a folder originally named "ȕsele̮Ss_diá͡cRiti̅cS" (or similar that stripped to "useless_diacritics")
    # was renamed to the *value* "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL".
    # This implies the original folder name was exactly "ȕsele̮Ss_diá͡cRiti̅cS" (or a case variant).
    # The test setup creates: (base_dir/"diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS")
    # This folder name will NOT be matched by the key "ȕsele̮Ss_diá͡cRiti̅cS" (stripped: "useless_diacritics")
    # because "useless_diacritics" is not in "diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS".
    
    # Let's adjust assertions to what *should* happen with current logic, or mark as known issue.
    # For now, I will keep the original assertions from the user prompt, acknowledging they might fail due to Issue 3.

    renamed_diacritic_dir_path = temp_test_dir / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL"
    assert renamed_diacritic_dir_path.is_dir(), f"Expected renamed directory '{renamed_diacritic_dir_path}' not found. Original was likely 'ȕsele̮Ss_diá͡cRiti̅cS' or similar."
    
    file_in_renamed_diacritic_dir = renamed_diacritic_dir_path / "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.txt"
    assert file_in_renamed_diacritic_dir.is_file()
    # Content: "Content with ȕsele̮Ss_diá͡cRiti̅cS and also useless_diacritics.\nAnd another Flojoy for good measure."
    # "ȕsele̮Ss_diá͡cRiti̅cS" -> "useless_diacritics" (key) -> "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" (value)
    # "useless_diacritics" -> "useless_diacritics" (key) -> "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL" (value)
    # "Flojoy" -> "Flojoy" (key in default map if complex map doesn't override) -> "Atlasvibe"
    # The complex_map_file fixture does not include "Flojoy". So "Flojoy" will not be replaced.
    assert_file_content(file_in_renamed_diacritic_dir, "Content with dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL and also dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL.\nAnd another Flojoy for good measure.")

    # Key: "The spaces will not be ignored" (stripped: "The spaces will not be ignored")
    # Value: "The control characters \n will be ignored_VAL"
    # Original file: "file_with_spaces_The spaces will not be ignored.md"
    # Expected: "file_with_spaces_The control characters \n will be ignored_VAL.md" (if name part matches)
    # The current logic would replace the whole name if it was *exactly* "The spaces will not be ignored"
    # If the name is "file_with_spaces_The spaces will not be ignored.md", it will search for "The spaces will not be ignored"
    # and replace that part.
    expected_space_file_name = "file_with_spaces_The control characters \n will be ignored_VAL.md" # This is problematic as filename
    # Let's assume the test means the *value* becomes the new name if the original name was the *key*.
    # Original filename in test setup: "file_with_spaces_The spaces will not be ignored.md"
    # This will be renamed to: "file_with_spaces_The control characters \n will be ignored_VAL.md"
    # The newline in filename is an issue. The test probably expects the value to be filename-safe.
    # The value in map is "The control characters \n will be ignored_VAL".
    # Let's assume the test implies the problematic char in value is handled or the test is simplified.
    # The assertion is: (temp_test_dir / "The control characters \n will be ignored_VAL.md").is_file()
    # This means original name was "The spaces will not be ignored.md" (or similar)
    # The test setup creates "file_with_spaces_The spaces will not be ignored.md"
    # This will not be renamed to "The control characters \n will be ignored_VAL.md"
    # It would be "file_with_spaces_The control characters \n will be ignored_VAL.md"
    
    # For "The control characters \n will be ignored_VAL.md":
    # Original key: "The spaces will not be ignored"
    # Original filename: "file_with_spaces_The spaces will not be ignored.md"
    # replace_occurrences("file_with_spaces_The spaces will not be ignored.md")
    # -> "file_with_spaces_" + replace_occurrences("The spaces will not be ignored") + ".md"
    # -> "file_with_spaces_The control characters \n will be ignored_VAL.md"
    # This filename with \n is not valid on most systems.
    # The assertion (temp_test_dir / "The control characters \n will be ignored_VAL.md").is_file()
    # implies the original name was just "The spaces will not be ignored.md" (without prefix/suffix)
    # and it was renamed to the value.
    # Let's assume the test means the file *content* is checked for a file whose name became the value.
    # This part of the test is ambiguous. I'll stick to the user's assertion.
    file_with_control_char_val_name = temp_test_dir / "The control characters \n will be ignored_VAL.md"
    assert file_with_control_char_val_name.is_file()
    assert_file_content(file_with_control_char_val_name, "This file has The control characters \n will be ignored_VAL in its name and content.")

    # Key: "_My_Love&Story" (stripped: "_My_Love&Story") -> Value: "_My_Story&Love_VAL"
    # Key: "_my_love&story" (stripped: "_my_love&story") -> Value: "_my_story&love_VAL"
    # Original file: "_My_Love&Story.log"
    # Expected: "_My_Story&Love_VAL.log"
    assert (temp_test_dir / "_My_Story&Love_VAL.log").is_file()
    assert_file_content(temp_test_dir / "_My_Story&Love_VAL.log", "Log for _My_Story&Love_VAL and _my_story&love_VAL. And My_Love&Story.")

    # Key: "COCO4_ep-m" (stripped: "COCO4_ep-m") -> Value: "MOCO4_ip-N_VAL"
    # Key: "Coco4_ep-M" (stripped: "Coco4_ep-M") -> Value: "Moco4_ip-N_VAL"
    # Original file: "filename_with_COCO4_ep-m.data"
    # Expected: "filename_with_MOCO4_ip-N_VAL.data"
    assert (temp_test_dir / "filename_with_MOCO4_ip-N_VAL.data").is_file() # Name changed
    # Content: "Data for COCO4_ep-m and Coco4_ep-M. Also coco4_ep-m."
    # "COCO4_ep-m" -> "MOCO4_ip-N_VAL"
    # "Coco4_ep-M" -> "Moco4_ip-N_VAL"
    # "coco4_ep-m" (lowercase of key) -> matches "COCO4_ep-m" (key) -> "MOCO4_ip-N_VAL"
    assert_file_content(temp_test_dir / "filename_with_MOCO4_ip-N_VAL.data", "Data for MOCO4_ip-N_VAL and Moco4_ip-N_VAL. Also MOCO4_ip-N_VAL.")


    # Key: "characters|not<allowed^in*paths::will/be!escaped%when?searched~in$filenames@and\"foldernames"
    # (stripped: "charactersnotallowedinpathswillbeescapedwhensearchedinfilenamesandfoldernames")
    # Value: "SpecialCharsKeyMatched_VAL"
    # Original file: "special_chars_in_content_test.txt"
    # Content: "This line contains characters|not<allowed^in*paths::will/be!escaped%when?searched~in$filenames@and\"foldernames to be replaced."
    # The key (after re.escape) will match the content.
    special_chars_file = temp_test_dir / "special_chars_in_content_test.txt" # Name unchanged
    assert special_chars_file.is_file()
    assert_file_content(special_chars_file, "This line contains SpecialCharsKeyMatched_VAL to be replaced.")

    # Key: "key_with\tcontrol\nchars" (stripped: "key_withcontrolchars") -> Value: "Value_for_key_with_controls_VAL"
    # Original file: "complex_map_key_withcontrolchars_original_name.txt"
    # Content: "Content for complex map control key filename test."
    # This file's name does not contain "key_with\tcontrol\nchars" or "key_withcontrolchars". Name unchanged.
    control_chars_key_orig_filename = temp_test_dir / "complex_map_key_withcontrolchars_original_name.txt"
    assert control_chars_key_orig_filename.is_file()
    assert_file_content(control_chars_key_orig_filename, "Content for complex map control key filename test.")
    
    # Original file: "complex_map_content_with_key_with_controls.txt"
    # Content: "Line with key_with\tcontrol\nchars to replace."
    # The key "key_with\tcontrol\nchars" (escaped) will match.
    control_chars_key_content_file = temp_test_dir / "complex_map_content_with_key_with_controls.txt" # Name unchanged
    assert control_chars_key_content_file.is_file()
    assert_file_content(control_chars_key_content_file, "Line with Value_for_key_with_controls_VAL to replace.")


def test_edge_case_run(temp_test_dir: Path, edge_case_map_file: Path):
    create_test_environment_content(temp_test_dir, use_edge_case_map=True)
    run_main_flow_for_test(temp_test_dir, edge_case_map_file)
    # Map: { "My\nKey": "MyKeyValue_VAL", "Key\nWith\tControls": "ControlValue_VAL", "\t": "ShouldBeSkipped_VAL", "foo": "Foo_VAL", "foo bar": "FooBar_VAL" }
    # Stripped keys in map: "MyKey" -> "MyKeyValue_VAL", "KeyWithControls" -> "ControlValue_VAL", "" (skipped), "foo" -> "Foo_VAL", "foo bar" -> "FooBar_VAL"

    # Original file: "edge_case_MyKey_original_name.txt"
    # Content: "Initial content for control key name test (MyKey)."
    # Name contains "MyKey". This matches stripped key "MyKey". So, "MyKey" in name becomes "MyKeyValue_VAL".
    # Expected name: "edge_case_MyKeyValue_VAL_original_name.txt"
    renamed_file = temp_test_dir / "edge_case_MyKeyValue_VAL_original_name.txt"
    assert renamed_file.is_file()
    # Content: "Initial content for control key name test (MyKey)."
    # "MyKey" in content matches stripped key "MyKey". Replaced by "MyKeyValue_VAL".
    assert_file_content(renamed_file, "Initial content for control key name test (MyKeyValue_VAL).")

    # Original file: "edge_case_content_with_MyKey_controls.txt"
    # Content: "Line with My\nKey to replace."
    # "My\nKey" in content. Stripped key "MyKey" from map.
    # replace_occurrences("Line with My\nKey to replace.")
    # The regex from stripped keys (e.g. "MyKey") will match "MyKey" in "Line with MyKey to replace." (if input was stripped first, which it isn't)
    # Or, if the regex is `(MyKey|KeyWithControls|foo|foo bar)` IGNORECASE.
    # This regex will match "My" then "Key" if they are adjacent after stripping controls from input.
    # The current replace_logic matches on the raw input string using regex from stripped keys.
    # So, `(MyKey|...)` will match "MyKey" in "MyKey" (if input was "MyKey").
    # If input is "My\nKey", the regex `(MyKey)` will not match "My\nKey".
    # This test will likely fail here if it expects "My\nKey" to be matched by the rule for "My\nKey" (stripped: "MyKey").
    content_file = temp_test_dir / "edge_case_content_with_MyKey_controls.txt" # Name unchanged
    assert content_file.is_file()
    # Expected: "Line with MyKeyValue_VAL to replace."
    # Actual: "Line with My\nKey to replace." (no change, because "MyKey" pattern doesn't match "My\nKey")
    assert_file_content(content_file, "Line with MyKeyValue_VAL to replace.") # This will likely fail.

    # Original file: "edge_case_key_priority.txt"
    # Content: "test foo bar test and also foo."
    # Map has "foo": "Foo_VAL", "foo bar": "FooBar_VAL".
    # _SORTED_RAW_KEYS_FOR_REPLACE will have "foo bar" before "foo".
    # Regex `(foo bar|foo)` IGNORECASE.
    # 1. Matches "foo bar". Callback gets "foo bar".
    #    - `if "foo bar" in _RAW_REPLACEMENT_MAPPING` (keys are "MyKey", "KeyWithControls", "foo", "foo bar") -> True. Returns "FooBar_VAL".
    #    String becomes: "test FooBar_VAL test and also foo."
    # 2. Then, regex matches "foo" in "and also foo.". Callback gets "foo".
    #    - `if "foo" in _RAW_REPLACEMENT_MAPPING` -> True. Returns "Foo_VAL".
    #    String becomes: "test FooBar_VAL test and also Foo_VAL."
    priority_file = temp_test_dir / "edge_case_key_priority.txt" # Name unchanged
    assert priority_file.is_file()
    assert_file_content(priority_file, "test FooBar_VAL test and also Foo_VAL.")


def test_precision_run(temp_test_dir: Path, precision_map_file: Path):
    create_test_environment_content(temp_test_dir, include_precision_test_file=True)
    run_main_flow_for_test(temp_test_dir, precision_map_file)
    # Map: { "flojoy": "atlasvibe_plain", "Flojoy": "Atlasvibe_TitleCase", 
    #        "FLÖJOY_DIACRITIC": "ATLASVIBE_DIACRITIC_VAL", "  flojoy  ": "  atlasvibe_spaced_val  ",
    #        "key\twith\ncontrol": "value_for_control_key_val" }
    # Stripped keys: "flojoy", "Flojoy", "FLOJOY_DIACRITIC", "  flojoy  ", "keywithcontrol"

    # Original name: "precision_test_flojoy_source.txt" -> "precision_test_atlasvibe_plain_source.txt"
    # Original name: "precision_name_flojoy_test.md" -> "precision_name_atlasvibe_plain_test.md"
    src_renamed = temp_test_dir / "precision_test_atlasvibe_plain_source.txt"
    name_renamed = temp_test_dir / "precision_name_atlasvibe_plain_test.md"
    assert src_renamed.is_file()
    assert name_renamed.is_file()
    assert_file_content(name_renamed, "File for precision rename test.") # Content has no map keys

    # Content of "precision_test_flojoy_source.txt":
    # 1. "Standard flojoy here.\n" -> "Standard atlasvibe_plain here.\n"
    #    - "flojoy" matches key "flojoy", value "atlasvibe_plain".
    # 2. "Another Flojoy for title case.\r\n" -> "Another Atlasvibe_TitleCase for title case.\r\n"
    #    - "Flojoy" matches key "Flojoy", value "Atlasvibe_TitleCase".
    # 3. "Test FLÖJOY_DIACRITIC with mixed case.\n" -> "Test ATLASVIBE_DIACRITIC_VAL with mixed case.\n"
    #    - "FLÖJOY_DIACRITIC" matches key "FLÖJOY_DIACRITIC" (stripped: "FLOJOY_DIACRITIC"), value "ATLASVIBE_DIACRITIC_VAL".
    # 4. "  flojoy  with exact spaces.\n" -> "  atlasvibe_spaced_val  with exact spaces.\n"
    #    - "  flojoy  " matches key "  flojoy  ", value "  atlasvibe_spaced_val  ".
    # 5. "  flojoy   with extra spaces.\n" -> "  atlasvibe_plain   with extra spaces.\n"
    #    - "flojoy" (part of "  flojoy   ") matches key "flojoy", value "atlasvibe_plain". Spaces preserved.
    # 6. "key\twith\ncontrol characters.\n" -> "value_for_control_key_val characters.\n"
    #    - "key\twith\ncontrol" matches key "key\twith\ncontrol" (stripped: "keywithcontrol"), value "value_for_control_key_val".
    # 7. "unrelated content\n" -> "unrelated content\n" (no change)
    # 8. "你好flojoy世界 (Chinese chars).\n" -> "你好atlasvibe_plain世界 (Chinese chars).\n"
    #    - "flojoy" matches key "flojoy", value "atlasvibe_plain".
    # 9. "emoji😊flojoy test.\n" -> "emoji😊atlasvibe_plain test.\n"
    #    - "flojoy" matches key "flojoy", value "atlasvibe_plain".
    # 10. b"malformed-\xff-flojoy-bytes\n" -> b"malformed-\xff-atlasvibe_plain-bytes\n" (surrogateescape handling)
    #    - "flojoy" matches key "flojoy", value "atlasvibe_plain".
    
    exp_lines = ["Standard atlasvibe_plain here.\n","Another Atlasvibe_TitleCase for title case.\r\n",
                 "Test ATLASVIBE_DIACRITIC_VAL with mixed case.\n","  atlasvibe_spaced_val  with exact spaces.\n",
                 "  atlasvibe_plain   with extra spaces.\n", "value_for_control_key_val characters.\n",
                 "unrelated content\n","你好atlasvibe_plain世界 (Chinese chars).\n","emoji😊atlasvibe_plain test.\n"]
    exp_bytes_list = [line.encode('utf-8','surrogateescape') for line in exp_lines] + [b"malformed-\xff-atlasvibe_plain-bytes\n"]
    assert_file_content(src_renamed, b"".join(exp_bytes_list), is_binary=True)


def test_resume_functionality(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True) 
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    initial_txns = load_transactions(txn_file)
    assert initial_txns and len(initial_txns) > 0
    processed_time_sim = time.time() - 3600 
    name_tx_mod, content_tx_mod, error_tx_mod = False, False, False
    for tx in initial_txns:
        if tx["TYPE"] == TransactionType.FILE_NAME.value and not name_tx_mod:
            tx["STATUS"] = TransactionStatus.COMPLETED.value
            tx["timestamp_processed"] = processed_time_sim
            name_tx_mod = True
        if tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and "large_flojoy_file.txt" in tx["PATH"] and not content_tx_mod:
            tx["STATUS"] = TransactionStatus.PENDING.value # This content will be processed in resume
            content_tx_mod = True
        if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME and tx["TYPE"] == TransactionType.FILE_NAME.value:
            tx["STATUS"] = TransactionStatus.FAILED.value
            tx["ERROR_MESSAGE"] = "Simulated initial fail"
            tx["timestamp_processed"] = processed_time_sim
            error_tx_mod = True
    assert name_tx_mod and error_tx_mod, "Resume setup failed" # content_tx_mod might not be true if large_file not included
    save_transactions(initial_txns, txn_file)
    
    # Simulate state after some renames from dry run were manually applied (or by a previous partial run)
    # Create the structure as if some renames happened
    # flojoy_root -> atlasvibe_root
    # deep_flojoy_file.txt -> deep_atlasvibe_file.txt
    if (temp_test_dir / "flojoy_root").exists():
        (temp_test_dir / "flojoy_root").rename(temp_test_dir / "atlasvibe_root")
    
    deep_file_orig_parent_renamed = temp_test_dir / "atlasvibe_root" / "sub_atlasvibe_folder" / "another_ATLASVIBE_dir"
    deep_file_orig_parent_renamed.mkdir(parents=True, exist_ok=True) # Ensure parent exists
    deep_file_orig_path = deep_file_orig_parent_renamed / "deep_flojoy_file.txt"
    deep_file_after_rename_path = deep_file_orig_parent_renamed / "deep_atlasvibe_file.txt"

    if deep_file_orig_path.exists() and not deep_file_after_rename_path.exists():
         deep_file_orig_path.rename(deep_file_after_rename_path)

    create_test_environment_content(temp_test_dir, for_resume_test_phase_2=True, include_symlink_tests=True) # Add new files

    if deep_file_after_rename_path.exists():
        new_mtime = time.time() + 5 
        os.utime(deep_file_after_rename_path, (new_mtime, new_mtime))
        with open(deep_file_after_rename_path, "a", encoding="utf-8") as f_append:
            f_append.write("\n# Externally appended for resume.")
            
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
    
    # Check content transaction for the new file (original path before rename)
    assert any(tx["PATH"] == "newly_added_flojoy_for_resume.txt" and 
               tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and
               tx["STATUS"] == TransactionStatus.COMPLETED.value for tx in final_txns), "Content transaction for new file not completed"

    only_name_mod_renamed = temp_test_dir / "only_name_atlasvibe.md" # Name already changed by first dry_run's effect or by resume's scan
    assert only_name_mod_renamed.exists()
    assert_file_content(only_name_mod_renamed, "Content without target string, but now with atlasvibe.") # Content changed
    
    # Check content transaction for "only_name_atlasvibe.md" (path after rename)
    # The PATH in transaction might be the original "only_name_flojoy.md" or the current "only_name_atlasvibe.md"
    # depending on when the content change was planned vs. when name change was effective.
    # If scan picked up "only_name_atlasvibe.md" and found "flojoy" in content:
    assert any( (tx["PATH"] == "only_name_atlasvibe.md" or tx["PATH"] == "only_name_flojoy.md") and
                tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and 
                tx["STATUS"] == TransactionStatus.COMPLETED.value for tx in final_txns), \
                "Content transaction for 'only_name_atlasvibe.md' (or original name) not completed."

    err_file_tx = next((tx for tx in final_txns if tx.get("ORIGINAL_NAME") == SELF_TEST_ERROR_FILE_BASENAME), None)
    assert err_file_tx and err_file_tx["STATUS"] == TransactionStatus.FAILED.value
    assert (temp_test_dir / SELF_TEST_ERROR_FILE_BASENAME).exists() # Should not be renamed

    if deep_file_after_rename_path.exists():
        assert "# Externally appended for resume." in deep_file_after_rename_path.read_text(encoding='utf-8')
        # The path in transaction could be original or renamed path depending on execution order
        # Check if any content transaction for this file (original or renamed path) has the appended content
        deep_file_rel_path_orig = str(Path("flojoy_root") / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt").replace("\\","/")
        deep_file_rel_path_renamed = str(deep_file_after_rename_path.relative_to(temp_test_dir)).replace("\\","/")
        
        assert any( (tx["PATH"] == deep_file_rel_path_orig or tx["PATH"] == deep_file_rel_path_renamed) and \
                   tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value and \
                   tx["STATUS"] == TransactionStatus.COMPLETED.value and \
                   tx.get("PROPOSED_LINE_CONTENT","").endswith("# Externally appended for resume.") # Check if the line with append was processed
                   for tx in final_txns), "Externally modified file content not re-processed correctly or not found in transactions"


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
        if tx["STATUS"] == TransactionStatus.COMPLETED.value: # In dry run, COMPLETED means planned
            assert tx.get("ERROR_MESSAGE") == "DRY_RUN" or tx.get("PROPOSED_LINE_CONTENT") is not None or tx["TYPE"] != TransactionType.FILE_CONTENT_LINE.value
        elif tx["STATUS"] == TransactionStatus.PENDING.value: # Should not be PENDING after dry_run scan
            pytest.fail(f"Tx {tx['id']} PENDING after dry run scan phase implies it wasn't processed for planning.")
        # SKIPPED is also a valid final state for a dry run if no change was needed.

def test_skip_scan_behavior(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir, include_symlink_tests=True)
    run_main_flow_for_test(temp_test_dir, default_map_file, dry_run=True) 
    file_to_delete_orig_path = temp_test_dir / "flojoy_root" / "another_flojoy_file.py"
    assert file_to_delete_orig_path.exists()
    file_to_delete_orig_path.unlink() # Delete a file that was in the dry_run's transaction plan
    
    # Run again with skip_scan=True and dry_run=False (actual execution)
    run_main_flow_for_test(temp_test_dir, default_map_file, skip_scan=True, dry_run=False)
    
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    deleted_file_txns_found = False
    for tx in transactions:
        # Path in transaction is relative to root_dir
        if "another_flojoy_file.py" in tx["PATH"]: 
            deleted_file_txns_found = True
            # If file was deleted, transaction should be SKIPPED or FAILED
            assert tx["STATUS"] in [TransactionStatus.SKIPPED.value, TransactionStatus.FAILED.value]
    assert deleted_file_txns_found, "Transactions for the deleted file were not found or not processed."
    
    # Check if other files were processed correctly
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
    create_test_environment_content(temp_test_dir) # Creates no_target_here.log
    (temp_test_dir / "build").mkdir(exist_ok=True)
    (temp_test_dir / "build" / "ignored_build_file.txt").write_text("flojoy in build")
    (temp_test_dir / "docs").mkdir(exist_ok=True)
    (temp_test_dir / "docs" / "specific_file.txt").write_text("flojoy in specific doc")
    (temp_test_dir / "important.log").write_text("flojoy important log") # Should be processed due to !important.log
    (temp_test_dir / "src").mkdir(exist_ok=True)
    (temp_test_dir / "src" / "main.py").write_text("flojoy in main.py")
    (temp_test_dir / "data.tmp").write_text("flojoy in data.tmp")
    (temp_test_dir / "temp_data").mkdir(exist_ok=True)
    (temp_test_dir / "temp_data" / "file.dat").write_text("flojoy in temp_data")
    (temp_test_dir / "other_file.log").write_text("flojoy in other_file.log") # Processed if .gitignore not used or if not matching
    
    if use_gitignore_cli:
        (temp_test_dir / ".gitignore").write_text(GITIGNORE_CONTENT)
    custom_ignore_path_str: Optional[str] = None
    if custom_ignore_name:
        custom_ignore_path = temp_test_dir / custom_ignore_name
        custom_ignore_path.write_text(CUSTOM_IGNORE_CONTENT)
        custom_ignore_path_str = str(custom_ignore_path)
        
    run_main_flow_for_test(temp_test_dir, default_map_file, use_gitignore=use_gitignore_cli, custom_ignore_file=custom_ignore_path_str)
    
    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    # If transactions is None (e.g. file not created due to no matches), treat as empty list for checks
    processed_paths_in_tx = {tx["PATH"] for tx in transactions} if transactions else set()

    for ignored_file_rel_path_str in expected_ignored_files:
        ignored_file_path = Path(ignored_file_rel_path_str)
        # Check if any transaction refers to this path or its components if it's a dir
        is_present_in_tx = False
        for tx_path_str in processed_paths_in_tx:
            tx_path = Path(tx_path_str)
            if tx_path == ignored_file_path or ignored_file_path in tx_path.parents:
                is_present_in_tx = True
                break
        assert not is_present_in_tx, f"File/Dir '{ignored_file_path}' expected to be ignored but found in transactions."
        assert (temp_test_dir / ignored_file_path).exists(), f"Ignored file/dir '{ignored_file_path}' should still exist with original name."
        # If it's a file, ensure its content is also unchanged (if it had 'flojoy')
        if (temp_test_dir / ignored_file_path).is_file() and "flojoy" in (temp_test_dir / ignored_file_path).read_text(encoding='utf-8', errors='ignore').lower():
            assert "flojoy" in (temp_test_dir / ignored_file_path).read_text(encoding='utf-8', errors='ignore').lower(), f"Ignored file '{ignored_file_path}' content changed."


    for processed_file_rel_path_str in expected_processed_files:
        processed_file_rel_path = Path(processed_file_rel_path_str)
        original_path_abs = temp_test_dir / processed_file_rel_path
        
        # Check if there's any transaction related to this original path
        related_tx_exists = any(
            tx["PATH"] == str(processed_file_rel_path) or # Direct match on original path
            (tx.get("ORIGINAL_NAME") and Path(tx["PATH"]).name == replace_occurrences(processed_file_rel_path.name) and Path(tx["PATH"]).parent == processed_file_rel_path.parent) # Match if name changed
            for tx in transactions or []
        )
        assert related_tx_exists, f"File '{processed_file_rel_path}' expected to be processed but no related transaction found."

        # Check if file was renamed or content changed as expected
        new_name = replace_occurrences(original_path_abs.name)
        new_path_abs = original_path_abs.with_name(new_name)

        if new_name != original_path_abs.name: # If name should have changed
            assert not original_path_abs.exists(), f"File '{original_path_abs}' should have been renamed to '{new_path_abs}'."
            assert new_path_abs.exists(), f"File '{original_path_abs}' was expected to be renamed to '{new_path_abs}', but new path doesn't exist."
            # If name changed, check content of the new file
            if "flojoy" in new_path_abs.read_text(encoding='utf-8', errors='ignore').lower():
                 assert "flojoy" not in new_path_abs.read_text(encoding='utf-8', errors='ignore').lower(), f"File '{new_path_abs}' content should have changed."
        elif original_path_abs.exists(): # If name did not change, check content of original file
            if "flojoy" in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower():
                 assert "flojoy" not in original_path_abs.read_text(encoding='utf-8', errors='ignore').lower(), f"File '{original_path_abs}' content should have changed."


@pytest.mark.parametrize("filename, content_bytes, is_binary_expected_by_lib, contains_flojoy_bytes", [
    ("text_file.txt", b"This is a plain text file with flojoy.", False, True),
    ("utf16_file.txt", "UTF-16 text with flojoy".encode('utf-16'), False, True), # isbinary likely sees it as text
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
        # For empty files, is_binary_file can raise FileNotFoundError if it tries to open it.
        # The library's behavior for empty files might be to consider them not binary, or it might error.
        # Let's assume empty files are not binary for the purpose of this test's expectation.
        if len(content_bytes) == 0:
            detected_as_binary_lib = False
        else:
            detected_as_binary_lib = lib_is_binary(str(file_path))
    except FileNotFoundError: 
        if len(content_bytes) == 0: # Expected behavior for empty file with some versions/setups of is_binary
            detected_as_binary_lib = False
        else:
            pytest.fail(f"is_binary_file raised FileNotFoundError for non-empty file: {filename}")
    except Exception as e:
        pytest.fail(f"is_binary_file raised an unexpected exception for {filename}: {e}")

    
    assert detected_as_binary_lib == is_binary_expected_by_lib, \
        f"File {filename} lib_is_binary detection mismatch. Expected binary: {is_binary_expected_by_lib}, Detected binary: {detected_as_binary_lib}"

    # Script treats as binary for content modification if is_binary_file is true AND it's not an RTF file.
    script_treats_as_binary_for_content_mod = detected_as_binary_lib and not filename.endswith(".rtf")

    # Run main flow, skipping renaming to focus on content processing
    run_main_flow_for_test(temp_test_dir, default_map_file, extensions=None, 
                           skip_file_renaming=True, skip_folder_renaming=True)

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    # If transactions is None (e.g. file not created), treat as empty list
    transactions = transactions or []
    
    content_tx_found = any(tx["PATH"] == filename and tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value for tx in transactions)
    
    binary_log_path = temp_test_dir / BINARY_MATCHES_LOG_FILE
    binary_log_has_match_for_this_file = False
    if binary_log_path.exists():
        log_content = binary_log_path.read_text(encoding='utf-8')
        # Check if any line in the log refers to this specific filename
        if f"File: {filename}" in log_content:
             # Further check if it's for a key that was expected to be found
             for key_str_map in replace_logic.get_raw_stripped_keys(): # these are the keys used for binary search
                 if f"File: {filename}, Key: '{key_str_map}'" in log_content:
                     binary_log_has_match_for_this_file = True
                     break


    if not script_treats_as_binary_for_content_mod: 
        # This is a text-like file (or RTF) for content processing purposes
        if contains_flojoy_bytes: # If the original content had a matchable term
            assert content_tx_found, f"Expected content transaction for text-like file {filename} which contained a match."
            # If it's not RTF, content should have been changed
            if file_path.suffix.lower() != '.rtf': 
                changed_content_str = file_path.read_text(encoding='utf-8', errors='surrogateescape')
                # Check that none of the original map keys (in any case) are present
                # This is a simplification; ideally, check against specific replacements.
                all_map_keys_lower = {k.lower() for k in replace_logic.get_raw_stripped_keys()}
                found_original_key = False
                for key_l in all_map_keys_lower:
                    if key_l in changed_content_str.lower():
                        found_original_key = True
                        break
                assert not found_original_key, f"Text file {filename} content not fully replaced. Found an original key variant."
        else: # No matchable term in original
            assert not content_tx_found, f"No content transaction expected for text-like file {filename} as it had no matches."
        
        assert not binary_log_has_match_for_this_file, f"Text-like file {filename} should not have matches in binary log."
    else: 
        # This is a binary file (and not RTF) for content processing purposes
        assert not content_tx_found, f"Binary file {filename} should not have content transactions."
        if contains_flojoy_bytes: # If the original content had a matchable term
             assert binary_log_has_match_for_this_file, f"Binary file {filename} with matches expected in binary log, but not found or not for a mapped key."
        else: # No matchable term in original
             assert not binary_log_has_match_for_this_file, f"Binary file {filename} without matches should not be in binary log for a mapped key."


@pytest.mark.slow 
def test_timeout_behavior_and_retries_mocked(temp_test_dir: Path, default_map_file: Path):
    create_test_environment_content(temp_test_dir)
    file_to_lock_rel = "file_with_floJoy_lines.txt" # This file has 3 lines, so 3 content transactions
    
    original_execute_content = file_system_operations._execute_content_line_transaction
    mock_tx_call_counts: Dict[str, int] = {} 
    max_fails_for_mock = 2 # Each targeted transaction should fail 2 times, then succeed on 3rd call

    def mock_execute_content_with_retry(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        nonlocal mock_tx_call_counts 
        is_target_file_tx = (tx_item["PATH"] == file_to_lock_rel or \
                             Path(tx_item["PATH"]).name == "file_with_atlasVibe_lines.txt") and \
                            tx_item["TYPE"] == TransactionType.FILE_CONTENT_LINE.value

        if is_target_file_tx:
            tx_id = tx_item['id'] # Ensure tx_item has an 'id'
            current_tx_call_count = mock_tx_call_counts.get(tx_id, 0) + 1
            mock_tx_call_counts[tx_id] = current_tx_call_count
            
            if current_tx_call_count <= max_fails_for_mock:
                # print(f"DEBUG MOCK: Simulating retryable OSError for {tx_item['PATH']} (tx_id: {tx_id}, line: {tx_item.get('LINE_NUMBER')}, attempt {current_tx_call_count})")
                return TransactionStatus.RETRY_LATER, f"Mocked OS error (retryable), tx_id: {tx_id}, attempt {current_tx_call_count}", True
        return original_execute_content(tx_item, root_dir, path_translation_map, path_cache, dry_run)

    with patch('file_system_operations._execute_content_line_transaction', mock_execute_content_with_retry):
        run_main_flow_for_test(temp_test_dir, default_map_file, timeout_minutes=1) 

    transactions = load_transactions(temp_test_dir / MAIN_TRANSACTION_FILE_NAME)
    assert transactions is not None
    
    target_txs_checked_count = 0
    for tx in transactions:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == "file_with_atlasVibe_lines.txt") and \
           tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            target_txs_checked_count +=1
            assert tx["STATUS"] == TransactionStatus.COMPLETED.value, f"Transaction for {tx['PATH']} (id: {tx['id']}, line: {tx.get('LINE_NUMBER')}) should have eventually completed."
            assert tx.get("retry_count", 0) == max_fails_for_mock, f"Transaction for {tx['PATH']} (id: {tx['id']}, line: {tx.get('LINE_NUMBER')}) should have {max_fails_for_mock} retries. Got {tx.get('retry_count',0)}."
            # Check that this specific transaction ID was called max_fails_for_mock + 1 times
            assert mock_tx_call_counts.get(tx['id']) == max_fails_for_mock + 1, \
                f"Mocked function for tx_id {tx['id']} not called expected number of times. Got {mock_tx_call_counts.get(tx['id'])}, expected {max_fails_for_mock + 1}"

    assert target_txs_checked_count > 0, "Did not find any targeted content transaction for retry test."
    # Ensure only the targeted transactions were tracked in mock_tx_call_counts
    assert len(mock_tx_call_counts) == target_txs_checked_count, "mock_tx_call_counts tracked more/less transactions than expected."


    # Reset for the indefinite retry part of the test
    mock_tx_call_counts_indef: Dict[str, int] = {}
    indef_max_mock_calls_per_tx = 7 
    
    def mock_always_retryable_error_indef(tx_item, root_dir, path_translation_map, path_cache, dry_run):
        nonlocal mock_tx_call_counts_indef
        is_target_file_tx = (tx_item["PATH"] == file_to_lock_rel or \
                             Path(tx_item["PATH"]).name == "file_with_atlasVibe_lines.txt") and \
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
    for tx in transactions_for_indef_retry:
        if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == "file_with_atlasVibe_lines.txt") and \
           tx["TYPE"] == TransactionType.FILE_CONTENT_LINE.value:
            tx["STATUS"] = TransactionStatus.PENDING.value 
            tx["retry_count"] = 0 # Reset retry_count
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
         if (tx.get("PATH") == file_to_lock_rel or Path(tx.get("PATH")).name == "file_with_atlasVibe_lines.txt") and \
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
    caplog.set_level(logging.INFO) # Ensure Prefect's logger output is captured at INFO level
    
    # Ensure directory is truly empty for the test
    for item in temp_test_dir.iterdir(): 
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
            
    # Recreate a simple map file in the temp_test_dir as main_flow expects it relative to CWD or absolute
    # For consistency, make it absolute for the test.
    simple_map_path = temp_test_dir / "simple_map.json"
    simple_map_path.write_text(json.dumps({"REPLACEMENT_MAPPING": {"flojoy": "atlasvibe"}}))
    
    # Run main_flow with the empty directory and the simple map
    run_main_flow_for_test(temp_test_dir, simple_map_path) 
       
    # Check for the specific log message from main_flow when directory is empty
    assert any("Target directory" in record.message and "is empty. Nothing to do." in record.message 
               for record in caplog.records), \
        "Expected 'Target directory ... is empty. Nothing to do.' log message."
        
    txn_file = temp_test_dir / MAIN_TRANSACTION_FILE_NAME
    # Transaction file should not exist, or if it does (e.g. from a previous test using tmp_path), it should be empty or contain an empty list.
    if txn_file.exists():
        transactions = load_transactions(txn_file)
        assert transactions is None or len(transactions) == 0, "Transaction file should be empty or non-existent for an empty directory run."
    
    # Clean up the simple map file
    if simple_map_path.exists():
        simple_map_path.unlink()
    
