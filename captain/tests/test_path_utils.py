#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial test implementation for path_utils module
# - Test all path manipulation functions
# - Use real file system operations for accurate testing
#

"""
Test suite for path utility functions.

Tests all functions in captain.utils.shared.path_utils with real file operations
to ensure proper path handling across different platforms.
"""

import tempfile
from pathlib import Path
import pytest
from captain.utils.shared.path_utils import (
    get_block_python_file,
    get_block_metadata_file,
    get_block_app_file,
    get_block_example_file,
    get_block_test_file,
    get_block_venv_dir,
    find_project_root,
    ensure_directory_exists,
    safe_path_join,
    get_relative_path,
    find_files_by_pattern,
    is_valid_block_directory,
)


class TestBlockPathGetters:
    """Test block-specific path getter functions."""

    def test_get_block_python_file(self):
        """Test getting Python file path for a block."""
        block_dir = Path("/path/to/blocks/MY_BLOCK")
        result = get_block_python_file(block_dir)
        assert result == block_dir / "MY_BLOCK.py"

        # Test with string input
        result = get_block_python_file("/path/to/blocks/ANOTHER_BLOCK")
        assert result == Path("/path/to/blocks/ANOTHER_BLOCK/ANOTHER_BLOCK.py")

    def test_get_block_metadata_file(self):
        """Test getting metadata file path for a block."""
        block_dir = Path("/path/to/blocks/MY_BLOCK")
        result = get_block_metadata_file(block_dir)
        assert result == block_dir / "block_data.json"

    def test_get_block_app_file(self):
        """Test getting app.json file path for a block."""
        block_dir = Path("/path/to/blocks/MY_BLOCK")
        result = get_block_app_file(block_dir)
        assert result == block_dir / "app.json"

    def test_get_block_example_file(self):
        """Test getting example.md file path for a block."""
        block_dir = Path("/path/to/blocks/MY_BLOCK")
        result = get_block_example_file(block_dir)
        assert result == block_dir / "example.md"

    def test_get_block_test_file(self):
        """Test getting test file path for a block."""
        block_dir = Path("/path/to/blocks/MY_BLOCK")
        result = get_block_test_file(block_dir)
        assert result == block_dir / "MY_BLOCK_test_.py"

        # Test with different block name
        block_dir = Path("/custom/path/CUSTOM_BLOCK")
        result = get_block_test_file(block_dir)
        assert result == block_dir / "CUSTOM_BLOCK_test_.py"

    def test_get_block_venv_dir(self):
        """Test getting virtual environment directory for a block."""
        block_dir = Path("/path/to/blocks/MY_BLOCK")
        result = get_block_venv_dir(block_dir)
        assert result == block_dir / ".venv"


