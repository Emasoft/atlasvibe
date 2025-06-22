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
Module Reloader for AtlasVibe

Provides hot-reloading capabilities for Python modules when code changes,
enabling real-time updates without restarting the application.
"""

import importlib
import importlib.util
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from threading import Lock

from captain.utils.logger import logger


class ModuleReloader:
    """
    Manages hot-reloading of Python modules.

    Features:
    - Tracks module dependencies
    - Reloads modules in correct order
    - Handles circular dependencies
    - Preserves module state where possible
    - Thread-safe operations
    """

    def __init__(self):
        """Initialize the module reloader."""
        self._reload_lock = Lock()
        self._reload_times: Dict[str, float] = {}
        self._module_dependencies: Dict[str, Set[str]] = {}
        self._failed_reloads: Dict[str, str] = {}

    def reload_module(self, module_name: str, force: bool = False) -> bool:
        """
        Reload a module and its dependencies.

        Args:
            module_name: Name of the module to reload
            force: Force reload even if recently reloaded

        Returns:
            True if reload successful, False otherwise
        """
        with self._reload_lock:
            try:
                # Check if module exists
                if module_name not in sys.modules:
                    logger.warning(f"Module {module_name} not loaded, cannot reload")
                    return False

                # Check if recently reloaded (within 1 second)
                if not force:
                    last_reload = self._reload_times.get(module_name, 0)
                    if time.time() - last_reload < 1.0:
                        logger.debug(
                            f"Module {module_name} recently reloaded, skipping"
                        )
                        return True

                # Get module and its dependencies
                dependencies = self._get_module_dependencies(module_name)

                # Reload in dependency order
                reloaded = self._reload_with_dependencies(module_name, dependencies)

                if reloaded:
                    self._reload_times[module_name] = time.time()
                    logger.info(f"Successfully reloaded module: {module_name}")
                    return True
                else:
                    logger.error(f"Failed to reload module: {module_name}")
                    return False

            except Exception as e:
                logger.error(f"Error reloading module {module_name}: {e}")
                self._failed_reloads[module_name] = str(e)
                return False

    def reload_module_from_path(self, file_path: Path) -> Optional[str]:
        """
        Reload a module from its file path.

        Args:
            file_path: Path to the Python file

        Returns:
            Module name if reloaded successfully, None otherwise
        """
        try:
            # Convert file path to module name
            module_name = self._path_to_module_name(file_path)

            if not module_name:
                logger.warning(f"Could not determine module name for {file_path}")
                return None

            # Check if module is loaded
            if module_name in sys.modules:
                # Reload existing module
                if self.reload_module(module_name):
                    return module_name
            else:
                # Load new module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    logger.info(f"Loaded new module: {module_name}")
                    return module_name

            return None

        except Exception as e:
            logger.error(f"Error reloading module from {file_path}: {e}")
            return None

    def reload_block_module(self, block_path: Path) -> bool:
        """
        Reload a block module specifically.

        Args:
            block_path: Path to the block Python file

        Returns:
            True if reload successful, False otherwise
        """
        try:
            # Construct module name for block
            parts = []

            # Walk up from file to find 'blocks' directory
            current = block_path
            while current.parent != current:
                if current.name == "blocks":
                    break
                parts.insert(0, current.name)
                current = current.parent

            if current.name != "blocks":
                # Try alternative: use relative path from project
                parts = str(block_path).split("/")
                if "blocks" in parts:
                    idx = parts.index("blocks")
                    parts = parts[idx:]
                    parts[-1] = parts[-1].replace(".py", "")
                else:
                    logger.warning(f"Could not find 'blocks' in path: {block_path}")
                    return False
            else:
                # Remove .py extension from filename
                parts[-1] = parts[-1].replace(".py", "")

            module_name = ".".join(parts)

            # Try to reload
            return self.reload_module(module_name, force=True)

        except Exception as e:
            logger.error(f"Error reloading block module {block_path}: {e}")
            return False

    def _get_module_dependencies(self, module_name: str) -> List[str]:
        """Get dependencies of a module that should be reloaded."""
        dependencies = []

        try:
            module = sys.modules.get(module_name)
            if not module:
                return dependencies

            # Check module's __dict__ for imported modules
            for name, obj in module.__dict__.items():
                if hasattr(obj, "__module__"):
                    dep_module = obj.__module__
                    if dep_module and dep_module != module_name:
                        # Only include user modules, not built-ins
                        if not dep_module.startswith("_") and "." in dep_module:
                            if dep_module.startswith(("captain", "blocks", "pkgs")):
                                dependencies.append(dep_module)

            # Remove duplicates while preserving order
            seen = set()
            unique_deps = []
            for dep in dependencies:
                if dep not in seen:
                    seen.add(dep)
                    unique_deps.append(dep)

            return unique_deps

        except Exception as e:
            logger.warning(f"Error getting dependencies for {module_name}: {e}")
            return []

    def _reload_with_dependencies(
        self, module_name: str, dependencies: List[str]
    ) -> bool:
        """Reload a module and its dependencies in correct order."""
        try:
            # Reload dependencies first
            for dep in dependencies:
                if dep in sys.modules:
                    try:
                        importlib.reload(sys.modules[dep])
                        logger.debug(f"Reloaded dependency: {dep}")
                    except Exception as e:
                        logger.warning(f"Failed to reload dependency {dep}: {e}")

            # Reload the main module
            module = sys.modules[module_name]
            importlib.reload(module)

            return True

        except Exception as e:
            logger.error(f"Failed to reload {module_name}: {e}")
            return False

    def _path_to_module_name(self, file_path: Path) -> Optional[str]:
        """Convert a file path to a module name."""
        try:
            # Remove .py extension
            if file_path.suffix == ".py":
                file_path = file_path.with_suffix("")

            # Try to find the module in sys.modules by matching paths
            for name, module in sys.modules.items():
                if hasattr(module, "__file__") and module.__file__:
                    module_path = Path(module.__file__).with_suffix("")
                    if module_path == file_path:
                        return name

            # If not found, construct from path
            parts = file_path.parts

            # Find common roots
            for root in ["captain", "blocks", "pkgs"]:
                if root in parts:
                    idx = parts.index(root)
                    return ".".join(parts[idx:])

            # Default: use filename
            return file_path.stem

        except Exception as e:
            logger.error(f"Error converting path to module name: {e}")
            return None

    def clear_failed_reloads(self):
        """Clear the list of failed reloads."""
        self._failed_reloads.clear()

    def get_failed_reloads(self) -> Dict[str, str]:
        """Get modules that failed to reload with error messages."""
        return self._failed_reloads.copy()

    def get_reload_stats(self) -> Dict[str, float]:
        """Get statistics about module reloads."""
        return self._reload_times.copy()


# Global instance
_module_reloader = ModuleReloader()


def reload_module(module_name: str, force: bool = False) -> bool:
    """
    Reload a module using the global reloader.

    Args:
        module_name: Name of the module to reload
        force: Force reload even if recently reloaded

    Returns:
        True if reload successful, False otherwise
    """
    return _module_reloader.reload_module(module_name, force)


def reload_module_from_path(file_path: Path) -> Optional[str]:
    """
    Reload a module from its file path.

    Args:
        file_path: Path to the Python file

    Returns:
        Module name if reloaded successfully, None otherwise
    """
    return _module_reloader.reload_module_from_path(file_path)


def reload_block_module(block_path: Path) -> bool:
    """
    Reload a block module specifically.

    Args:
        block_path: Path to the block Python file

    Returns:
        True if reload successful, False otherwise
    """
    return _module_reloader.reload_block_module(block_path)


def get_reloader() -> ModuleReloader:
    """Get the global module reloader instance."""
    return _module_reloader
