#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of project-scoped block loading
# - Support for loading blocks from both blueprint directory and project directory
# - Added caching and module management for project blocks
# 

"""Project-scoped block loading utilities.

This module handles loading blocks from both the global blueprint directory
and project-specific atlasvibe_blocks directories.
"""

import os
import sys
import importlib
from pathlib import Path
from typing import Dict, Optional
from captain.utils.logger import logger
from captain.utils.blocks_path import get_blocks_path
from captain.utils.project_structure import get_project_blocks_dir, validate_project_structure
from captain.utils.block_utils import add_to_sys_path


class ProjectBlocksLoader:
    """Manages loading blocks for a specific project."""
    
    def __init__(self, project_path: Optional[str] = None):
        """Initialize the loader.
        
        Args:
            project_path: Path to the .atlasvibe project file
        """
        self.project_path = project_path
        self.blueprint_mapping: Dict[str, str] = {}
        self.project_mapping: Dict[str, str] = {}
        self.combined_mapping: Dict[str, str] = {}
        self._initialized = False
        
    def initialize(self) -> None:
        """Initialize the block mappings."""
        if self._initialized:
            return
            
        # Load blueprint blocks
        self._load_blueprint_blocks()
        
        # Load project-specific blocks if project path is provided
        if self.project_path and validate_project_structure(self.project_path):
            self._load_project_blocks()
            
        # Combine mappings, with project blocks taking precedence
        self.combined_mapping = {**self.blueprint_mapping, **self.project_mapping}
        self._initialized = True
        
    def _load_blueprint_blocks(self) -> None:
        """Load blueprint blocks from the global blocks directory."""
        try:
            blocks_dir = get_blocks_path()
            parent_dir = Path(blocks_dir).parent
            
            # Add to sys.path if not already there
            add_to_sys_path(parent_dir)
                
            # Walk through blueprint blocks
            for root, _, files in os.walk(blocks_dir):
                if root == blocks_dir:
                    continue
                    
                for file in files:
                    if file.endswith(".py") and not file.startswith("_"):
                        try:
                            # Create module path
                            rel_path = Path(root).relative_to(parent_dir)
                            module_parts = list(rel_path.parts) + [file[:-3]]
                            module_path = ".".join(module_parts)
                            
                            # Map function name to module path
                            func_name = file[:-3]
                            self.blueprint_mapping[func_name] = module_path
                        except Exception as e:
                            logger.error(f"Failed to process blueprint block {file}: {e}")
                        
            logger.info(f"Loaded {len(self.blueprint_mapping)} blueprint blocks")
        except Exception as e:
            logger.error(f"Failed to load blueprint blocks: {e}")
            # Continue without blueprint blocks rather than failing completely
        
    def _load_project_blocks(self) -> None:
        """Load project-specific blocks."""
        if not self.project_path:
            return
            
        try:
            project_blocks_dir = get_project_blocks_dir(self.project_path)
            if not project_blocks_dir.exists():
                return
                
            # Add project directory to sys.path with priority
            project_dir = project_blocks_dir.parent
            add_to_sys_path(project_dir, prepend=True)
                
            # Walk through project blocks
            for block_dir in project_blocks_dir.iterdir():
                if not block_dir.is_dir() or block_dir.name.startswith("_"):
                    continue
                    
                try:
                    # Look for Python file with same name as directory
                    py_file = block_dir / f"{block_dir.name}.py"
                    if py_file.exists():
                        # Check for __init__.py
                        init_file = block_dir / "__init__.py"
                        if not init_file.exists():
                            logger.warning(f"Block {block_dir.name} missing __init__.py, creating one")
                            init_file.write_text("")
                            
                        # Create module path relative to project directory
                        module_path = f"atlasvibe_blocks.{block_dir.name}.{block_dir.name}"
                        self.project_mapping[block_dir.name] = module_path
                except Exception as e:
                    logger.error(f"Failed to process project block {block_dir.name}: {e}")
                    
            logger.info(f"Loaded {len(self.project_mapping)} project-specific blocks")
        except Exception as e:
            logger.error(f"Failed to load project blocks: {e}")
            # Continue without project blocks rather than failing completely
        
    def get_module(self, func_name: str):
        """Get a module for a given function name.
        
        Args:
            func_name: Name of the function/block
            
        Returns:
            Imported module or None if not found
        """
        if not self._initialized:
            self.initialize()
            
        module_path = self.combined_mapping.get(func_name)
        if not module_path:
            logger.error(f"Block '{func_name}' not found in mappings")
            return None
            
        try:
            # Import and reload to get latest changes
            module = importlib.import_module(module_path)
            module = importlib.reload(module)
            return module
        except Exception as e:
            logger.error(f"Failed to import module '{module_path}': {e}")
            return None
            
    def get_available_blocks(self) -> Dict[str, Dict[str, str]]:
        """Get all available blocks categorized by source.
        
        Returns:
            Dictionary with 'blueprints' and 'project' keys
        """
        if not self._initialized:
            self.initialize()
            
        return {
            "blueprints": dict(self.blueprint_mapping),
            "project": dict(self.project_mapping)
        }
        
    def is_project_block(self, func_name: str) -> bool:
        """Check if a block is from the project directory.
        
        Args:
            func_name: Name of the function/block
            
        Returns:
            True if it's a project-specific block
        """
        return func_name in self.project_mapping
        
    def clear_project_modules(self) -> None:
        """Clear project-specific modules from sys.modules.
        
        This is useful when switching projects.
        """
        modules_to_remove = []
        for module_name in sys.modules:
            if module_name.startswith("atlasvibe_blocks."):
                modules_to_remove.append(module_name)
                
        for module_name in modules_to_remove:
            del sys.modules[module_name]
            
        logger.info(f"Cleared {len(modules_to_remove)} project modules")


# Global instance for current project
_current_loader: Optional[ProjectBlocksLoader] = None


def get_project_loader(project_path: Optional[str] = None) -> ProjectBlocksLoader:
    """Get or create a project blocks loader.
    
    Args:
        project_path: Path to the .atlasvibe project file
        
    Returns:
        ProjectBlocksLoader instance
    """
    global _current_loader
    
    # If project path changed, create new loader
    if _current_loader is None or _current_loader.project_path != project_path:
        if _current_loader:
            _current_loader.clear_project_modules()
        _current_loader = ProjectBlocksLoader(project_path)
        
    return _current_loader


def get_module_for_block(func_name: str, project_path: Optional[str] = None):
    """Get a module for a given block function.
    
    This is a convenience function that uses the global loader.
    
    Args:
        func_name: Name of the function/block
        project_path: Path to the .atlasvibe project file
        
    Returns:
        Imported module or None if not found
    """
    loader = get_project_loader(project_path)
    return loader.get_module(func_name)