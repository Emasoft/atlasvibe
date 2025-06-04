#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of project structure utilities for atlasvibe
# - Created functions to manage project directories and custom blocks
# - Added project validation and initialization functions
# - Added block name validation and better error handling
# - Improved function name replacement with regex
# 

"""Project structure management utilities for atlasvibe.

This module handles the creation and management of project-centric
directory structures where each project contains its own custom blocks.
"""

import json
import shutil
import re
from pathlib import Path
from typing import Optional, List
from captain.utils.logger import logger


class ProjectStructureError(Exception):
    """Exception raised for project structure related errors."""
    pass


def get_project_dir(project_path: str) -> Path:
    """Get the project directory from a project file path.
    
    Args:
        project_path: Path to the .atlasvibe project file
        
    Returns:
        Path to the project directory
    """
    project_file = Path(project_path)
    if project_file.suffix != '.atlasvibe':
        raise ProjectStructureError(f"Invalid project file: {project_path}")
    
    # Project directory is the parent directory of the project file
    return project_file.parent


def get_project_blocks_dir(project_path: str) -> Path:
    """Get the custom blocks directory for a project.
    
    Args:
        project_path: Path to the .atlasvibe project file
        
    Returns:
        Path to the project's atlasvibe_blocks directory
    """
    project_dir = get_project_dir(project_path)
    return project_dir / "atlasvibe_blocks"


def initialize_project_structure(project_path: str) -> None:
    """Initialize the directory structure for a project.
    
    Creates the atlasvibe_blocks directory if it doesn't exist.
    
    Args:
        project_path: Path to the .atlasvibe project file
    """
    blocks_dir = get_project_blocks_dir(project_path)
    blocks_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py to make it a Python package
    init_file = blocks_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")
    
    logger.info(f"Initialized project structure at {blocks_dir}")


def validate_project_structure(project_path: str) -> bool:
    """Validate that a project has the correct structure.
    
    Args:
        project_path: Path to the .atlasvibe project file
        
    Returns:
        True if the project structure is valid, False otherwise
    """
    try:
        project_file = Path(project_path)
        if not project_file.exists():
            logger.debug(f"Project file does not exist: {project_path}")
            return False
        if project_file.suffix != '.atlasvibe':
            logger.debug(f"Invalid project file extension: {project_path}")
            return False
            
        blocks_dir = get_project_blocks_dir(project_path)
        is_valid = blocks_dir.exists() and blocks_dir.is_dir()
        if not is_valid:
            logger.debug(f"Project blocks directory missing or invalid: {blocks_dir}")
        return is_valid
    except (ProjectStructureError, OSError, ValueError) as e:
        logger.debug(f"Error validating project structure: {e}")
        return False


def list_project_blocks(project_path: str) -> List[str]:
    """List all custom blocks in a project.
    
    Args:
        project_path: Path to the .atlasvibe project file
        
    Returns:
        List of block names (directory names) in the project
    """
    blocks_dir = get_project_blocks_dir(project_path)
    if not blocks_dir.exists():
        return []
    
    blocks = []
    for item in blocks_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            # Check if it has a Python file with the same name
            py_file = item / f"{item.name}.py"
            if py_file.exists():
                blocks.append(item.name)
    
    return sorted(blocks)


def validate_block_name(name: str) -> None:
    """Validate a block name for safety and correctness.
    
    Args:
        name: The block name to validate
        
    Raises:
        ProjectStructureError: If the name is invalid
    """
    if not name or not name.strip():
        raise ProjectStructureError("Block name cannot be empty")
    
    # Check for path traversal attempts
    if '..' in name or '/' in name or '\\' in name:
        raise ProjectStructureError("Block name cannot contain path separators or '..'")
    
    # Check for valid Python identifier
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
        raise ProjectStructureError(
            "Block name must start with a letter and contain only letters, "
            "numbers, and underscores"
        )
    
    # Check for Python reserved words
    import keyword
    if keyword.iskeyword(name):
        raise ProjectStructureError(f"'{name}' is a Python reserved word")
    
    # Check for common problematic names
    reserved_names = {'__init__', '__main__', 'test', 'tests'}
    if name.lower() in reserved_names:
        raise ProjectStructureError(f"'{name}' is a reserved name")


