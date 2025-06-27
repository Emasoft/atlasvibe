"""
Utilities for block testing to ensure cross-platform compatibility.
"""

import sys
from pathlib import Path
import importlib.util


def import_block_module(block_name: str, test_file_path: str):
    """
    Import a block module dynamically, handling cross-platform path issues.

    Args:
        block_name: Name of the block module to import
        test_file_path: Path to the test file (usually __file__)

    Returns:
        The imported module

    Example:
        # In a test file
        from blocks.block_test_utils import import_block_module
        MY_BLOCK = import_block_module("MY_BLOCK", __file__)
    """
    test_dir = Path(test_file_path).parent
    module_path = test_dir / f"{block_name}.py"

    if not module_path.exists():
        raise ImportError(f"Block module {block_name}.py not found in {test_dir}")

    # Use importlib to load the module
    spec = importlib.util.spec_from_file_location(block_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load module spec for {block_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[block_name] = module
    spec.loader.exec_module(module)

    return module


def ensure_block_importable(test_file_path: str):
    """
    Ensure the block in the same directory as the test can be imported.

    Args:
        test_file_path: Path to the test file (usually __file__)
    """
    test_dir = Path(test_file_path).parent

    # Add the test directory to sys.path if not already there
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))

    # Also add parent directories up to blocks/ to handle relative imports
    current_dir = test_dir
    while current_dir.name != "blocks" and current_dir.parent != current_dir:
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        current_dir = current_dir.parent
