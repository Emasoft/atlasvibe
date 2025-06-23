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
# - Initial implementation of project migration utilities
# - Migrates old blueprint-based projects to new custom block format
# - Automatically creates custom block copies for all blocks in workflow
# - Updates workflow to reference custom blocks instead of blueprints
#

"""Project migration utilities for converting old format projects to new format.

Handles migration from blueprint-based projects to project-centric custom block format.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from captain.utils.logger import logger
from captain.utils.project_structure import (
    initialize_project_structure,
    copy_blueprint_to_project,
    get_project_blocks_dir,
    ProjectStructureError,
)
from captain.utils.blocks_path import get_blocks_path


class ProjectMigrationError(Exception):
    """Exception raised for project migration errors."""

    pass


def is_old_format_project(project_data: dict) -> bool:
    """Check if a project is in the old blueprint-based format.

    Args:
        project_data: The project data dictionary

    Returns:
        True if project is in old format, False otherwise
    """
    # Check if project has rfInstance with nodes
    if "rfInstance" not in project_data or "nodes" not in project_data["rfInstance"]:
        return False

    nodes = project_data["rfInstance"]["nodes"]
    if not nodes:
        return False

    # Check if any node is missing isCustom field or has blueprint paths
    for node in nodes:
        if "data" not in node:
            continue

        node_data = node["data"]

        # If node has isCustom=True, it's already in new format
        if node_data.get("isCustom", False):
            continue

        # If node has a path that looks like a blueprint path, it's old format
        if "path" in node_data:
            path = node_data["path"]
            # Blueprint paths don't contain "atlasvibe_blocks"
            if "atlasvibe_blocks" not in path:
                return True

    return False


def find_blueprint_block(blueprint_key: str) -> Optional[Path]:
    """Find the path to a blueprint block.

    Args:
        blueprint_key: The block function name (e.g., "CONSTANT", "SINE")

    Returns:
        Path to the blueprint directory if found, None otherwise
    """
    blocks_base_path = Path(get_blocks_path())

    # Search for the block in the blueprint directory structure
    for block_path in blocks_base_path.rglob(blueprint_key):
        if block_path.is_dir() and (block_path / f"{blueprint_key}.py").exists():
            return block_path

    return None


def migrate_project_to_new_format(
    project_path: str, project_data: dict, dry_run: bool = False
) -> Tuple[dict, List[str]]:
    """Migrate a project from old blueprint format to new custom block format.

    Args:
        project_path: Path to the .atlasvibe project file
        project_data: The project data dictionary
        dry_run: If True, don't actually create files, just return what would be done

    Returns:
        Tuple of (migrated_project_data, list_of_created_blocks)

    Raises:
        ProjectMigrationError: If migration fails
    """
    if not is_old_format_project(project_data):
        logger.info("Project is already in new format, no migration needed")
        return project_data, []

    logger.info(f"Migrating project {project_path} to new format...")

    # Initialize project structure if not in dry run
    if not dry_run:
        initialize_project_structure(project_path)

    # Track created blocks and block name mappings
    created_blocks = []
    block_mappings = {}  # old_func -> new_custom_name

    # Copy the project data to avoid modifying the original
    migrated_data = json.loads(json.dumps(project_data))

    # Process each node in the workflow
    nodes = migrated_data["rfInstance"]["nodes"]

    for node in nodes:
        if "data" not in node:
            continue

        node_data = node["data"]

        # Skip if already a custom block
        if node_data.get("isCustom", False):
            continue

        # Get the blueprint function name
        func_name = node_data.get("func")
        if not func_name:
            continue

        # Check if we've already created this custom block
        if func_name in block_mappings:
            custom_name = block_mappings[func_name]
        else:
            # Find the blueprint block
            blueprint_path = find_blueprint_block(func_name)
            if not blueprint_path:
                logger.warning(
                    f"Could not find blueprint for block '{func_name}', will mark as hardware block"
                )
                # For hardware blocks that don't have blueprints, just mark them
                # They will need to be manually configured when the hardware is connected
                node_data["isHardwareBlock"] = True
                node_data["requiresHardware"] = True
                continue

            # Generate a unique custom block name
            base_name = func_name
            counter = 1
            custom_name = f"{base_name}_{counter}"

            # Ensure uniqueness
            blocks_dir = get_project_blocks_dir(project_path)
            while (blocks_dir / custom_name).exists():
                counter += 1
                custom_name = f"{base_name}_{counter}"

            # Create the custom block if not in dry run
            if not dry_run:
                try:
                    copy_blueprint_to_project(
                        str(blueprint_path), project_path, custom_name
                    )
                    logger.info(
                        f"Created custom block '{custom_name}' from blueprint '{func_name}'"
                    )
                except ProjectStructureError as e:
                    raise ProjectMigrationError(
                        f"Failed to create custom block '{custom_name}': {e}"
                    )
            else:
                # Custom block already exists at blocks_dir / custom_name
                pass

            created_blocks.append(custom_name)
            block_mappings[func_name] = custom_name

        # Update the node to reference the custom block
        node_data["func"] = custom_name
        node_data["isCustom"] = True
        node_data["path"] = str(
            Path("atlasvibe_blocks") / custom_name / f"{custom_name}.py"
        )

        # Update the node label if it matches the old function name
        if node_data.get("label") == func_name:
            node_data["label"] = custom_name

    logger.info(f"Migration complete. Created {len(created_blocks)} custom blocks.")

    return migrated_data, created_blocks


def needs_migration(project_path: str) -> bool:
    """Check if a project file needs migration.

    Args:
        project_path: Path to the .atlasvibe project file

    Returns:
        True if project needs migration, False otherwise
    """
    try:
        with open(project_path, "r") as f:
            project_data = json.load(f)
        return is_old_format_project(project_data)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error checking project {project_path}: {e}")
        return False
