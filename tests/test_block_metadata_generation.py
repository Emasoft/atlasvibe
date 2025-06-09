#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created comprehensive test for block metadata generation
# - Tests generation of block_data.json from Python docstring
# - Tests the complete metadata file structure
# - Demonstrates what files are generated and what must be created manually
# 

"""Test block metadata generation from Python source files.

This test demonstrates how AtlasVibe generates metadata files from block Python code:
1. block_data.json - Generated from docstring
2. app.json - Must be created manually (contains example workflow)
3. example.md - Must be created manually (describes the example)
4. *_test.py - Must be created manually (unit tests)
"""

import pytest
import tempfile
import json
import ast
import os
from pathlib import Path
from docstring_parser import parse

from captain.utils.manifest.build_manifest import create_manifest
from cli.utils.generate_docstring_json import generate_docstring_json


class TestBlockMetadataGeneration:
    """Test the generation of metadata files from block Python code."""
    
    @pytest.fixture
    def test_block_dir(self):
        """Create a test block directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create block directory structure like blueprint blocks
            block_base = Path(tmpdir) / "blocks" / "TEST_CATEGORY" / "TEST_SUBCATEGORY" / "TEST_BLOCK"
            block_base.mkdir(parents=True)
            
            yield block_base
    
    def test_reproduce_append_block_structure(self, test_block_dir):
        """Test reproducing the APPEND block metadata structure."""
        
        # Step 1: Create the Python source file (this is the only required file)
        py_file = test_block_dir / "TEST_BLOCK.py"
        py_file.write_text("""from atlasvibe import atlasvibe, OrderedPair, Matrix, DataFrame, Vector, Scalar


@atlasvibe
def TEST_BLOCK(
    primary_dp: OrderedPair | Matrix | DataFrame | Scalar | Vector | None,
    secondary_dp: OrderedPair | Matrix | DataFrame | Scalar | Vector,
) -> OrderedPair | Matrix | DataFrame | Vector | Scalar:
    \"\"\"Append a single data point to an array.

    The large array must be passed to the bottom "array" connection.

    For ordered pair, the single point must have a shape of 1 (or (1,)).

    Parameters
    ----------
    primary_dp : OrderedPair|Vector|Scalar|Matrix|DataFrame|None
        Input that ends up "on top" of the resulting DataContainer.
    secondary_dp : OrderedPair|Vector|Scalar|Matrix|DataFrame
        Input that ends up "on the bottom" of the resulting DataContainer.

    Returns
    -------
    OrderedPair, Matrix, DataFrame, Vector
    \"\"\"

    if isinstance(primary_dp, OrderedPair) and isinstance(secondary_dp, OrderedPair):
        x0 = primary_dp.x
        y0 = primary_dp.y
        x1 = secondary_dp.x
        y1 = secondary_dp.y
        x = append(x0, x1)
        y = append(y0, y1)
        return OrderedPair(x=x, y=y)
    
    # ... other implementations
    return primary_dp
