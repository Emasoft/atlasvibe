# conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def create_test_environment_content():
    """Fixture to create a standardized test directory structure with files."""
    def _create(tmp_path: Path):
        test_dir = tmp_path / "test_run"
        test_dir.mkdir()
        
        # Create sample directories
        (test_dir / "flojoy_root").mkdir()
        (test_dir / "flojoy_root" / "sub_flojoy_folder").mkdir()
        (test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir").mkdir()
        deep_file = test_dir / "flojoy_root" / "sub_flojoy_folder" / "another_FLOJOY_dir" / "deep_flojoy_file.txt"
        deep_file.write_text("This file contains FLOJOY multiple times: Flojoy floJoy")
        
        # Create excluded items
        (test_dir / "excluded_flojoy_dir").mkdir()
        (test_dir / "excluded_flojoy_dir" / "excluded_file.txt").write_text("FLOJOY content")
        (test_dir / "exclude_this_flojoy_file.txt").write_text("Flojoy exclusion test")
        
        # Create symlink tests if needed
        include_symlink_tests = False
        if include_symlink_tests:
            symlink_target = test_dir / "symlink_targets_outside"
            symlink_target.mkdir()
            (symlink_target / "external_flojoy.txt").write_text("External FLOJOY")
            (test_dir / "symlink_to_external").symlink_to(symlink_target / "external_flojoy.txt")
        return test_dir
    return _create
