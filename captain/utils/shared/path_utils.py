#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Path utility functions for consistent path operations across the codebase.
"""

from pathlib import Path
from typing import Optional, List


def get_block_python_file(block_dir: Path | str) -> Path:
    """
    Get the Python file path for a block given its directory.

    Args:
        block_dir: Path to the block directory

    Returns:
        Path to the block's Python file
    """
    block_dir = Path(block_dir)
    block_name = block_dir.name
    return block_dir / f"{block_name}.py"


def get_block_metadata_file(block_dir: Path | str) -> Path:
    """
    Get the block_data.json file path for a block.

    Args:
        block_dir: Path to the block directory

    Returns:
        Path to the block's metadata file
    """
    return Path(block_dir) / "block_data.json"


def get_block_app_file(block_dir: Path | str) -> Path:
    """
    Get the app.json file path for a block.

    Args:
        block_dir: Path to the block directory

    Returns:
        Path to the block's app.json file
    """
    return Path(block_dir) / "app.json"


def get_block_example_file(block_dir: Path | str) -> Path:
    """
    Get the example.md file path for a block.

    Args:
        block_dir: Path to the block directory

    Returns:
        Path to the block's example file
    """
    return Path(block_dir) / "example.md"


def get_block_test_file(block_dir: Path | str) -> Path:
    """
    Get the test file path for a block.

    Args:
        block_dir: Path to the block directory

    Returns:
        Path to the block's test file
    """
    block_dir = Path(block_dir)
    block_name = block_dir.name
    return block_dir / f"{block_name}_test_.py"


def get_block_venv_dir(block_dir: Path | str) -> Path:
    """
    Get the virtual environment directory for a block.

    Args:
        block_dir: Path to the block directory

    Returns:
        Path to the block's virtual environment
    """
    return Path(block_dir) / ".venv"


def find_project_root(start_path: Optional[Path | str] = None) -> Optional[Path]:
    """
    Find the project root directory by looking for pyproject.toml.

    Args:
        start_path: Starting path to search from (default: current directory)

    Returns:
        Path to project root, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)

    current = start_path.resolve()

    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent

    return None


def ensure_directory_exists(
    path: Path | str, parents: bool = True, exist_ok: bool = True
) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory
        parents: Create parent directories if needed
        exist_ok: Don't raise error if directory already exists

    Returns:
        Path object for the directory
    """
    path = Path(path)
    path.mkdir(parents=parents, exist_ok=exist_ok)
    return path


def safe_path_join(*parts: str | Path) -> Path:
    """
    Safely join path components, handling various input types.

    Args:
        *parts: Path components to join

    Returns:
        Joined path
    """
    if not parts:
        return Path()

    # Convert all parts to Path objects and join
    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part

    return result


def get_relative_path(path: Path | str, base: Optional[Path | str] = None) -> Path:
    """
    Get relative path from base directory.

    Args:
        path: Path to make relative
        base: Base directory (default: current directory)

    Returns:
        Relative path
    """
    path = Path(path).resolve()

    if base is None:
        base = Path.cwd()
    else:
        base = Path(base).resolve()

    try:
        return path.relative_to(base)
    except ValueError:
        # Paths don't have a common base, return absolute path
        return path


def find_files_by_pattern(
    directory: Path | str, pattern: str, recursive: bool = True
) -> List[Path]:
    """
    Find all files matching a pattern in a directory.

    Args:
        directory: Directory to search in
        pattern: Glob pattern to match
        recursive: Search recursively in subdirectories

    Returns:
        List of matching file paths
    """
    directory = Path(directory)

    if recursive:
        return sorted(directory.rglob(pattern))
    else:
        return sorted(directory.glob(pattern))


def is_valid_block_directory(path: Path | str) -> bool:
    """
    Check if a directory is a valid block directory.

    Args:
        path: Path to check

    Returns:
        True if valid block directory, False otherwise
    """
    path = Path(path)

    if not path.is_dir():
        return False

    # Check for required files
    block_name = path.name
    python_file = path / f"{block_name}.py"
    init_file = path / "__init__.py"

    return python_file.exists() and init_file.exists()
