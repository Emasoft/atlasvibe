# conftest.py
import pytest
import json
from pathlib import Path
import os

@pytest.fixture
def temp_test_dir(tmp_path: Path):
    """Fixture that creates separate config and runtime directories for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    
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
    
    return { 
        "runtime": runtime_dir, 
        "config": config_dir
    }

@pytest.fixture
def default_map_file(temp_test_dir):
    """Fixture that creates a default replacement mapping file in config directory."""
    map_file = temp_test_dir["config"] / "replacement_mapping.json"
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
    try:
        # Clean file locks from Prefect
        from prefect.utilities.filesystem import remove_fs_lock
        import atexit
        atexit.register(remove_fs_lock)
    except ImportError:
        pass
    try:
        # Clean any temporary files
        base_path = Path(__file__).parent
        for path in base_path.glob('**/planned_transactions.json'):
            if path.parent.name != 'runtime':
                continue
            for backup in path.glob('*.bak'):
                backup.unlink(missing_ok=True)
    except Exception:
        pass
