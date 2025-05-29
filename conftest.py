# conftest.py
import pytest
import json
from pathlib import Path
import os

@pytest.fixture
def temp_test_dir(tmp_path: Path):
    """Fixture that creates a full test directory structure"""
    test_dir = tmp_path / "test_run"
    test_dir.mkdir()
    
    # Create sample directories and files
    (test_dir / "flojoy_root").mkdir()
    (test_dir / "flojoy_root" / "sub_flojoy_folder").mkdir()
    (test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir").mkdir()
    deep_file = test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
    deep_file.write_text("This file contains FLOJOY multiple times: Flojoy floJoy")
    
    # Create excluded items
    (test_dir / "excluded_flojoy_dir").mkdir()
    (test_dir / "excluded_flojoy_dir" / "excluded_file.txt").write_text("FLOJOY content")
    (test_dir / "exclude_this_flojoy_file.txt").write_text("Flojoy exclusion test")
    
    return test_dir

@pytest.fixture
def default_map_file(temp_test_dir: Path):
    """Fixture that creates a default replacement mapping file"""
    map_file = temp_test_dir / "replacement_mapping.json"
    map_content = {
        "REPLACEMENT_MAPPING": {
            "flojoy": "atlasvibe",
            "Flojoy": "Atlasvibe",
            "floJoy": "atlasVibe",
            "FloJoy": "AtlasVibe",
            "FLOJOY": "ATLASVIBE"
        }
    }
    map_file.write_text(json.dumps(map_content))
    return map_file

@pytest.fixture
def assert_file_content():
    """Helper fixture to assert file content matches expected string"""
    def _assert(file_path: Path, expected_content: str):
        content = file_path.read_text(encoding='utf-8')
        assert content == expected_content
    return _assert

@pytest.fixture(scope="session", autouse=True)
def prefect_server_cleanup():
    """Cleanup Prefect server after all tests finish"""
    yield
    import psutil
    from prefect import get_client
    
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if "prefect" in proc.name().lower() and current_pid != proc.ppid():
                proc.terminate()
        except psutil.NoSuchProcess:
            continue
    
    try:
        get_client()._cache.clear()
    except Exception:
        pass
