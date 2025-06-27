#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate block metadata for all blocks
"""

import json
from pathlib import Path
from typing import List, Tuple
import docstring_parser

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE FILE:
# - Initial creation of block metadata validator
# - Validates block_data.json matches Python docstrings
# - Checks for required metadata files
# - Reports validation errors with details
#


def validate_block_metadata(block_path: Path) -> Tuple[bool, List[str]]:
    """Validate metadata for a single block.

    Args:
        block_path: Path to block directory

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    block_name = block_path.name

    # Check for required files
    py_file = block_path / f"{block_name}.py"
    json_file = block_path / "block_data.json"

    if not py_file.exists():
        errors.append(f"Missing Python file: {py_file}")
        return False, errors

    if not json_file.exists():
        errors.append(f"Missing block_data.json: {json_file}")
        return False, errors

    # Parse Python file
    try:
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract docstring
        import ast

        tree = ast.parse(content)

        # Find the main function with @atlasvibe decorator
        main_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    decorator_name = ""
                    if isinstance(decorator, ast.Name):
                        decorator_name = decorator.id
                    elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                        decorator_name = decorator.func.id

                    if decorator_name in ["atlasvibe", "atlasvibe_node"]:
                        main_func = node
                        break
                if main_func:
                    break

        if not main_func:
            errors.append("No function with @atlasvibe decorator found")
            return False, errors

        # Parse docstring
        docstring = ast.get_docstring(main_func)
        if not docstring:
            errors.append("No docstring found in main function")

    except Exception as e:
        errors.append(f"Error parsing Python file: {e}")
        return False, errors

    # Load and validate JSON
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        if "docstring" not in json_data:
            errors.append("Missing 'docstring' field in block_data.json")

        # Validate docstring field structure
        if "docstring" in json_data:
            ds = json_data["docstring"]
            if not isinstance(ds, dict):
                errors.append("'docstring' field must be a dictionary")
            else:
                # Check required fields
                if "short_description" not in ds:
                    errors.append("Missing 'short_description' in docstring")
                if "parameters" not in ds:
                    errors.append("Missing 'parameters' in docstring")
                elif not isinstance(ds["parameters"], list):
                    errors.append("'parameters' must be a list")

    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in block_data.json: {e}")
    except Exception as e:
        errors.append(f"Error reading block_data.json: {e}")

    # Compare docstring with JSON if both exist
    if docstring and "docstring" in json_data:
        try:
            parsed_doc = docstring_parser.parse(docstring)
            json_doc = json_data["docstring"]

            # Compare descriptions
            if parsed_doc.short_description != json_doc.get("short_description"):
                errors.append("Docstring short_description doesn't match JSON")

            # Compare parameters
            json_params = {p["name"]: p for p in json_doc.get("parameters", [])}
            for param in parsed_doc.params:
                if param.arg_name not in json_params:
                    errors.append(f"Parameter '{param.arg_name}' in docstring not found in JSON")

        except Exception as e:
            errors.append(f"Error comparing docstring with JSON: {e}")

    return len(errors) == 0, errors


def validate_all_blocks() -> bool:
    """Validate metadata for all blocks.

    Returns:
        True if all blocks are valid, False otherwise
    """
    blocks_dir = Path(__file__).parent.parent.parent / "blocks"
    if not blocks_dir.exists():
        print(f"❌ Blocks directory not found: {blocks_dir}")
        return False

    all_valid = True
    total_blocks = 0
    valid_blocks = 0

    # Find all block directories
    for category_dir in blocks_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        for subcategory_dir in category_dir.iterdir():
            if not subcategory_dir.is_dir() or subcategory_dir.name.startswith("."):
                continue

            for block_dir in subcategory_dir.iterdir():
                if not block_dir.is_dir() or block_dir.name.startswith("."):
                    continue

                total_blocks += 1
                is_valid, errors = validate_block_metadata(block_dir)

                if is_valid:
                    valid_blocks += 1
                else:
                    all_valid = False
                    print(f"\n❌ {block_dir.relative_to(blocks_dir)}:")
                    for error in errors:
                        print(f"   - {error}")

    # Summary
    print("\n📊 Validation Summary:")
    print(f"   Total blocks: {total_blocks}")
    print(f"   Valid blocks: {valid_blocks}")
    print(f"   Invalid blocks: {total_blocks - valid_blocks}")

    if all_valid:
        print("✅ All blocks have valid metadata!")
    else:
        print("❌ Some blocks have invalid metadata")

    return all_valid


def main():
    """Main entry point."""
    import sys

    success = validate_all_blocks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
