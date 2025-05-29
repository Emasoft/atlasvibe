# conftest.py
import pytest
from pathlib import Path
import json
import os
import shutil

@pytest.fixture
def temp_test_dir(tmp_path: Path):
    """Fixture that creates separate config and runtime directories for testing.
    Verify that the directory structure is correct. 
    Ensures virtual directory tree for consistent transaction counts"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    
    # Create sample directories and files in runtime directory
    (runtime_dir / "flojoy_root").mkdir()
    (runtime_dir / "flojoy_root" / "sub_flojoy_folder").mkdir()
    (runtime_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir").mkdir()
    deep_file = runtime_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    deep_file.write_text("This file contains FLOJOY multiple times: Flojoy floJoy")
    
    # Create excluded items in runtime directory
    (runtime_dir / "excluded_flojoy_dir").mkdir()
    (runtime_dir / "excluded_flojoy_dir" / "excluded_file.txt").write_text("FLOJOY content")
    (runtime_dir / "exclude_this_flojoy_file.txt").write_text("Flojoy exclusion test")
    
    # Verify structure
    assert (runtime_dir / "flojoy_root").exists(), "Required dir not created in fixture"
    context = {
        "runtime": runtime_dir,
        "config": config_dir
    }
    yield context
    # Cleanup
    shutil.rmtree(tmp_path)

@pytest.fixture
def default_map_file(temp_test_dir: dict) -> Path:
    """
    Create the default replacement mapping file in config directory.
    """
    config_dir = temp_test_dir["config"]
    map_file = config_dir / "replacement_mapping.json"
    
    # Create and populate replacement mapping file
    map_data = {
        "REPLACEMENT_MAPPING": {
            "flojoy": "atlasvibe",
            "Flojoy": "Atlasvibe",
            "floJoy": "atlasVibe",
            "FloJoy": "AtlasVibe",
            "FLOJOY": "ATLASVIBE"
        }
    }
    map_file.write_text(json.dumps(map_data, ensure_ascii=False, indent=2), encoding='utf-8')
    return map_file

@pytest.fixture
def assert_file_content():
    def _assert(file_path: Path, expected_content: str):
        """Helper to validate file content with readable diffs"""
        actual = file_path.read_text(encoding='utf-8')
        assert actual == expected_content, f"Content mismatch in {file_path}: Expected {expected_content!r}, got {actual!r}"
    
    return _assert
