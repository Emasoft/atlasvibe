#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module for automatic metadata generation for custom blocks
# - Generates block_data.json from docstring
# - Generates app.json with default workflow
# - Generates example.md with basic documentation
# - Generates test file with basic structure
#

"""
Automatic metadata generation for custom blocks.

This module handles the automatic generation of metadata files when a custom block
Python file is created or modified. It generates:
- block_data.json (from docstring)
- app.json (default workflow)
- example.md (basic documentation)
- test file (basic test structure)
"""

import ast
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docstring_parser import parse
from captain.utils.logger import logger


def extract_docstring_data(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Extract docstring data from a Python file and return structured JSON data.

    Args:
        file_path: Path to the Python file

    Returns:
        Dictionary with docstring data or None if extraction fails
    """
    try:
        with open(file_path, "r") as f:
            code = f.read()

        tree = ast.parse(code)
        block_name = Path(file_path).stem

        # Find the main function with matching name
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == block_name:
                # Extract docstring
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Str, ast.Constant))
                ):
                    if isinstance(node.body[0].value, ast.Str):
                        docstring = node.body[0].value.s
                    else:
                        docstring = node.body[0].value.value

                    # Parse docstring
                    parsed = parse(docstring)

                    return {
                        "docstring": {
                            "short_description": parsed.short_description or "",
                            "long_description": parsed.long_description or "",
                            "parameters": [
                                {
                                    "name": param.arg_name,
                                    "type": param.type_name,
                                    "description": param.description or "",
                                }
                                for param in parsed.params
                            ],
                            "returns": [
                                {
                                    "name": rtn.return_name or "",
                                    "type": rtn.type_name or "",
                                    "description": rtn.description or "",
                                }
                                for rtn in parsed.many_returns
                            ]
                            if parsed.many_returns
                            else [],
                        }
                    }

    except Exception as e:
        logger.error(f"Failed to extract docstring from {file_path}: {e}")

    return None


def generate_block_data_json(block_dir: str, block_name: str) -> bool:
    """
    Generate block_data.json from the Python file's docstring.

    Args:
        block_dir: Directory containing the block
        block_name: Name of the block

    Returns:
        True if successful, False otherwise
    """
    py_file = os.path.join(block_dir, f"{block_name}.py")
    json_file = os.path.join(block_dir, "block_data.json")

    if not os.path.exists(py_file):
        return False

    # Extract docstring data
    docstring_data = extract_docstring_data(py_file)
    if not docstring_data:
        # Create minimal block_data.json
        docstring_data = {
            "docstring": {
                "short_description": f"{block_name} block",
                "long_description": "",
                "parameters": [],
                "returns": [],
            }
        }

    # Load existing data if present
    existing_data = {}
    if os.path.exists(json_file):
        try:
            with open(json_file, "r") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load existing block_data.json: {e}")

    # Merge with existing data
    existing_data.update(docstring_data)

    # Write block_data.json
    try:
        with open(json_file, "w") as f:
            json.dump(existing_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to write block_data.json: {e}")
        return False


def generate_app_json(block_dir: str, block_name: str) -> bool:
    """
    Generate a default app.json workflow file.

    Args:
        block_dir: Directory containing the block
        block_name: Name of the block

    Returns:
        True if successful, False otherwise
    """
    app_file = os.path.join(block_dir, "app.json")

    # Don't overwrite existing app.json
    if os.path.exists(app_file):
        return True

    # Create a minimal workflow with just the block
    app_data = {
        "rfInstance": {
            "nodes": [
                {
                    "id": "1",
                    "type": "atlasvibe_block",
                    "position": {"x": 250, "y": 250},
                    "data": {
                        "label": block_name,
                        "func": block_name,
                        "path": f"blocks/{block_name}",
                    },
                }
            ],
            "edges": [],
        },
        "textNodes": [],
    }

    try:
        with open(app_file, "w") as f:
            json.dump(app_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to write app.json: {e}")
        return False


def generate_example_md(block_dir: str, block_name: str) -> bool:
    """
    Generate a basic example.md file.

    Args:
        block_dir: Directory containing the block
        block_name: Name of the block

    Returns:
        True if successful, False otherwise
    """
    example_file = os.path.join(block_dir, "example.md")

    # Don't overwrite existing example.md
    if os.path.exists(example_file):
        return True

    # Extract docstring for description
    py_file = os.path.join(block_dir, f"{block_name}.py")
    docstring_data = extract_docstring_data(py_file)

    description = "This block provides custom functionality."
    if docstring_data and docstring_data["docstring"]["short_description"]:
        description = docstring_data["docstring"]["short_description"]

    content = f"""
In this example, the `{block_name}` block is used to demonstrate its functionality.

{description}

## Parameters

Configure the block parameters according to your specific needs.

## Usage

1. Add the `{block_name}` block to your workflow
2. Configure the input parameters
3. Connect to other blocks as needed
4. Run the workflow

## Expected Output

The block will process the input data and produce the expected output based on its implementation.
"""

    try:
        with open(example_file, "w") as f:
            f.write(content.strip())
        return True
    except Exception as e:
        logger.error(f"Failed to write example.md: {e}")
        return False


def generate_test_file(block_dir: str, block_name: str) -> bool:
    """
    Generate a basic test file for the block.

    Args:
        block_dir: Directory containing the block
        block_name: Name of the block

    Returns:
        True if successful, False otherwise
    """
    test_file = os.path.join(block_dir, f"{block_name}_test_.py")

    # Don't overwrite existing test file
    if os.path.exists(test_file):
        return True

    # Get parameter info from docstring if available
    py_file = os.path.join(block_dir, f"{block_name}.py")
    docstring_data = extract_docstring_data(py_file)
    params_info = []
    if docstring_data and docstring_data["docstring"]["parameters"]:
        params_info = docstring_data["docstring"]["parameters"]
    
    content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for {block_name} block."""

import pytest
from atlasvibe.data_container import DataContainer
from {block_name} import {block_name}


class Test{block_name}:
    """Test suite for {block_name} block."""
    
    def test_{block_name.lower()}_basic(self):
        """Test basic functionality of {block_name}."""
        # Test with default parameters
        result = {block_name}()
        assert result is not None
        assert isinstance(result, DataContainer)
    
    def test_{block_name.lower()}_with_parameters(self):
        """Test {block_name} with various parameters."""
        # Test with different parameter combinations
        # Modify these tests based on your block's actual parameters
        '''
    
    # Add parameter-specific tests if we have parameter info
    if params_info:
        for param in params_info:
            param_name = param["name"]
            param_type = param["type"]
            content += f'''
        # Test with {param_name} parameter
        test_{param_name} = DataContainer({param_type}())  # Create appropriate test value
        result = {block_name}({param_name}=test_{param_name})
        assert result is not None
        '''
    
    content += f'''
    
    def test_{block_name.lower()}_error_handling(self):
        """Test {block_name} error handling."""
        # Test with invalid inputs
        with pytest.raises(Exception):
            # Add specific error case based on your block's logic
            {block_name}(invalid_param="invalid_value")
    
    def test_{block_name.lower()}_output_type(self):
        """Test {block_name} output type."""
        result = {block_name}()
        # Verify the output is wrapped in DataContainer
        assert isinstance(result, DataContainer)
        # Add more specific type checks based on expected output


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    try:
        with open(test_file, "w") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write test file: {e}")
        return False


def generate_all_metadata_files(block_dir: str) -> Tuple[bool, List[str]]:
    """
    Generate all metadata files for a custom block.

    This function is called when a new Python file is detected in a block directory.
    It generates:
    - block_data.json (from docstring)
    - app.json (default workflow)
    - example.md (basic documentation)
    - test file (basic test structure)

    Args:
        block_dir: Directory containing the block

    Returns:
        Tuple of (success, list of generated files)
    """
    block_name = os.path.basename(block_dir)
    py_file = os.path.join(block_dir, f"{block_name}.py")

    if not os.path.exists(py_file):
        return False, []

    generated_files = []
    success = True

    # Generate block_data.json
    if generate_block_data_json(block_dir, block_name):
        generated_files.append("block_data.json")
    else:
        success = False

    # Generate app.json
    if generate_app_json(block_dir, block_name):
        generated_files.append("app.json")
    else:
        success = False

    # Generate example.md
    if generate_example_md(block_dir, block_name):
        generated_files.append("example.md")
    else:
        success = False

    # Generate test file
    if generate_test_file(block_dir, block_name):
        generated_files.append(f"{block_name}_test_.py")
    else:
        success = False

    return success, generated_files


def regenerate_block_data_json(block_dir: str) -> bool:
    """
    Regenerate only block_data.json when a Python file is modified.

    This preserves other metadata files and only updates the docstring data.

    Args:
        block_dir: Directory containing the block

    Returns:
        True if successful, False otherwise
    """
    block_name = os.path.basename(block_dir)
    return generate_block_data_json(block_dir, block_name)

