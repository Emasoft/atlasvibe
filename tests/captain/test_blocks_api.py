#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - API integration tests for blocks endpoints
# - Tests the actual endpoint behavior with mock dependencies
# 

"""API integration tests for blocks endpoints."""

import pytest
from pathlib import Path
import tempfile
import json
from unittest.mock import patch, MagicMock, ANY

from fastapi.testclient import TestClient
from fastapi import FastAPI

# Mock modules before imports
import sys
sys.modules['atlasvibe'] = MagicMock()
sys.modules['atlasvibe.utils'] = MagicMock()
sys.modules['captain.internal.manager'] = MagicMock()
sys.modules['captain.internal.wsmanager'] = MagicMock()
sys.modules['captain.utils.manifest.generate_manifest'] = MagicMock()
sys.modules['captain.utils.blocks_metadata'] = MagicMock()
sys.modules['captain.utils.import_blocks'] = MagicMock()
sys.modules['captain.utils.blocks_path'] = MagicMock()
sys.modules['captain.utils.manifest.build_manifest'] = MagicMock()
sys.modules['captain.utils.project_structure'] = MagicMock()

# Import after mocking
from captain.routes import blocks

# Create test client
app = FastAPI()
app.include_router(blocks.router)
client = TestClient(app)


class TestBlocksAPI:
    """Test the blocks API endpoints."""
    
    @pytest.fixture
    def temp_block_file(self):
        """Create a temporary block file."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            prefix='test_block_',
            delete=False,
            dir=tempfile.gettempdir()
        ) as f:
            # Make path include "atlasvibe_blocks"
            temp_dir = Path(f.name).parent / "atlasvibe_blocks" / "TEST_BLOCK"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            block_file = temp_dir / "TEST_BLOCK.py"
            block_file.write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 1) -> int:
    return x * 2
""")
            yield str(block_file)
            
            # Cleanup
            if block_file.exists():
                block_file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
    
    @patch('captain.routes.blocks.process_block_directory')
    @patch('captain.routes.blocks.logger')
    def test_update_block_code_success(self, mock_logger, mock_process, temp_block_file):
        """Test successful block code update."""
        # Setup mock
        mock_process.return_value = {
            "name": "TEST_BLOCK",
            "type": "default",
            "func": "TEST_BLOCK",
            "inputs": [],
            "outputs": []
        }
        
        # Make request
        response = client.post("/blocks/update-code/", json={
            "block_path": temp_block_file,
            "content": "# Updated content",
            "project_path": "/test/project.atlasvibe"
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_BLOCK"
        assert "path" in data
        
        # Verify file was updated
        with open(temp_block_file, 'r') as f:
            assert f.read() == "# Updated content"
        
        # Verify process_block_directory was called
        mock_process.assert_called_once()
        
        # Verify logging
        mock_logger.info.assert_called()
    
    def test_update_block_code_not_custom_block(self):
        """Test that updating non-custom blocks is forbidden."""
        response = client.post("/blocks/update-code/", json={
            "block_path": "/blocks/MATH/ADD/ADD.py",
            "content": "# New content",
            "project_path": "/test/project.atlasvibe"
        })
        
        assert response.status_code == 403
        assert "custom project blocks" in response.json()["detail"]
    
    def test_update_block_code_invalid_project_path(self):
        """Test that invalid project paths are rejected."""
        response = client.post("/blocks/update-code/", json={
            "block_path": "/test/atlasvibe_blocks/BLOCK/BLOCK.py",
            "content": "# New content",
            "project_path": "/test/invalid_project"
        })
        
        assert response.status_code == 422
        assert "Invalid project path" in response.json()["detail"]
    
    def test_update_block_code_missing_file(self):
        """Test handling of missing block files."""
        response = client.post("/blocks/update-code/", json={
            "block_path": "/nonexistent/atlasvibe_blocks/BLOCK/BLOCK.py",
            "content": "# New content",
            "project_path": "/test/project.atlasvibe"
        })
        
        assert response.status_code == 404
        assert "Block file not found" in response.json()["detail"]
    
    @patch('captain.routes.blocks.process_block_directory')
    def test_update_block_code_manifest_failure(self, mock_process, temp_block_file):
        """Test rollback when manifest generation fails."""
        # Read original content
        with open(temp_block_file, 'r') as f:
            original_content = f.read()
        
        # Setup mock to fail
        mock_process.return_value = None
        
        # Make request
        response = client.post("/blocks/update-code/", json={
            "block_path": temp_block_file,
            "content": "# This should be rolled back",
            "project_path": "/test/project.atlasvibe"
        })
        
        # Verify error response
        assert response.status_code == 500
        assert "Failed to regenerate manifest" in response.json()["detail"]
        
        # Verify file was rolled back
        with open(temp_block_file, 'r') as f:
            assert f.read() == original_content
    
    @patch('captain.routes.blocks.process_block_directory')
    def test_update_block_code_exception_rollback(self, mock_process, temp_block_file):
        """Test rollback on unexpected exceptions."""
        # Read original content
        with open(temp_block_file, 'r') as f:
            original_content = f.read()
        
        # Setup mock to raise exception
        mock_process.side_effect = Exception("Unexpected error")
        
        # Make request
        response = client.post("/blocks/update-code/", json={
            "block_path": temp_block_file,
            "content": "# This should be rolled back",
            "project_path": "/test/project.atlasvibe"
        })
        
        # Verify error response
        assert response.status_code == 500
        
        # Verify file was rolled back
        with open(temp_block_file, 'r') as f:
            assert f.read() == original_content
    
    def test_update_block_code_validates_request(self):
        """Test request validation."""
        # Missing required fields
        response = client.post("/blocks/update-code/", json={
            "block_path": "/test/atlasvibe_blocks/BLOCK/BLOCK.py"
            # Missing content and project_path
        })
        
        assert response.status_code == 422  # Validation error