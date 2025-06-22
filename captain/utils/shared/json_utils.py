#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

"""
JSON utility functions for consistent file operations across the codebase.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import tempfile
from captain.utils.logger import logger


def load_json_file(
    file_path: Path | str,
    default: Optional[Dict[str, Any]] = None,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    Load JSON data from a file with error handling.

    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid
        encoding: File encoding (default: utf-8)

    Returns:
        Dict containing the JSON data, or default if error occurs
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.warning(f"JSON file not found: {file_path}")
        return default if default is not None else {}

    try:
        with open(file_path, "r", encoding=encoding) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        return default if default is not None else {}
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return default if default is not None else {}


def save_json_file(
    file_path: Path | str,
    data: Dict[str, Any],
    indent: int = 2,
    encoding: str = "utf-8",
    atomic: bool = True,
    create_parents: bool = True,
) -> bool:
    """
    Save JSON data to a file with atomic write support.

    Args:
        file_path: Path to save the JSON file
        data: Dictionary to save as JSON
        indent: JSON indentation (default: 2)
        encoding: File encoding (default: utf-8)
        atomic: Use atomic write to prevent corruption (default: True)
        create_parents: Create parent directories if they don't exist (default: True)

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)

    try:
        # Create parent directories if needed
        if create_parents and not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert data to JSON string
        json_str = json.dumps(data, indent=indent, ensure_ascii=False)

        if atomic:
            # Write to temporary file first, then rename (atomic operation)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding=encoding, dir=file_path.parent, delete=False
            ) as tmp_file:
                tmp_file.write(json_str)
                tmp_file.write("\n")  # Add trailing newline
                tmp_path = tmp_file.name

            # Atomic rename
            os.replace(tmp_path, file_path)
        else:
            # Direct write
            with open(file_path, "w", encoding=encoding) as f:
                f.write(json_str)
                f.write("\n")  # Add trailing newline

        return True

    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")
        # Clean up temporary file if it exists
        if atomic and "tmp_path" in locals() and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return False


def update_json_file(
    file_path: Path | str,
    updates: Dict[str, Any],
    create_if_missing: bool = True,
    encoding: str = "utf-8",
) -> bool:
    """
    Update specific fields in a JSON file while preserving other content.

    Args:
        file_path: Path to the JSON file
        updates: Dictionary of updates to apply
        create_if_missing: Create file if it doesn't exist (default: True)
        encoding: File encoding (default: utf-8)

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)

    # Load existing data
    if file_path.exists():
        data = load_json_file(file_path, default={}, encoding=encoding)
    elif create_if_missing:
        data = {}
    else:
        logger.error(f"JSON file not found and create_if_missing=False: {file_path}")
        return False

    # Apply updates
    data.update(updates)

    # Save back
    return save_json_file(file_path, data, encoding=encoding)


def merge_json_files(
    source_files: list[Path | str], target_file: Path | str, encoding: str = "utf-8"
) -> bool:
    """
    Merge multiple JSON files into one.

    Args:
        source_files: List of source JSON files to merge
        target_file: Target file to save merged data
        encoding: File encoding (default: utf-8)

    Returns:
        True if successful, False otherwise
    """
    merged_data = {}

    for source in source_files:
        source_path = Path(source)
        if source_path.exists():
            data = load_json_file(source_path, encoding=encoding)
            merged_data.update(data)
        else:
            logger.warning(f"Source file not found, skipping: {source_path}")

    return save_json_file(target_file, merged_data, encoding=encoding)