""")
        
        # Step 2: Generate block_data.json from the docstring
        self._generate_block_data_json(py_file)
        
        # Verify block_data.json was created
        block_data_file = test_block_dir / "block_data.json"
        assert block_data_file.exists()
        
        # Read and verify the content
        with open(block_data_file) as f:
            block_data = json.load(f)
        
        print("\n=== Generated block_data.json ===")
        print(json.dumps(block_data, indent=2))
        
        # Verify the structure matches expected format
        assert "docstring" in block_data
        docstring = block_data["docstring"]
        assert "short_description" in docstring
        assert "long_description" in docstring
        assert "parameters" in docstring
        assert "returns" in docstring
        
        # Verify parameters
        assert len(docstring["parameters"]) == 2
        param1 = docstring["parameters"][0]
        assert param1["name"] == "primary_dp"
        assert param1["type"] == "OrderedPair|Vector|Scalar|Matrix|DataFrame|None"
        assert "on top" in param1["description"]
        
        # Step 3: Create manifest using the captain utilities
        manifest = create_manifest(str(py_file))
        
        print("\n=== Generated Manifest ===")
        print(json.dumps(manifest, indent=2))
        
        # Verify manifest structure
        assert manifest["name"] == "TEST_BLOCK"
        assert manifest["key"] == "TEST_BLOCK"
        assert "inputs" in manifest
        assert len(manifest["inputs"]) == 2
        assert manifest["inputs"][0]["name"] == "primary_dp"
        assert manifest["inputs"][1]["name"] == "secondary_dp"
        
        # Step 4: Document what files must be created manually
        manual_files = {
            "app.json": self._create_example_app_json(),
            "example.md": self._create_example_md(),
            "TEST_BLOCK_test.py": self._create_test_file()
        }
        
        print("\n=== Files that must be created manually ===")
        for filename, content in manual_files.items():
            print(f"\n{filename}:")
            print("-" * 40)
            if filename.endswith('.json'):
                print(json.dumps(content, indent=2)[:200] + "...")
            else:
                print(content[:200] + "...")
            
            # Create the files
            if filename.endswith('.json'):
                (test_block_dir / filename).write_text(json.dumps(content, indent=2))
            else:
                (test_block_dir / filename).write_text(content)
        
        # Step 5: Verify complete block structure
        expected_files = [
            "TEST_BLOCK.py",
            "block_data.json",
            "app.json",
            "example.md",
            "TEST_BLOCK_test.py"
        ]
        
        actual_files = [f.name for f in test_block_dir.iterdir() if f.is_file()]
        
        print("\n=== Complete Block Structure ===")
        for file in expected_files:
            exists = file in actual_files
            print(f"{file}: {'✅' if exists else '❌'}")
        
        # All files should exist
        assert all(file in actual_files for file in expected_files)
    
    def _generate_block_data_json(self, py_file: Path):
        """Generate block_data.json from Python file docstring."""
        # Read the Python file
        with open(py_file, 'r') as f:
            code = f.read()
        
        # Parse the AST
        tree = ast.parse(code)
        
        # Find the function with matching name
        block_name = py_file.stem
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == block_name:
                # Extract docstring
                if (node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Str)):
                    
                    docstring = node.body[0].value.s
                    
                    # Parse docstring
                    parsed = parse(docstring)
                    
                    # Build JSON data
                    docstring_data = {
                        "docstring": {
                            "long_description": parsed.long_description or "",
                            "short_description": parsed.short_description or "",
                            "parameters": [
                                {
                                    "name": param.arg_name,
                                    "type": param.type_name,
                                    "description": param.description,
                                }
                                for param in parsed.params
                            ],
                            "returns": [
                                {
                                    "name": rtn.return_name,
                                    "type": rtn.type_name,
                                    "description": rtn.description,
                                }
                                for rtn in parsed.many_returns
                            ] if parsed.many_returns else [
                                {
                                    "name": None,
                                    "type": parsed.returns.type_name if parsed.returns else None,
                                    "description": parsed.returns.description if parsed.returns else None
                                }
                            ]
                        }
                    }
                    
                    # Write to block_data.json
                    output_file = py_file.parent / "block_data.json"
                    with open(output_file, 'w') as f:
                        json.dump(docstring_data, f, indent=2)
                    
                    return docstring_data
        
        raise ValueError(f"Function {block_name} not found in {py_file}")
    
    def _create_example_app_json(self):
        """Create an example app.json structure."""
        # This is a simplified version - real app.json files contain complete workflows
        return {
            "rfInstance": {
                "nodes": [
                    {
                        "id": "TEST_BLOCK-123",
                        "type": "TEST_CATEGORY",
                        "data": {
                            "id": "TEST_BLOCK-123",
                            "label": "TEST_BLOCK",
                            "func": "TEST_BLOCK",
                            "type": "TEST_CATEGORY",
                            "ctrls": {},
                            "inputs": [
                                {
                                    "name": "primary_dp",
                                    "id": "primary_dp",
                                    "type": "OrderedPair|Matrix|DataFrame|Scalar|Vector",
                                    "desc": "Input that ends up \"on top\" of the resulting DataContainer.",
                                    "multiple": False
                                },
                                {
                                    "name": "secondary_dp",
                                    "id": "secondary_dp",
                                    "type": "OrderedPair|Matrix|DataFrame|Scalar|Vector",
                                    "desc": "Input that ends up \"on the bottom\" of the resulting DataContainer.",
                                    "multiple": False
                                }
                            ],
                            "outputs": [
                                {
                                    "name": "default",
                                    "id": "default",
                                    "type": "OrderedPair|Matrix|DataFrame|Vector|Scalar",
                                    "desc": None
                                }
                            ],
                            "path": "TEST_CATEGORY/TEST_SUBCATEGORY/TEST_BLOCK/TEST_BLOCK.py"
                        },
                        "position": {"x": 0, "y": 0},
                        "width": 216,
                        "height": 198
                    }
                ],
                "edges": []
            },
            "textNodes": []
        }
    
    def _create_example_md(self):
        """Create an example.md file."""
        return """In this example, `TEST_BLOCK` demonstrates appending data containers.

The block takes two inputs and combines them according to their types.

This is useful for building up data arrays in loops.
"""
    
    def _create_test_file(self):
        """Create a test file for the block."""
        return """from functools import wraps
from unittest.mock import patch

import numpy
from atlasvibe import DataContainer


def mock_atlasvibe_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


# Patch the atlasvibe decorator
patch("atlasvibe.atlasvibe", mock_atlasvibe_decorator).start()


def test_TEST_BLOCK():
    import TEST_BLOCK
    
    # Test with OrderedPair
    element_a = DataContainer(
        type="OrderedPair", x=numpy.array([1, 2]), y=numpy.array([3, 4])
    )
    element_b = DataContainer(
        type="OrderedPair", x=numpy.array([5]), y=numpy.array([6])
    )
    
    result = TEST_BLOCK.TEST_BLOCK(element_a, element_b)
    
    assert len(result.x) == 3
    assert len(result.y) == 3