class TestFindProjectRoot:
    """Test find_project_root function."""

    def test_find_project_root_with_pyproject(self):
        """Test finding project root with pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            project_root = Path(tmpdir) / "myproject"
            project_root.mkdir()
            (project_root / "pyproject.toml").touch()

            subdir = project_root / "src" / "submodule"
            subdir.mkdir(parents=True)

            # Find from subdir
            result = find_project_root(subdir)
            assert result == project_root.resolve()

            # Find from project root itself
            result = find_project_root(project_root)
            assert result == project_root.resolve()

    def test_find_project_root_no_pyproject(self):
        """Test finding project root when no pyproject.toml exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "some" / "deep" / "path"
            subdir.mkdir(parents=True)

            result = find_project_root(subdir)
            assert result is None

    def test_find_project_root_from_current_dir(self):
        """Test finding project root from current directory."""
        # Save current directory
        import os

        original_cwd = os.getcwd()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                project_dir = Path(tmpdir)
                (project_dir / "pyproject.toml").touch()

                # Change to project directory
                os.chdir(project_dir)

                # Test with no argument (uses cwd)
                result = find_project_root()
                assert result == project_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_find_project_root_multiple_levels(self):
        """Test finding project root from deeply nested directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure with pyproject.toml at different levels
            root = Path(tmpdir)
            project1 = root / "project1"
            project1.mkdir()
            (project1 / "pyproject.toml").touch()

            nested_project = project1 / "subproject"
            nested_project.mkdir()
            (nested_project / "pyproject.toml").touch()

            deep_dir = nested_project / "src" / "module"
            deep_dir.mkdir(parents=True)

            # Should find the nearest pyproject.toml
            result = find_project_root(deep_dir)
            assert result == nested_project.resolve()


class TestEnsureDirectoryExists:
    """Test ensure_directory_exists function."""

    def test_create_new_directory(self):
        """Test creating a new directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_directory"

            result = ensure_directory_exists(new_dir)
            assert result == new_dir
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_create_nested_directories(self):
        """Test creating nested directories with parents=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "level1" / "level2" / "level3"

            result = ensure_directory_exists(nested_dir, parents=True)
            assert result == nested_dir
            assert nested_dir.exists()
            assert nested_dir.is_dir()

    def test_existing_directory(self):
        """Test that existing directory is handled properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_dir = Path(tmpdir) / "existing"
            existing_dir.mkdir()

            # Should not raise error with exist_ok=True (default)
            result = ensure_directory_exists(existing_dir)
            assert result == existing_dir

    def test_create_without_parents(self):
        """Test creating directory without parents fails appropriately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "missing_parent" / "child"

            # Should raise error when parent doesn't exist and parents=False
            with pytest.raises(FileNotFoundError):
                ensure_directory_exists(nested_dir, parents=False)


class TestSafePathJoin:
    """Test safe_path_join function."""

    def test_join_basic_paths(self):
        """Test joining basic path components."""
        result = safe_path_join("path", "to", "file.txt")
        assert result == Path("path/to/file.txt")

    def test_join_with_path_objects(self):
        """Test joining Path objects."""
        base = Path("/home/user")
        result = safe_path_join(base, "documents", "file.txt")
        assert result == Path("/home/user/documents/file.txt")

    def test_join_mixed_types(self):
        """Test joining mixed strings and Path objects."""
        result = safe_path_join(Path("/root"), "folder", Path("subfolder"), "file.txt")
        assert result == Path("/root/folder/subfolder/file.txt")

    def test_join_empty_parts(self):
        """Test joining with no arguments returns empty Path."""
        result = safe_path_join()
        assert result == Path()

    def test_join_single_part(self):
        """Test joining single part."""
        result = safe_path_join("/single/path")
        assert result == Path("/single/path")

    def test_join_absolute_paths(self):
        """Test joining with absolute paths."""
        # When joining absolute paths, later absolute paths replace earlier ones
        result = safe_path_join("/first/path", "/second/path")
        assert result == Path("/second/path")


class TestGetRelativePath:
    """Test get_relative_path function."""

    def test_relative_path_same_base(self):
        """Test getting relative path with common base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "base"
            base.mkdir()

            target = base / "sub" / "file.txt"
            target.parent.mkdir(parents=True)
            target.touch()

            result = get_relative_path(target, base)
            assert result == Path("sub/file.txt")

    def test_relative_path_different_base(self):
        """Test getting relative path with no common base."""
        # On different drives or completely unrelated paths
        path1 = Path("/completely/different/path")
        path2 = Path("/another/path")

        result = get_relative_path(path1, path2)
        # Should return absolute path when no common base
        assert result.is_absolute()

    def test_relative_path_default_base(self):
        """Test getting relative path with default base (cwd)."""
        import os

        original_cwd = os.getcwd()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                file_path = Path(tmpdir) / "file.txt"
                file_path.touch()

                result = get_relative_path(file_path)
                assert result == Path("file.txt")
        finally:
            os.chdir(original_cwd)

    def test_relative_path_with_parent_base(self):
        """Test relative path when base is parent of target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "level1" / "level2" / "file.txt"
            target.parent.mkdir(parents=True)
            target.touch()

            result = get_relative_path(target, base)
            assert result == Path("level1/level2/file.txt")


class TestFindFilesByPattern:
    """Test find_files_by_pattern function."""

    def test_find_files_recursive(self):
        """Test finding files recursively."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create test structure
            (root / "file1.txt").touch()
            (root / "file2.py").touch()

            subdir = root / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").touch()
            (subdir / "file4.py").touch()

            # Find all .txt files recursively
            result = find_files_by_pattern(root, "*.txt", recursive=True)
            assert len(result) == 2
            assert all(f.suffix == ".txt" for f in result)
            assert result[0] < result[1]  # Check sorting

    def test_find_files_non_recursive(self):
        """Test finding files non-recursively."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create test structure
            (root / "file1.txt").touch()
            (root / "file2.txt").touch()

            subdir = root / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").touch()

            # Find .txt files non-recursively
            result = find_files_by_pattern(root, "*.txt", recursive=False)
            assert len(result) == 2
            assert all(f.parent == root for f in result)

    def test_find_files_complex_pattern(self):
        """Test finding files with complex patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create various test files
            (root / "test_file.py").touch()
            (root / "test_another.py").touch()
            (root / "production_file.py").touch()
            (root / "test.txt").touch()

            # Find test Python files
            result = find_files_by_pattern(root, "test_*.py", recursive=False)
            assert len(result) == 2
            assert all("test_" in f.name and f.suffix == ".py" for f in result)

    def test_find_files_no_matches(self):
        """Test finding files with no matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").touch()

            result = find_files_by_pattern(root, "*.nonexistent")
            assert result == []


class TestIsValidBlockDirectory:
    """Test is_valid_block_directory function."""

    def test_valid_block_directory(self):
        """Test identifying a valid block directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "MY_BLOCK"
            block_dir.mkdir()

            # Create required files
            (block_dir / "MY_BLOCK.py").touch()
            (block_dir / "__init__.py").touch()

            assert is_valid_block_directory(block_dir) is True

    def test_invalid_missing_python_file(self):
        """Test block directory missing main Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "MY_BLOCK"
            block_dir.mkdir()

            # Only create __init__.py
            (block_dir / "__init__.py").touch()

            assert is_valid_block_directory(block_dir) is False

    def test_invalid_missing_init_file(self):
        """Test block directory missing __init__.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "MY_BLOCK"
            block_dir.mkdir()

            # Only create main Python file
            (block_dir / "MY_BLOCK.py").touch()

            assert is_valid_block_directory(block_dir) is False

    def test_invalid_not_directory(self):
        """Test that files are not valid block directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "not_a_directory.txt"
            file_path.touch()

            assert is_valid_block_directory(file_path) is False

    def test_invalid_wrong_python_filename(self):
        """Test block directory with mismatched Python filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "MY_BLOCK"
            block_dir.mkdir()

            # Create files with wrong name
            (block_dir / "WRONG_NAME.py").touch()
            (block_dir / "__init__.py").touch()

            assert is_valid_block_directory(block_dir) is False
