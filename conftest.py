# tests/conftest.py
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `create_test_environment_content`:
#   - Corrected deep path creation to be under `flojoy_root`.
#   - For `use_complex_map`:
#     - Changed `diacritic_test_folder_ȕsele̮Ss_diá͡cRiti̅cS` to `ȕsele̮Ss_diá͡cRiti̅cS_folder` to test replacement of the key part.
#     - Changed `file_with_diacritics_ȕsele̮Ss_diá͡cRiti̅cS.txt` to `ȕsele̮Ss_diá͡cRiti̅cS_file.txt`.
#     - Changed `file_with_spaces_The spaces will not be ignored.md` to `The spaces will not be ignored_file.md`.
#   - These changes aim to create file/folder names that directly contain the (unstripped) keys from the complex map,
#     allowing `replace_logic.py` (after its fix) to match and replace them.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
import shutil
import json
from pathlib import Path
import os
from typing import Union, Optional

SELF_TEST_ERROR_FILE_BASENAME = "error_file_flojoy.txt"
VERY_LARGE_FILE_NAME_ORIG = "very_large_flojoy_file.txt"
VERY_LARGE_FILE_NAME_REPLACED = "very_large_flojoy_file_replaced.txt" # Note: This name might be further changed by tests
VERY_LARGE_FILE_LINES = 10000
VERY_LARGE_FILE_MATCH_INTERVAL = 500