def copy_blueprint_to_project(
    blueprint_path: str,
    project_path: str,
    new_block_name: str
) -> str:
    """Copy a blueprint block to a project as a custom block.
    
    Args:
        blueprint_path: Path to the blueprint block directory
        project_path: Path to the .atlasvibe project file
        new_block_name: Name for the new custom block
        
    Returns:
        Path to the new custom block directory
        
    Raises:
        ProjectStructureError: If the operation fails
    """
    # Validate the block name first
    validate_block_name(new_block_name)
    
    # Ensure project structure exists
    initialize_project_structure(project_path)
    
    blocks_dir = get_project_blocks_dir(project_path)
    new_block_dir = blocks_dir / new_block_name
    
    if new_block_dir.exists():
        raise ProjectStructureError(
            f"Block '{new_block_name}' already exists in project"
        )
    
    # Track if we need to rollback
    created_dir = False
    
    try:
        # Copy the blueprint directory
        shutil.copytree(blueprint_path, new_block_dir)
        created_dir = True
        
        # Ensure __init__.py exists in the new block directory
        block_init = new_block_dir / "__init__.py"
        if not block_init.exists():
            block_init.write_text("")
        
        # Rename the main Python file
        blueprint_name = Path(blueprint_path).name
        old_py_file = new_block_dir / f"{blueprint_name}.py"
        new_py_file = new_block_dir / f"{new_block_name}.py"
        
        if old_py_file.exists():
            old_py_file.rename(new_py_file)
            
            # Update function name in the Python file
            update_block_function_name(new_py_file, blueprint_name, new_block_name)
        else:
            raise ProjectStructureError(
                f"Blueprint Python file '{blueprint_name}.py' not found"
            )
        
        # Update metadata files
        update_block_metadata(new_block_dir, blueprint_name, new_block_name)
        
        logger.info(f"Created custom block '{new_block_name}' from blueprint '{blueprint_name}'")
        return str(new_block_dir)
        
    except Exception as e:
        # Rollback on failure
        if created_dir and new_block_dir.exists():
            try:
                shutil.rmtree(new_block_dir)
                logger.info(f"Rolled back creation of block '{new_block_name}'")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback: {rollback_error}")
        
        logger.error(f"Failed to copy blueprint to project: {e}")
        if isinstance(e, ProjectStructureError):
            raise
        raise ProjectStructureError(str(e))


def update_block_function_name(
    py_file: Path,
    old_name: str,
    new_name: str
) -> None:
    """Update the function name in a block's Python file.
    
    Args:
        py_file: Path to the Python file
        old_name: Original function name
        new_name: New function name
    """
    content = py_file.read_text()
    
    # Use regex to replace function definition more precisely
    # This handles cases with different spacing and ensures we only replace
    # the function definition, not other occurrences of the name
    pattern = rf'^(\s*def\s+){re.escape(old_name)}(\s*\()'
    replacement = rf'\1{new_name}\2'
    
    # Use MULTILINE flag to match at the beginning of any line
    updated_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if updated_content == content:
        logger.warning(f"Function definition 'def {old_name}(' not found in {py_file}")
    
    py_file.write_text(updated_content)


def update_block_metadata(
    block_dir: Path,
    old_name: str,
    new_name: str
) -> None:
    """Update metadata files in a block directory.
    
    Args:
        block_dir: Path to the block directory
        old_name: Original block name
        new_name: New block name
    """
    # Update app.json if it exists
    app_json = block_dir / "app.json"
    if app_json.exists():
        data = json.loads(app_json.read_text())
        
        # Update node labels and function references
        if "rfInstance" in data and "nodes" in data["rfInstance"]:
            for node in data["rfInstance"]["nodes"]:
                if "data" in node:
                    if node["data"].get("func") == old_name:
                        node["data"]["func"] = new_name
                    if node["data"].get("label") == old_name:
                        node["data"]["label"] = new_name
        
        app_json.write_text(json.dumps(data, indent=2))
    
    # Update block_data.json if it exists
    block_data_json = block_dir / "block_data.json"
    if block_data_json.exists():
        # The block_data.json typically doesn't contain the function name,
        # but we'll check just in case
        data = json.loads(block_data_json.read_text())
        block_data_json.write_text(json.dumps(data, indent=2))


def get_custom_block_path(project_path: str, block_name: str) -> Optional[str]:
    """Get the full path to a custom block in a project.
    
    Args:
        project_path: Path to the .atlasvibe project file
        block_name: Name of the custom block
        
    Returns:
        Full path to the block directory, or None if not found
    """
    blocks_dir = get_project_blocks_dir(project_path)
    block_dir = blocks_dir / block_name
    
    if block_dir.exists() and block_dir.is_dir():
        return str(block_dir)
    
    return None