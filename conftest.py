# conftest.py
import pytest
import json
from pathlib import Path
import os

@pytest.fixture
def temp_test_dir(tmp_path: Path):
    """Fixture that creates separate config and runtime directories for testing.
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
    
    return { 
        "runtime": runtime_dir, 
        "config": config_dir
    }  # End of fixture