"""
    
    def test_metadata_regeneration_on_change(self, test_block_dir):
        """Test that metadata is regenerated when the Python file changes."""
        
        # Create initial Python file
        py_file = test_block_dir / "CHANGING_BLOCK.py"
        py_file.write_text("""from atlasvibe import atlasvibe

@atlasvibe
def CHANGING_BLOCK(x: int = 10) -> int:
    \"\"\"Simple block that doubles a value.
    
    Parameters
    ----------
    x : int
        Input value to double
        
    Returns
    -------
    int
        The doubled value
    \"\"\"
    return x * 2
""")
        
        # Generate initial metadata
        self._generate_block_data_json(py_file)
        initial_manifest = create_manifest(str(py_file))
        
        print("\n=== Initial Manifest ===")
        print(f"Parameters: {list(initial_manifest['parameters'].keys())}")
        
        # Modify the Python file
        py_file.write_text("""from atlasvibe import atlasvibe

@atlasvibe(deps={"numpy": ">=1.20.0"})
def CHANGING_BLOCK(x: int = 10, multiplier: int = 3, offset: float = 0.5) -> float:
    \"\"\"Enhanced block with more parameters.
    
    Now supports custom multiplication and offset.
    
    Parameters
    ----------
    x : int
        Input value
    multiplier : int  
        Multiplication factor
    offset : float
        Value to add after multiplication
        
    Returns
    -------
    float
        The result of (x * multiplier) + offset
    \"\"\"
    import numpy as np
    return float(x * multiplier + offset)
""")
        
        # Regenerate metadata
        self._generate_block_data_json(py_file)
        updated_manifest = create_manifest(str(py_file))
        
        print("\n=== Updated Manifest ===")
        print(f"Parameters: {list(updated_manifest['parameters'].keys())}")
        print(f"Dependencies: {updated_manifest.get('pip_dependencies', [])}")
        
        # Verify changes
        assert len(updated_manifest['parameters']) == 3
        assert 'multiplier' in updated_manifest['parameters']
        assert 'offset' in updated_manifest['parameters']
        assert updated_manifest['parameters']['multiplier']['default'] == 3
        assert updated_manifest['parameters']['offset']['default'] == 0.5
        
        # Verify dependencies were detected
        assert 'pip_dependencies' in updated_manifest
        assert len(updated_manifest['pip_dependencies']) == 1
        assert updated_manifest['pip_dependencies'][0]['name'] == 'numpy'
    
    def test_complete_metadata_flow(self):
        """Document the complete metadata generation flow."""
        
        flow = {
            "1. User creates Python file": {
                "action": "Create BLOCK_NAME.py with @atlasvibe decorator",
                "generated": "Nothing yet",
                "manual": "Must write the Python code"
            },
            "2. Run manifest generation": {
                "action": "create_manifest() extracts metadata from AST",
                "generated": "In-memory manifest with inputs/outputs/parameters",
                "manual": "Nothing"
            },
            "3. Run docstring generation": {
                "action": "generate_docstring_json() extracts from docstring",
                "generated": "block_data.json with structured documentation",
                "manual": "Must write proper docstring in NumPy format"
            },
            "4. Create example workflow": {
                "action": "User creates example usage",
                "generated": "Nothing",
                "manual": "app.json - complete workflow demonstrating the block"
            },
            "5. Write example description": {
                "action": "User documents the example",
                "generated": "Nothing", 
                "manual": "example.md - explains what the example does"
            },
            "6. Create unit tests": {
                "action": "User writes tests",
                "generated": "Nothing",
                "manual": "BLOCK_NAME_test.py - unit tests for the block"
            },
            "7. File watcher detects changes": {
                "action": "BlocksWatcher monitors file system",
                "generated": "WebSocket 'manifest_update' events",
                "manual": "Nothing"
            },
            "8. Frontend fetches updates": {
                "action": "Frontend calls /blocks/manifest/",
                "generated": "Complete manifest with all blocks",
                "manual": "Nothing"
            }
        }
        
        print("\n=== Complete Metadata Generation Flow ===")
        for step, details in flow.items():
            print(f"\n{step}")
            print(f"  Action: {details['action']}")
            print(f"  Generated: {details['generated']}")
            print(f"  Manual: {details['manual']}")
        
        # Summary
        print("\n=== Summary ===")
        print("Automatically generated files:")
        print("  - block_data.json (from docstring)")
        print("  - In-memory manifest (from AST)")
        print("\nManually created files:")
        print("  - app.json (example workflow)")
        print("  - example.md (example description)")
        print("  - *_test.py (unit tests)")
        print("\nNOTE: __pycache__ is created by Python when importing modules")
        
        assert True  # Documentation test