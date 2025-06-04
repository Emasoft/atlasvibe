#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of project structure utilities for atlasvibe
# - Created functions to manage project directories and custom blocks
# - Added project validation and initialization functions
# 

"""Project structure management utilities for atlasvibe.

This module handles the creation and management of project-centric
directory structures where each project contains its own custom blocks.
"""

import json
import shutil
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
        if not project_file.exists() or project_file.suffix != '.atlasvibe':
            return False
            
        blocks_dir = get_project_blocks_dir(project_path)
        return blocks_dir.exists() and blocks_dir.is_dir()
    except Exception:
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
    try:
        # Ensure project structure exists
        initialize_project_structure(project_path)
        
        blocks_dir = get_project_blocks_dir(project_path)
        new_block_dir = blocks_dir / new_block_name
        
        if new_block_dir.exists():
            raise ProjectStructureError(
                f"Block '{new_block_name}' already exists in project"
            )
        
        # Copy the blueprint directory
        shutil.copytree(blueprint_path, new_block_dir)
        
        # Rename the main Python file
        blueprint_name = Path(blueprint_path).name
        old_py_file = new_block_dir / f"{blueprint_name}.py"
        new_py_file = new_block_dir / f"{new_block_name}.py"
        
        if old_py_file.exists():
            old_py_file.rename(new_py_file)
            
            # Update function name in the Python file
            update_block_function_name(new_py_file, blueprint_name, new_block_name)
        
        # Update metadata files
        update_block_metadata(new_block_dir, blueprint_name, new_block_name)
        
        logger.info(f"Created custom block '{new_block_name}' from blueprint '{blueprint_name}'")
        return str(new_block_dir)
        
    except Exception as e:
        logger.error(f"Failed to copy blueprint to project: {e}")
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
    
    # Replace the decorated function name
    content = content.replace(f"def {old_name}(", f"def {new_name}(")
    
    py_file.write_text(content)


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