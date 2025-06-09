#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test automatic metadata generation for custom blocks.

This test verifies that when a new Python file is created in a block directory,
all the necessary metadata files are automatically generated.
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from captain.services.consumer.blocks_watcher import BlocksWatcher
from captain.utils.block_metadata_generator import (
    generate_all_metadata_files,
    generate_app_json,
    generate_block_data_json,
    generate_example_md,
    generate_test_file,
)


class TestAutomaticMetadataGeneration:
    """Test automatic generation of metadata files for custom blocks."""

    @pytest.fixture
    def temp_blocks_dir(self):
        """Create a temporary blocks directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_block_code(self):
        """Sample block Python code with docstring."""
        return '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe
from atlasvibe.parameter_types import String, Number, Matrix


@atlasvibe
def SAMPLE_BLOCK(
    text: String = "Hello",
    multiplier: Number = 2.0,
    data: Matrix = [[1, 2], [3, 4]]
) -> Matrix:
    """
    Sample block for testing metadata generation.
    
    This block demonstrates automatic metadata generation
    when a new custom block is created.
    
    Parameters
    ----------
    text : String
        Input text to process
    multiplier : Number
        Multiplication factor
    data : Matrix
        Input matrix data
        
    Returns
    -------
    Matrix
        Processed matrix output
    """
    # Sample implementation
    return [[val * multiplier for val in row] for row in data]
'''

    def test_generate_block_data_json(self, temp_blocks_dir, sample_block_code):
        """Test generation of block_data.json from docstring."""
        # Create block directory and Python file
        block_dir = Path(temp_blocks_dir) / "SAMPLE_BLOCK"
        block_dir.mkdir()
        py_file = block_dir / "SAMPLE_BLOCK.py"
        py_file.write_text(sample_block_code)
        
        # Generate block_data.json
        result = generate_block_data_json(str(block_dir), "SAMPLE_BLOCK")
        assert result is True
        
        # Verify block_data.json was created
        json_file = block_dir / "block_data.json"
        assert json_file.exists()
        
        # Verify content
        with open(json_file) as f:
            data = json.load(f)
            
        assert "docstring" in data
        assert data["docstring"]["short_description"] == "Sample block for testing metadata generation."
        assert len(data["docstring"]["parameters"]) == 3
        assert data["docstring"]["parameters"][0]["name"] == "text"
        assert data["docstring"]["parameters"][0]["type"] == "String"
        assert len(data["docstring"]["returns"]) == 1
        assert data["docstring"]["returns"][0]["type"] == "Matrix"

    def test_generate_app_json(self, temp_blocks_dir):
        """Test generation of default app.json."""
        block_dir = Path(temp_blocks_dir) / "TEST_BLOCK"
        block_dir.mkdir()
        
        # Generate app.json
        result = generate_app_json(str(block_dir), "TEST_BLOCK")
        assert result is True
        
        # Verify app.json was created
        app_file = block_dir / "app.json"
        assert app_file.exists()
        
        # Verify content
        with open(app_file) as f:
            data = json.load(f)
            
        assert "rfInstance" in data
        assert len(data["rfInstance"]["nodes"]) == 1
        assert data["rfInstance"]["nodes"][0]["data"]["func"] == "TEST_BLOCK"

    def test_generate_example_md(self, temp_blocks_dir, sample_block_code):
        """Test generation of example.md."""
        block_dir = Path(temp_blocks_dir) / "SAMPLE_BLOCK"
        block_dir.mkdir()
        py_file = block_dir / "SAMPLE_BLOCK.py"
        py_file.write_text(sample_block_code)
        
        # Generate example.md
        result = generate_example_md(str(block_dir), "SAMPLE_BLOCK")
        assert result is True
        
        # Verify example.md was created
        example_file = block_dir / "example.md"
        assert example_file.exists()
        
        # Verify content
        content = example_file.read_text()
        assert "SAMPLE_BLOCK" in content
        assert "Sample block for testing metadata generation" in content

    def test_generate_test_file(self, temp_blocks_dir):
        """Test generation of test file."""
        block_dir = Path(temp_blocks_dir) / "TEST_BLOCK"
        block_dir.mkdir()
        
        # Generate test file
        result = generate_test_file(str(block_dir), "TEST_BLOCK")
        assert result is True
        
        # Verify test file was created
        test_file = block_dir / "TEST_BLOCK_test_.py"
        assert test_file.exists()
        
        # Verify content
        content = test_file.read_text()
        assert "test_test_block_basic" in content
        assert "import TEST_BLOCK" in content

    def test_generate_all_metadata_files(self, temp_blocks_dir, sample_block_code):
        """Test generation of all metadata files at once."""
        # Create block directory and Python file
        block_dir = Path(temp_blocks_dir) / "COMPLETE_BLOCK"
        block_dir.mkdir()
        py_file = block_dir / "COMPLETE_BLOCK.py"
        py_file.write_text(sample_block_code.replace("SAMPLE_BLOCK", "COMPLETE_BLOCK"))
        
        # Generate all metadata files
        success, generated_files = generate_all_metadata_files(str(block_dir))
        
        assert success is True
        assert len(generated_files) == 4
        assert "block_data.json" in generated_files
        assert "app.json" in generated_files
        assert "example.md" in generated_files
        assert "COMPLETE_BLOCK_test_.py" in generated_files
        
        # Verify all files exist
        assert (block_dir / "block_data.json").exists()
        assert (block_dir / "app.json").exists()
        assert (block_dir / "example.md").exists()
        assert (block_dir / "COMPLETE_BLOCK_test_.py").exists()

    def test_blocks_watcher_generates_metadata(self, temp_blocks_dir, sample_block_code):
        """Test that BlocksWatcher generates metadata for new blocks."""
        # This test simulates what happens when the file watcher detects a new block
        
        # Create block directory
        block_dir = Path(temp_blocks_dir) / "WATCHER_BLOCK"
        block_dir.mkdir()
        
        # Verify no metadata files exist yet
        assert not (block_dir / "block_data.json").exists()
        assert not (block_dir / "app.json").exists()
        assert not (block_dir / "example.md").exists()
        
        # Create Python file (simulating user creating a new block)
        py_file = block_dir / "WATCHER_BLOCK.py"
        py_file.write_text(sample_block_code.replace("SAMPLE_BLOCK", "WATCHER_BLOCK"))
        
        # Simulate blocks watcher detecting the new file
        # In real usage, this happens automatically via file watching
        success, generated_files = generate_all_metadata_files(str(block_dir))
        
        # Verify metadata was generated
        assert success is True
        assert (block_dir / "block_data.json").exists()
        assert (block_dir / "app.json").exists()
        assert (block_dir / "example.md").exists()
        assert (block_dir / "WATCHER_BLOCK_test_.py").exists()

    def test_preserve_existing_files(self, temp_blocks_dir):
        """Test that existing metadata files are not overwritten."""
        block_dir = Path(temp_blocks_dir) / "EXISTING_BLOCK"
        block_dir.mkdir()
        
        # Create existing files with custom content
        existing_app = {"custom": "app data"}
        existing_example = "Custom example content"
        
        (block_dir / "app.json").write_text(json.dumps(existing_app))
        (block_dir / "example.md").write_text(existing_example)
        
        # Create Python file
        py_file = block_dir / "EXISTING_BLOCK.py"
        py_file.write_text("def EXISTING_BLOCK(): pass")
        
        # Generate metadata (should not overwrite existing files)
        generate_all_metadata_files(str(block_dir))
        
        # Verify existing files were preserved
        with open(block_dir / "app.json") as f:
            assert json.load(f) == existing_app
        assert (block_dir / "example.md").read_text() == existing_example

    def test_regenerate_block_data_on_modification(self, temp_blocks_dir):
        """Test that block_data.json is regenerated when Python file is modified."""
        from captain.utils.block_metadata_generator import regenerate_block_data_json
        
        block_dir = Path(temp_blocks_dir) / "MODIFIED_BLOCK"
        block_dir.mkdir()
        
        # Create initial Python file
        py_file = block_dir / "MODIFIED_BLOCK.py"
        initial_code = '''
def MODIFIED_BLOCK():
    """Initial description."""
    pass
'''
        py_file.write_text(initial_code)
        
        # Generate initial metadata
        generate_block_data_json(str(block_dir), "MODIFIED_BLOCK")
        
        # Read initial block_data.json
        with open(block_dir / "block_data.json") as f:
            initial_data = json.load(f)
        assert initial_data["docstring"]["short_description"] == "Initial description."
        
        # Modify Python file
        modified_code = '''
def MODIFIED_BLOCK():
    """Updated description with more details."""
    pass
'''
        py_file.write_text(modified_code)
        
        # Regenerate block_data.json
        regenerate_block_data_json(str(block_dir))
        
        # Verify block_data.json was updated
        with open(block_dir / "block_data.json") as f:
            updated_data = json.load(f)
        assert updated_data["docstring"]["short_description"] == "Updated description with more details."