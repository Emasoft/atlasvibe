#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Real API integration test for block update functionality
# - Tests the actual API endpoint using FastAPI test client
# - No mocks, uses real file operations
# 

"""API integration tests for block update functionality."""

import pytest
import tempfile
import json
from pathlib import Path
from fastapi.testclient import TestClient
import sys
import os

# Add captain to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from captain.main import app

client = TestClient(app)


class TestBlockUpdateAPI:
    """Test the block update API endpoint with real file operations."""
    
    @pytest.fixture
    def project_setup(self):
        """Create a real project structure for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            
            project_file = project_dir / "test_project.atlasvibe"
            project_file.write_text(json.dumps({
                "version": "0.1.0",
                "nodes": [],
                "edges": []
            }))
            
            # Create custom blocks directory
            blocks_dir = project_dir / "atlasvibe_blocks"
            blocks_dir.mkdir()
            
            # Create a test block
            block_dir = blocks_dir / "TEST_BLOCK"
            block_dir.mkdir()
            
            (block_dir / "__init__.py").write_text("")
            
            block_file = block_dir / "TEST_BLOCK.py"
            block_file.write_text("""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 1) -> int:
    '''Test block for testing.
    
    Parameters:
        x: Input value
        
    Returns:
        int: Doubled value
    '''
    return x * 2
""")
            
            (block_dir / "app.json").write_text(json.dumps({
                "name": "TEST_BLOCK",
                "type": "default"
            }))
            
            (block_dir / "block_data.json").write_text(json.dumps({
                "inputs": [{"name": "x", "type": "int", "default": 1}],
                "outputs": [{"name": "output", "type": "int"}]
            }))
            
            yield {
                "project_file": str(project_file),
                "block_file": str(block_file),
                "block_dir": block_dir
            }
    
    def test_update_block_code_endpoint(self, project_setup):
        """Test the /blocks/update-code/ endpoint."""
        new_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 1) -> int:
    '''Test block for testing.
    
    Parameters:
        x: Input value
        
    Returns:
        int: Tripled value
    '''
    return x * 3  # Changed from x * 2
"""
        
        response = client.post(
            "/blocks/update-code/",
            json={
                "block_path": project_setup["block_file"],
                "content": new_code,
                "project_path": project_setup["project_file"]
            }
        )
        
        # Should succeed
        assert response.status_code == 200
        
        # Check file was updated
        with open(project_setup["block_file"], 'r') as f:
            actual_content = f.read()
        
        assert actual_content == new_code
        assert "x * 3" in actual_content
        
        # Response should contain manifest data
        data = response.json()
        assert data.get("name") == "TEST_BLOCK"
        assert "path" in data
    
    def test_update_non_custom_block_rejected(self):
        """Test that blueprint blocks cannot be updated."""
        response = client.post(
            "/blocks/update-code/",
            json={
                "block_path": "/blocks/MATH/ADD/ADD.py",
                "content": "# new content",
                "project_path": "/project/test.atlasvibe"
            }
        )
        
        assert response.status_code == 403
        assert "custom project blocks" in response.json()["detail"]
    
    def test_update_invalid_project_path(self, project_setup):
        """Test that invalid project paths are rejected."""
        response = client.post(
            "/blocks/update-code/",
            json={
                "block_path": project_setup["block_file"],
                "content": "# new content",
                "project_path": "/invalid/path.txt"
            }
        )
        
        assert response.status_code == 422
        assert "Invalid project path" in response.json()["detail"]
    
    def test_update_nonexistent_block(self):
        """Test handling of non-existent block files."""
        response = client.post(
            "/blocks/update-code/",
            json={
                "block_path": "/nonexistent/atlasvibe_blocks/BLOCK/BLOCK.py",
                "content": "# content",
                "project_path": "/project/test.atlasvibe"
            }
        )
        
        assert response.status_code == 404
        assert "Block file not found" in response.json()["detail"]