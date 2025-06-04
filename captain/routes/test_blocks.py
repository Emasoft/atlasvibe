#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial test implementation for block update functionality
# - Tests for update_block_code endpoint following TDD methodology
# 

"""Tests for the blocks API endpoints.

This module tests the block-related API endpoints, particularly
the update_block_code functionality for custom blocks.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock
import tempfile
import shutil
import sys

# Mock the atlasvibe module before importing blocks
sys.modules['atlasvibe'] = Mock()
sys.modules['atlasvibe.utils'] = Mock()

from fastapi import FastAPI

# Create test app
app = FastAPI()


class TestUpdateBlockCode:
    """Test cases for the update_block_code endpoint."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with custom blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project.atlasvibe"
            project_path.touch()
            
            # Create custom blocks directory
            blocks_dir = Path(tmpdir) / "atlasvibe_blocks" / "CUSTOM_BLOCK"
            blocks_dir.mkdir(parents=True)
            
            # Create a test block file
            block_file = blocks_dir / "CUSTOM_BLOCK.py"
            block_file.write_text("""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def CUSTOM_BLOCK(x: int = 1) -> int:
    '''A custom test block.
    
    Parameters:
        x: Input value
        
    Returns:
        int: The input multiplied by 2
    '''
    return x * 2
""")
            
            yield {
                "project_path": str(project_path),
                "block_file": str(block_file),
                "blocks_dir": str(blocks_dir)
            }
    
    def test_update_block_code_success(self, temp_project_dir):
        """Test successful update of custom block code."""
        new_content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def CUSTOM_BLOCK(x: int = 1) -> int:
    '''A custom test block - updated.
    
    Parameters:
        x: Input value
        
    Returns:
        int: The input multiplied by 3
    '''
    return x * 3
"""
        
        with patch('captain.routes.blocks.process_block_directory') as mock_process:
            mock_process.return_value = {
                "name": "CUSTOM_BLOCK",
                "type": "default",
                "inputs": [{"name": "x", "type": "int", "default": 1}],
                "outputs": [{"name": "output", "type": "int"}]
            }
            
            response = client.post("/blocks/update-code/", json={
                "block_path": temp_project_dir["block_file"],
                "content": new_content,
                "project_path": temp_project_dir["project_path"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "CUSTOM_BLOCK"
            assert data["path"] == temp_project_dir["blocks_dir"]
            
            # Verify file was updated
            with open(temp_project_dir["block_file"], "r") as f:
                assert "multiplied by 3" in f.read()
    
    def test_update_block_code_blueprint_forbidden(self):
        """Test that updating blueprint blocks is forbidden."""
        response = client.post("/blocks/update-code/", json={
            "block_path": "/blocks/MATH/ADD/ADD.py",
            "content": "new content",
            "project_path": "/project.atlasvibe"
        })
        
        assert response.status_code == 403
        assert "Can only edit custom project blocks" in response.json()["detail"]
    
    def test_update_block_code_invalid_project_path(self, temp_project_dir):
        """Test that invalid project paths are rejected."""
        response = client.post("/blocks/update-code/", json={
            "block_path": temp_project_dir["block_file"],
            "content": "new content",
            "project_path": "/invalid/path"
        })
        
        assert response.status_code == 422
        assert "Invalid project path" in response.json()["detail"]
    
    def test_update_block_code_nonexistent_file(self):
        """Test handling of nonexistent block files."""
        response = client.post("/blocks/update-code/", json={
            "block_path": "/nonexistent/atlasvibe_blocks/BLOCK/BLOCK.py",
            "content": "new content",
            "project_path": "/project.atlasvibe"
        })
        
        assert response.status_code == 404
        assert "Block file not found" in response.json()["detail"]
    
    def test_update_block_code_manifest_generation_failure(self, temp_project_dir):
        """Test rollback when manifest generation fails."""
        original_content = Path(temp_project_dir["block_file"]).read_text()
        new_content = "invalid python code that will fail manifest generation"
        
        with patch('captain.routes.blocks.process_block_directory') as mock_process:
            mock_process.return_value = None  # Simulate manifest generation failure
            
            response = client.post("/blocks/update-code/", json={
                "block_path": temp_project_dir["block_file"],
                "content": new_content,
                "project_path": temp_project_dir["project_path"]
            })
            
            assert response.status_code == 500
            assert "Failed to regenerate manifest" in response.json()["detail"]
            
            # Verify file was rolled back to original content
            assert Path(temp_project_dir["block_file"]).read_text() == original_content
    
    def test_update_block_code_preserves_backup_on_error(self, temp_project_dir):
        """Test that original content is preserved when an error occurs."""
        original_content = Path(temp_project_dir["block_file"]).read_text()
        
        with patch('captain.routes.blocks.Path.write_text') as mock_write:
            # First call succeeds (writing new content)
            # Second call fails (simulating error during processing)
            mock_write.side_effect = [None, Exception("Write error")]
            
            response = client.post("/blocks/update-code/", json={
                "block_path": temp_project_dir["block_file"],
                "content": "new content",
                "project_path": temp_project_dir["project_path"]
            })
            
            assert response.status_code == 500