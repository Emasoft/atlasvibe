#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of shared block utilities
# - Extracted common block discovery and path management functions
# - Centralized validation and error handling patterns
# 

"""Shared utilities for block operations.

This module provides common functionality used across block-related modules
to reduce code duplication and improve maintainability.
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from captain.utils.logger import logger


def add_to_sys_path(path: Path, prepend: bool = False) -> bool:
    """Add a path to sys.path if not already present.
    
    Args:
        path: Path to add
        prepend: Whether to add at the beginning (True) or end (False)
        
    Returns:
        True if path was added, False if already present
    """
    path_str = str(path)
    if path_str not in sys.path:
        if prepend:
            sys.path.insert(0, path_str)
        else:
            sys.path.append(path_str)
        logger.debug(f"Added {path_str} to sys.path")
        return True
    return False


def find_block_directories(root_path: Path, check_init: bool = False) -> Dict[str, Path]:
    """Find all block directories in a given path.
    
    Args:
        root_path: Root directory to search
        check_init: Whether to check for __init__.py files
        
    Returns:
        Dictionary mapping block names to their paths
    """
    blocks = {}
    
    if not root_path.exists() or not root_path.is_dir():
        return blocks
        
    try:
        for item in root_path.iterdir():
            if not item.is_dir() or item.name.startswith('_'):
                continue
                
            # Check for Python file with same name as directory
            py_file = item / f"{item.name}.py"
            if py_file.exists():
                # Optionally check for __init__.py
                if check_init:
                    init_file = item / "__init__.py"
                    if not init_file.exists():
                        logger.warning(f"Block {item.name} missing __init__.py")
                        continue
                        
                blocks[item.name] = item
    except Exception as e:
        logger.error(f"Error scanning directory {root_path}: {e}")
        
    return blocks


def construct_module_path(block_path: Path, base_path: Path) -> str:
    """Construct a Python module path from a file path.
    
    Args:
        block_path: Path to the block
        base_path: Base path to calculate relative path from
        
    Returns:
        Module path as a dot-separated string
    """
    try:
        rel_path = block_path.relative_to(base_path)
        return ".".join(rel_path.parts)
    except ValueError as e:
        logger.error(f"Failed to construct module path: {e}")
        raise


def find_blueprint_in_categories(blocks_dir: Path, blueprint_key: str) -> Optional[Path]:
    """Find a blueprint block in category directories.
    
    Args:
        blocks_dir: Base blocks directory
        blueprint_key: Name of the blueprint to find
        
    Returns:
        Path to blueprint directory if found, None otherwise
    """
    # Search patterns for different nesting levels
    patterns = ["*/*", "*/*/*"]
    
    for pattern in patterns:
        try:
            for block_dir in blocks_dir.glob(f"{pattern}/{blueprint_key}"):
                if block_dir.is_dir():
                    return block_dir
        except Exception as e:
            logger.error(f"Error searching for blueprint {blueprint_key}: {e}")
            
    return None


def ensure_init_files(directory: Path) -> None:
    """Ensure __init__.py files exist in a directory hierarchy.
    
    Args:
        directory: Directory to check
    """
    # Create __init__.py in the directory
    init_file = directory / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")
        logger.debug(f"Created __init__.py in {directory}")
        
    # Also ensure parent directories have __init__.py if needed
    parent = directory.parent
    if parent.name == "atlasvibe_blocks" and not (parent / "__init__.py").exists():
        (parent / "__init__.py").write_text("")
        logger.debug(f"Created __init__.py in {parent}")


def validate_path_safe(path: str) -> bool:
    """Validate that a path is safe (no traversal attempts).
    
    Args:
        path: Path string to validate
        
    Returns:
        True if path is safe, False otherwise
    """
    # Check for path traversal attempts
    if '..' in path or path.startswith('/') or path.startswith('\\'):
        return False
        
    # Check for absolute paths on Windows
    if len(path) > 1 and path[1] == ':':
        return False
        
    return True