def create_test_environment_content(
    base_dir: Path,
    use_complex_map: bool = False,
    use_edge_case_map: bool = False,
    for_resume_test_phase_2: bool = False,
    include_very_large_file: bool = False,
    include_precision_test_file: bool = False,
    include_symlink_tests: bool = False
):
    flojoy_root_dir = base_dir / "flojoy_root"

    if not for_resume_test_phase_2:
        (flojoy_root_dir / "sub_flojoy_folder" / "another_FLOJOY_dir").mkdir(parents=True, exist_ok=True)
        (flojoy_root_dir / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt").write_text(
            "Line 1: flojoy content.\nLine 2: More Flojoy here.\nLine 3: No target.\nLine 4: FLOJOY project."
        )
        (flojoy_root_dir / "another_flojoy_file.py").write_text("import flojoy_lib\n# class MyFlojoyClass: pass")
        
        deep_path_parts = ["depth1_flojoy","depth2","depth3_flojoy","depth4","depth5","depth6_flojoy","depth7","depth8","depth9_flojoy","depth10_file_flojoy.txt"]
        current_path = flojoy_root_dir 
        for i, part in enumerate(deep_path_parts):
            current_path /= part
            if i < len(deep_path_parts) - 1: current_path.mkdir(parents=True, exist_ok=True)
            else: current_path.write_text("flojoy deep content")

        (base_dir / "only_name_flojoy.md").write_text("Content without target string.")
        (base_dir / "file_with_floJoy_lines.txt").write_text("First floJoy.\nSecond FloJoy.\nflojoy and FLOJOY on same line.")
        (base_dir / "unmapped_variant_flojoy_content.txt").write_text("This has fLoJoY content, and also flojoy.")
        (base_dir / "binary_flojoy_file.bin").write_bytes(b"prefix_flojoy_suffix" + b"\x00\x01\x02flojoy_data\x03\x04")
        (base_dir / "binary_fLoJoY_name.bin").write_bytes(b"unmapped_variant_binary_content" + b"\x00\xff")
        (base_dir / "excluded_flojoy_dir").mkdir(exist_ok=True)
        (base_dir / "excluded_flojoy_dir" / "inner_flojoy_file.txt").write_text("flojoy inside excluded dir")
        (base_dir / "exclude_this_flojoy_file.txt").write_text("flojoy content in explicitly excluded file")
        (base_dir / "no_target_here.log").write_text("This is a log file without the target string.")
        
        try: (base_dir / "gb18030_flojoy_file.txt").write_text("你好 flojoy 世界", encoding="gb18030")
        except Exception: (base_dir / "gb18030_flojoy_file.txt").write_text("fallback flojoy content")
        
        large_lines = [f"This flojoy line should be replaced {i}\n" if i % 50 == 0 else f"Normal line {i}\n" for i in range(1000)]
        (base_dir / "large_flojoy_file.txt").write_text("".join(large_lines), encoding='utf-8')
        (base_dir / SELF_TEST_ERROR_FILE_BASENAME).write_text("This file will cause a rename error during tests.")

    if include_very_large_file:
        with open(base_dir / VERY_LARGE_FILE_NAME_ORIG, 'w', encoding='utf-8') as f:
            for i in range(VERY_LARGE_FILE_LINES):
                is_match_line = (i == 0 or i == VERY_LARGE_FILE_LINES // 2 or i == VERY_LARGE_FILE_LINES - 1 or
                                 (i % VERY_LARGE_FILE_MATCH_INTERVAL == 0 and i != 0 and i != VERY_LARGE_FILE_LINES // 2 and i != VERY_LARGE_FILE_LINES -1) )
                f.write(f"Line {i+1}: This is a {'flojoy line that should be replaced' if is_match_line else 'standard non-matching line'}.\n")
        # VERY_LARGE_FILE_NAME_REPLACED is just a placeholder for tests to know what the *original* name of the replaced file was.
        # The actual replaced name will depend on the map.
        # We create it here mostly for size comparison or if a test needs to verify its *original* content before replacement.
        # For this test suite, it's more about having a large file that *gets* replaced.
        # So, we might not need to write to VERY_LARGE_FILE_NAME_REPLACED here.
        # However, if a test specifically checks this name, it's kept.
        # For now, let's assume it's for tracking the original name of the file that will be replaced.
        # If tests need a pre-replaced version, that's a different setup.
        # The current tests seem to imply VERY_LARGE_FILE_NAME_ORIG is the one processed.

    if include_precision_test_file:
        lines = ["Standard flojoy here.\n", "Another Flojoy for title case.\r\n", "Test FLÖJOY_DIACRITIC with mixed case.\n",
                   "  flojoy  with exact spaces.\n", "  flojoy   with extra spaces.\n", "key\twith\ncontrol characters.\n",
                   "unrelated content\n", "你好flojoy世界 (Chinese chars).\n", "emoji😊flojoy test.\n"]
        with open(base_dir / "precision_test_flojoy_source.txt", "wb") as f:
            for line_str in lines: f.write(line_str.encode('utf-8', errors='surrogateescape'))
            f.write(b"malformed-\xff-flojoy-bytes\n")
        (base_dir / "precision_name_flojoy_test.md").write_text("File for precision rename test.")

    if use_complex_map:
        complex_diacritic_folder = base_dir / "ȕsele̮Ss_diá͡cRiti̅cS_folder"
        complex_diacritic_folder.mkdir(parents=True,exist_ok=True)
        (complex_diacritic_folder/"ȕsele̮Ss_diá͡cRiti̅cS_file.txt").write_text(
            "Content with ȕsele̮Ss_diá͡cRiti̅cS and also useless_diacritics.\nAnd another Flojoy for good measure.")
        
        (base_dir/"The spaces will not be ignored_file.md").write_text(
            "This file has The spaces will not be ignored in its name and content.")
        
        (base_dir/"_My_Love&Story.log").write_text("Log for _My_Love&Story and _my_love&story. And My_Love&Story.")
        (base_dir/"filename_with_COCO4_ep-m.data").write_text("Data for COCO4_ep-m and Coco4_ep-M. Also coco4_ep-m.")
        (base_dir/"special_chars_in_content_test.txt").write_text("This line contains characters|not<allowed^in*paths::will/be!escaped%when?searched~in$filenames@and\"foldernames to be replaced.")
        (base_dir/"complex_map_key_withcontrolchars_original_name.txt").write_text("Content for complex map control key filename test.")
        (base_dir/"complex_map_content_with_key_with_controls.txt").write_text("Line with key_with\tcontrol\nchars to replace.")

    if use_edge_case_map:
        (base_dir/"edge_case_MyKey_original_name.txt").write_text("Initial content for control key name test (MyKey).")
        (base_dir/"edge_case_content_with_MyKey_controls.txt").write_text("Line with My\nKey to replace.")
        (base_dir/"edge_case_empty_stripped_key_target.txt").write_text("This should not be changed by an empty key.")
        (base_dir/"edge_case_key_priority.txt").write_text("test foo bar test and also foo.")

    if for_resume_test_phase_2:
        (base_dir/"newly_added_flojoy_for_resume.txt").write_text("This flojoy content is new for resume.")
        # This part of the original conftest was problematic:
        # renamed_only_name_file = base_dir / "only_name_atlasvibe.md"
        # if renamed_only_name_file.exists(): renamed_only_name_file.write_text("Content without target string, but now with flojoy.")
        # Instead, ensure the *original* file "only_name_flojoy.md" exists if it's expected to be processed by resume.
        # If the test intends to modify a file that *would have been renamed*, it should modify the original.
        # The test_resume_functionality will handle the state of "only_name_flojoy.md".

    if include_symlink_tests:
        symlink_target_dir = base_dir / "symlink_targets_outside"; symlink_target_dir.mkdir(parents=True, exist_ok=True)
        target_file_abs = symlink_target_dir / "target_file_flojoy.txt"
        target_file_abs.write_text("flojoy in symlink target file")
        target_subdir_abs = symlink_target_dir / "target_dir_flojoy"; target_subdir_abs.mkdir(exist_ok=True)
        (target_subdir_abs / "another_flojoy_file.txt").write_text("flojoy content in symlinked dir target")
        link_file_path = base_dir / "link_to_file_flojoy.txt"
        link_dir_path = base_dir / "link_to_dir_flojoy"
        try:
            if not os.path.lexists(link_file_path): os.symlink(target_file_abs, link_file_path, target_is_directory=False)
            if not os.path.lexists(link_dir_path): os.symlink(target_subdir_abs, link_dir_path, target_is_directory=True)
        except OSError as e: print(f"Warning: Symlink creation failed (OSError: {e}).")
        except Exception as e: print(f"Warning: Symlink creation failed (Error: {e}).")

@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    test_dir = tmp_path / "test_run"; test_dir.mkdir(); return test_dir

@pytest.fixture
def default_map_file(temp_test_dir: Path) -> Path:
    map_data = {"REPLACEMENT_MAPPING": {"flojoy": "atlasvibe", "Flojoy": "Atlasvibe", "floJoy": "atlasVibe", "FloJoy": "AtlasVibe", "FLOJOY": "ATLASVIBE"}}
    map_path = temp_test_dir / "default_mapping.json"; map_path.write_text(json.dumps(map_data, indent=2)); return map_path

@pytest.fixture
def complex_map_file(temp_test_dir: Path) -> Path:
    map_data = {"REPLACEMENT_MAPPING": { "ȕsele̮Ss_diá͡cRiti̅cS": "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL", "The spaces will not be ignored": "The control characters \n will be ignored_VAL", "key_with\tcontrol\nchars": "Value_for_key_with_controls_VAL", "_My_Love&Story": "_My_Story&Love_VAL", "_my_love&story": "_my_story&love_VAL", "COCO4_ep-m": "MOCO4_ip-N_VAL", "Coco4_ep-M": "Moco4_ip-N_VAL", "characters|not<allowed^in*paths::will\\/be!escaped%when?searched~in$filenames@and\"foldernames": "SpecialCharsKeyMatched_VAL" }}
    map_path = temp_test_dir / "complex_mapping.json"; map_path.write_text(json.dumps(map_data, indent=2)); return map_path

@pytest.fixture
def edge_case_map_file(temp_test_dir: Path) -> Path:
    map_data = {"REPLACEMENT_MAPPING": { "My\nKey": "MyKeyValue_VAL", "Key\nWith\tControls": "ControlValue_VAL", "\t": "ShouldBeSkipped_VAL", "foo": "Foo_VAL", "foo bar": "FooBar_VAL" }}
    map_path = temp_test_dir / "edge_case_mapping.json"; map_path.write_text(json.dumps(map_data, indent=2)); return map_path

@pytest.fixture
def empty_map_file(temp_test_dir: Path) -> Path:
    map_data = {"REPLACEMENT_MAPPING": {}}
    map_path = temp_test_dir / "empty_mapping.json"; map_path.write_text(json.dumps(map_data, indent=2)); return map_path

@pytest.fixture
def precision_map_file(temp_test_dir: Path) -> Path:
    map_data = {"REPLACEMENT_MAPPING": { "flojoy": "atlasvibe_plain", "Flojoy": "Atlasvibe_TitleCase", "FLÖJOY_DIACRITIC": "ATLASVIBE_DIACRITIC_VAL", "  flojoy  ": "  atlasvibe_spaced_val  ", "key\twith\ncontrol": "value_for_control_key_val" }}
    map_path = temp_test_dir / "precision_mapping.json"; map_path.write_text(json.dumps(map_data, indent=2)); return map_path

def assert_file_content( file_path: Path, expected_content: Union[str, bytes], encoding: Optional[str] = 'utf-8', is_binary: bool = False ):
    assert file_path.exists(), f"File missing: {file_path}"
    try:
        if is_binary:
            actual = file_path.read_bytes(); expected = expected_content if isinstance(expected_content, bytes) else str(expected_content).encode(encoding or 'utf-8')
            assert actual == expected, f"Binary mismatch for {file_path}.\nGot: {actual[:100]!r}\nExp: {expected[:100]!r}"
        else:
            actual = file_path.read_text(encoding=encoding, errors='surrogateescape')
            expected_norm = str(expected_content).replace("\r\n", "\n").replace("\r", "\n")
            actual_norm = actual.replace("\r\n", "\n").replace("\r", "\n")
            assert actual_norm == expected_norm, f"Content mismatch for {file_path}.\nExp:\n{expected_norm!r}\nGot:\n{actual_norm!r}"
    except Exception as e: pytest.fail(f"Error reading/comparing {file_path}: {e}")
