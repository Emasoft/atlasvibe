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
# - Initial implementation of sample project migration script
# - Converts old JSON-based sample projects to new folder-based format
# - Creates project folders with .atlasvibe files and atlasvibe_blocks directories
# - Automatically migrates all blocks to custom blocks
#

"""Script to migrate sample projects from old format to new folder-based format."""

import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from captain.utils.project_migration import (
    migrate_project_to_new_format,
    is_old_format_project,
)
from captain.utils.logger import logger


def create_project_folder_structure(source_json: Path, target_dir: Path, project_name: str) -> Path:
    """Create the new folder-based project structure.

    Args:
        source_json: Path to the source JSON file
        target_dir: Base directory for migrated projects
        project_name: Name of the project

    Returns:
        Path to the created .atlasvibe file
    """
    # Create project folder
    project_folder = target_dir / project_name
    project_folder.mkdir(parents=True, exist_ok=True)

    # Create .atlasvibe project file path
    project_file = project_folder / f"{project_name}.atlasvibe"

    # Create atlasvibe_blocks directory
    blocks_dir = project_folder / "atlasvibe_blocks"
    blocks_dir.mkdir(exist_ok=True)

    # Create __init__.py in blocks directory
    (blocks_dir / "__init__.py").write_text("")

    return project_file


def migrate_sample_project(source_path: Path, target_base_dir: Path) -> bool:
    """Migrate a single sample project to new format.

    Args:
        source_path: Path to the source JSON file
        target_base_dir: Base directory for migrated projects

    Returns:
        True if migration successful, False otherwise
    """
    try:
        # Load the project data
        with open(source_path, "r") as f:
            project_data = json.load(f)

        # Get project name from filename
        project_name = source_path.stem

        # Create folder structure
        project_file = create_project_folder_structure(source_path, target_base_dir, project_name)

        logger.info(f"Migrating project: {project_name}")

        # Check if it needs migration
        if not is_old_format_project(project_data):
            logger.info(f"Project {project_name} is already in new format")
            # Still save it to the new location
            with open(project_file, "w") as f:
                json.dump(project_data, f, indent=2)
            return True

        # Temporarily save the old format project to trigger migration
        with open(project_file, "w") as f:
            json.dump(project_data, f, indent=2)

        # Migrate the project
        migrated_data, created_blocks = migrate_project_to_new_format(str(project_file), project_data, dry_run=False)

        # Save the migrated project
        with open(project_file, "w") as f:
            json.dump(migrated_data, f, indent=2)

        logger.info(f"Successfully migrated {project_name}. " f"Created {len(created_blocks)} custom blocks.")

        return True

    except Exception as e:
        logger.error(f"Failed to migrate {source_path}: {e}")
        return False


def main():
    """Main migration function."""
    # Paths
    apps_dir = Path(__file__).parent.parent / "src" / "renderer" / "data" / "apps"
    target_dir = Path(__file__).parent.parent / "sample_projects"

    if not apps_dir.exists():
        logger.error(f"Apps directory not found: {apps_dir}")
        return 1

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Get all JSON files
    json_files = list(apps_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} sample projects to migrate")

    # Track results
    successful = 0
    failed = 0

    # Migrate each project
    for json_file in json_files:
        if json_file.stem == "index":  # Skip index.ts export file
            continue

        if migrate_sample_project(json_file, target_dir):
            successful += 1
        else:
            failed += 1

    logger.info(f"Migration complete. Successful: {successful}, Failed: {failed}")

    # Create a README for the sample projects
    readme_path = target_dir / "README.md"
    readme_content = """# Sample Projects

This directory contains sample AtlasVibe projects in the new folder-based format.

## Project Structure

Each project folder contains:
- `<project_name>.atlasvibe` - The main project file
- `atlasvibe_blocks/` - Directory containing custom block copies used by the project

## Format

These projects have been migrated from the old blueprint-based format to the new
project-centric format where each project contains its own custom block copies.

## Loading Projects

To load a project:
1. Open AtlasVibe
2. Use File > Open Project
3. Navigate to the project folder
4. Select the `.atlasvibe` file

The application will automatically load the project and its custom blocks.
"""

    readme_path.write_text(readme_content)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
