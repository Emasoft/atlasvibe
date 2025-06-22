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
Text file utility functions for consistent file operations across the codebase.
"""

import os
import tempfile
from pathlib import Path
from captain.utils.logger import logger


def load_text_file(
    file_path: Path | str,
    default: str = "",
    encoding: str = "utf-8",
) -> str:
    """
    Load text content from a file with error handling.

    Args:
        file_path: Path to the text file
        default: Default value to return if file doesn't exist or is invalid
        encoding: File encoding (default: utf-8)

    Returns:
        String containing the file content, or default if error occurs
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.warning(f"Text file not found: {file_path}")
        return default

    try:
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return default


def save_text_file(
    file_path: Path | str,
    content: str,
    encoding: str = "utf-8",
    atomic: bool = True,
    create_parents: bool = True,
) -> bool:
    """
    Save text content to a file with atomic write support.

    Args:
        file_path: Path to save the text file
        content: Text content to save
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

        if atomic:
            # Write to temporary file first, then rename (atomic operation)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding=encoding, dir=file_path.parent, delete=False
            ) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Atomic rename
            os.replace(tmp_path, file_path)
        else:
            # Direct write
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)

        return True

    except Exception as e:
        logger.error(f"Error saving text file {file_path}: {e}")
        # Clean up temporary file if it exists
        if atomic and "tmp_path" in locals() and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return False


def append_text_file(
    file_path: Path | str,
    content: str,
    encoding: str = "utf-8",
    create_if_missing: bool = True,
) -> bool:
    """
    Append text content to a file.

    Args:
        file_path: Path to the text file
        content: Text content to append
        encoding: File encoding (default: utf-8)
        create_if_missing: Create file if it doesn't exist (default: True)

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)

    try:
        if not file_path.exists() and not create_if_missing:
            logger.error(
                f"Text file not found and create_if_missing=False: {file_path}"
            )
            return False

        # Create parent directories if needed
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "a", encoding=encoding) as f:
            f.write(content)

        return True

    except Exception as e:
        logger.error(f"Error appending to text file {file_path}: {e}")
        return False


def update_text_file(
    file_path: Path | str,
    old_text: str,
    new_text: str,
    replace_all: bool = True,
    encoding: str = "utf-8",
) -> bool:
    """
    Update text in a file by replacing occurrences.

    Args:
        file_path: Path to the text file
        old_text: Text to search for
        new_text: Text to replace with
        replace_all: Replace all occurrences (True) or just first (False)
        encoding: File encoding (default: utf-8)

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"Text file not found: {file_path}")
        return False

    try:
        # Load current content
        content = load_text_file(file_path, encoding=encoding)

        # Replace text
        if replace_all:
            updated_content = content.replace(old_text, new_text)
        else:
            updated_content = content.replace(old_text, new_text, 1)

        # Save back
        return save_text_file(file_path, updated_content, encoding=encoding)

    except Exception as e:
        logger.error(f"Error updating text file {file_path}: {e}")
        return False


def merge_text_files(
    source_files: list[Path | str],
    target_file: Path | str,
    separator: str = "",
    encoding: str = "utf-8",
) -> bool:
    """
    Merge multiple text files into one.

    Args:
        source_files: List of source text files to merge
        target_file: Target file to save merged content
        separator: Text to insert between merged files (default: empty)
        encoding: File encoding (default: utf-8)

    Returns:
        True if successful, False otherwise
    """
    merged_parts = []

    for source in source_files:
        source_path = Path(source)
        if source_path.exists():
            content = load_text_file(source_path, encoding=encoding)
            merged_parts.append(content)
        else:
            logger.warning(f"Source file not found, skipping: {source_path}")

    # Join with separator
    merged_content = separator.join(merged_parts)

    return save_text_file(target_file, merged_content, encoding=encoding)
