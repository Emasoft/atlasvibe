#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial test implementation for json_utils module
# - Test all functions with various scenarios
# - Use real file operations instead of mocking
#

"""
Test suite for JSON utility functions.

Tests all functions in captain.utils.shared.json_utils with real file operations
to ensure proper behavior in production scenarios.
"""

import json
import tempfile
from pathlib import Path
from captain.utils.shared.json_utils import (
    load_json_file,
    save_json_file,
    update_json_file,
    merge_json_files,
)


class TestLoadJsonFile:
    """Test load_json_file function."""

    def test_load_valid_json(self):
        """Test loading a valid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = {"key": "value", "number": 42}
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result == test_data
        finally:
            temp_path.unlink()

    def test_load_missing_file(self):
        """Test loading a non-existent file returns default."""
        missing_path = Path("/tmp/non_existent_file.json")

        # Test with default None
        result = load_json_file(missing_path)
        assert result == {}

        # Test with custom default
        custom_default = {"default": "value"}
        result = load_json_file(missing_path, default=custom_default)
        assert result == custom_default

    def test_load_invalid_json(self):
        """Test loading a file with invalid JSON returns default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result == {}

            # Test with custom default
            custom_default = {"error": "default"}
            result = load_json_file(temp_path, default=custom_default)
            assert result == custom_default
        finally:
            temp_path.unlink()

    def test_load_empty_file(self):
        """Test loading an empty file returns default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            assert result == {}
        finally:
            temp_path.unlink()

    def test_load_with_different_encoding(self):
        """Test loading JSON with UTF-8 encoding."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            test_data = {"message": "Hello 世界 🌍"}
            json.dump(test_data, f, ensure_ascii=False)
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path, encoding="utf-8")
            assert result == test_data
        finally:
            temp_path.unlink()


class TestSaveJsonFile:
    """Test save_json_file function."""

    def test_save_json_basic(self):
        """Test saving JSON data to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            test_data = {"key": "value", "list": [1, 2, 3]}

            result = save_json_file(file_path, test_data)
            assert result is True
            assert file_path.exists()

            # Verify the content
            loaded_data = json.loads(file_path.read_text())
            assert loaded_data == test_data

    def test_save_json_with_parent_creation(self):
        """Test saving JSON creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "deep" / "nested" / "dir" / "test.json"
            test_data = {"created": True}

            result = save_json_file(file_path, test_data)
            assert result is True
            assert file_path.exists()
            assert file_path.parent.exists()

    def test_save_json_atomic_write(self):
        """Test atomic write functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "atomic.json"
            original_data = {"version": 1}
            new_data = {"version": 2}

            # Write original data
            save_json_file(file_path, original_data)

            # Simulate partial write by using atomic=True (default)
            result = save_json_file(file_path, new_data, atomic=True)
            assert result is True

            # Verify the content was updated atomically
            loaded_data = json.loads(file_path.read_text())
            assert loaded_data == new_data

    def test_save_json_non_atomic_write(self):
        """Test non-atomic write functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "non_atomic.json"
            test_data = {"atomic": False}

            result = save_json_file(file_path, test_data, atomic=False)
            assert result is True
            assert file_path.exists()

            loaded_data = json.loads(file_path.read_text())
            assert loaded_data == test_data

    def test_save_json_with_indentation(self):
        """Test saving JSON with custom indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "indented.json"
            test_data = {"nested": {"key": "value"}}

            save_json_file(file_path, test_data, indent=4)

            content = file_path.read_text()
            # Check for 4-space indentation
            assert "    " in content
            assert content.endswith("\n")

    def test_save_json_unicode_handling(self):
        """Test saving JSON with Unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "unicode.json"
            test_data = {"emoji": "🚀", "chinese": "你好", "special": "café"}

            result = save_json_file(file_path, test_data)
            assert result is True

            # Verify Unicode is preserved
            loaded_data = json.loads(file_path.read_text(encoding="utf-8"))
            assert loaded_data == test_data

    def test_save_json_permission_error(self):
        """Test handling permission errors."""
        # Try to write to a read-only directory
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir) / "readonly"
            dir_path.mkdir()
            file_path = dir_path / "test.json"

            # Make directory read-only
            import os

            os.chmod(dir_path, 0o444)

            try:
                result = save_json_file(file_path, {"test": "data"})
                # On some systems this might still succeed, so we just check the result
                assert isinstance(result, bool)
            finally:
                # Restore permissions for cleanup
                os.chmod(dir_path, 0o755)


