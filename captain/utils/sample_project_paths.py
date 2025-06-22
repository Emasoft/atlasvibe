#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of centralized sample project path utilities
# - Provides consistent path resolution for sample projects
# - Handles both development and packaged app scenarios
#

"""Utilities for handling sample project paths consistently."""

import os
from pathlib import Path
from typing import Optional


def is_sample_project_path(path: str) -> bool:
    """Check if a path refers to a sample project.

    Args:
        path: The path to check

    Returns:
        True if path starts with 'sample_projects/', False otherwise
    """
    return path.startswith("sample_projects/")


def resolve_sample_project_path(path: str) -> Path:
    """Resolve a sample project path to an absolute path.

    Args:
        path: The sample project path (e.g., "sample_projects/loop")

    Returns:
        Absolute path to the sample project

    Raises:
        FileNotFoundError: If the sample project doesn't exist
    """
    if not is_sample_project_path(path):
        raise ValueError(f"Not a sample project path: {path}")

    # Get app root directory
    app_root = Path(os.getcwd())

    # Check if we're in development (captain directory exists)
    if (app_root / "captain").exists():
        # Development mode
        sample_path = app_root / path
    else:
        # Packaged app mode - samples might be in resources
        # This would need to be adjusted based on how Electron packages resources
        sample_path = app_root / path

    if not sample_path.exists():
        raise FileNotFoundError(f"Sample project not found: {sample_path}")

    return sample_path


def get_sample_project_file(project_name: str) -> Optional[Path]:
    """Get the .atlasvibe file for a sample project.

    Args:
        project_name: Name of the sample project (e.g., "loop")

    Returns:
        Path to the .atlasvibe file if found, None otherwise
    """
    try:
        project_dir = resolve_sample_project_path(f"sample_projects/{project_name}")
        project_file = project_dir / f"{project_name}.atlasvibe"

        if project_file.exists():
            return project_file
        return None
    except (ValueError, FileNotFoundError):
        return None


def get_sample_project_blocks_dir(project_name: str) -> Optional[Path]:
    """Get the atlasvibe_blocks directory for a sample project.

    Args:
        project_name: Name of the sample project

    Returns:
        Path to the blocks directory if found, None otherwise
    """
    try:
        project_dir = resolve_sample_project_path(f"sample_projects/{project_name}")
        blocks_dir = project_dir / "atlasvibe_blocks"

        if blocks_dir.exists():
            return blocks_dir
        return None
    except (ValueError, FileNotFoundError):
        return None