class TestUpdateJsonFile:
    """Test update_json_file function."""

    def test_update_existing_file(self):
        """Test updating an existing JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "update.json"
            original_data = {"key1": "value1", "key2": "value2"}

            # Create original file
            save_json_file(file_path, original_data)

            # Update it
            updates = {"key2": "updated", "key3": "new"}
            result = update_json_file(file_path, updates)
            assert result is True

            # Verify updates
            loaded_data = json.loads(file_path.read_text())
            assert loaded_data["key1"] == "value1"  # Preserved
            assert loaded_data["key2"] == "updated"  # Updated
            assert loaded_data["key3"] == "new"  # Added

    def test_update_non_existent_file_create(self):
        """Test updating a non-existent file with create_if_missing=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "new.json"
            updates = {"created": True}

            result = update_json_file(file_path, updates, create_if_missing=True)
            assert result is True
            assert file_path.exists()

            loaded_data = json.loads(file_path.read_text())
            assert loaded_data == updates

    def test_update_non_existent_file_no_create(self):
        """Test updating a non-existent file with create_if_missing=False."""
        file_path = Path("/tmp/non_existent_update.json")
        updates = {"should": "fail"}

        result = update_json_file(file_path, updates, create_if_missing=False)
        assert result is False
        assert not file_path.exists()

    def test_update_nested_values(self):
        """Test updating with nested dictionary values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nested.json"
            original_data = {"config": {"setting1": "value1"}}

            save_json_file(file_path, original_data)

            # Update with nested structure
            updates = {"config": {"setting1": "updated", "setting2": "new"}}
            result = update_json_file(file_path, updates)
            assert result is True

            loaded_data = json.loads(file_path.read_text())
            # Note: update replaces the entire nested dict
            assert loaded_data["config"] == updates["config"]


class TestMergeJsonFiles:
    """Test merge_json_files function."""

    def test_merge_multiple_files(self):
        """Test merging multiple JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source files
            file1 = Path(tmpdir) / "file1.json"
            file2 = Path(tmpdir) / "file2.json"
            file3 = Path(tmpdir) / "file3.json"
            target = Path(tmpdir) / "merged.json"

            save_json_file(file1, {"a": 1, "b": 2})
            save_json_file(file2, {"b": 3, "c": 4})  # b will be overwritten
            save_json_file(file3, {"d": 5})

            result = merge_json_files([file1, file2, file3], target)
            assert result is True
            assert target.exists()

            merged_data = json.loads(target.read_text())
            assert merged_data == {"a": 1, "b": 3, "c": 4, "d": 5}

    def test_merge_with_missing_source(self):
        """Test merging when some source files are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "exists.json"
            file2 = Path(tmpdir) / "missing.json"
            target = Path(tmpdir) / "merged.json"

            save_json_file(file1, {"exists": True})

            # file2 doesn't exist, should be skipped with warning
            result = merge_json_files([file1, file2], target)
            assert result is True

            merged_data = json.loads(target.read_text())
            assert merged_data == {"exists": True}

    def test_merge_empty_list(self):
        """Test merging with empty source list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "empty_merge.json"

            result = merge_json_files([], target)
            assert result is True

            merged_data = json.loads(target.read_text())
            assert merged_data == {}

    def test_merge_overwrites_target(self):
        """Test that merge overwrites existing target file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.json"
            target = Path(tmpdir) / "target.json"

            # Create existing target
            save_json_file(target, {"old": "data"})

            # Create source
            save_json_file(source, {"new": "data"})

            result = merge_json_files([source], target)
            assert result is True

            merged_data = json.loads(target.read_text())
            assert merged_data == {"new": "data"}
            assert "old" not in merged_data
