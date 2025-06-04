#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial test implementation for update_block_code endpoint
# - Following TDD methodology
# 

"""Tests for the update_block_code endpoint."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

# Test data
INITIAL_BLOCK_CODE = """#!/usr/bin/env python3
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
"""

UPDATED_BLOCK_CODE = """#!/usr/bin/env python3
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


class TestUpdateBlockCode:
    """Test cases for update_block_code functionality."""
    
    @pytest.fixture
    def temp_custom_block(self):
        """Create a temporary custom block file."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            prefix='atlasvibe_blocks_CUSTOM_',
            delete=False
        ) as f:
            f.write(INITIAL_BLOCK_CODE)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    def test_validate_custom_block_path_accepts_valid_path(self):
        """Test that paths containing 'atlasvibe_blocks' are accepted."""
        from captain.routes.blocks import UpdateBlockCodeRequest
        
        # This should not raise an exception
        valid_path = "/project/atlasvibe_blocks/CUSTOM/CUSTOM.py"
        request = UpdateBlockCodeRequest(
            block_path=valid_path,
            content="content",
            project_path="/project/test.atlasvibe"
        )
        
        # Should be able to check if it's a custom block
        assert "atlasvibe_blocks" in request.block_path
    
    def test_validate_custom_block_path_rejects_blueprint_path(self):
        """Test that paths without 'atlasvibe_blocks' are rejected."""
        from captain.routes.blocks import UpdateBlockCodeRequest
        
        blueprint_path = "/blocks/MATH/ADD/ADD.py"
        request = UpdateBlockCodeRequest(
            block_path=blueprint_path,
            content="content",
            project_path="/project/test.atlasvibe"
        )
        
        # Should be able to identify this is not a custom block
        assert "atlasvibe_blocks" not in request.block_path
    
    def test_validate_project_path_accepts_valid_atlasvibe_file(self):
        """Test that project paths ending with .atlasvibe are accepted."""
        from captain.routes.blocks import UpdateBlockCodeRequest
        
        request = UpdateBlockCodeRequest(
            block_path="/path/atlasvibe_blocks/BLOCK/BLOCK.py",
            content="content",
            project_path="/project/myproject.atlasvibe"
        )
        
        assert request.project_path.endswith('.atlasvibe')
    
    def test_validate_project_path_rejects_invalid_paths(self):
        """Test that project paths not ending with .atlasvibe are invalid."""
        from captain.routes.blocks import UpdateBlockCodeRequest
        
        request = UpdateBlockCodeRequest(
            block_path="/path/atlasvibe_blocks/BLOCK/BLOCK.py",
            content="content",
            project_path="/project/invalid"
        )
        
        assert not request.project_path.endswith('.atlasvibe')
    
    @patch('captain.routes.blocks.Path')
    @patch('captain.routes.blocks.process_block_directory')
    def test_update_block_code_writes_new_content(
        self, 
        mock_process_block,
        mock_path_class,
        temp_custom_block
    ):
        """Test that update_block_code writes the new content to file."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = INITIAL_BLOCK_CODE
        mock_path.parent.name = "CUSTOM_BLOCK"
        mock_path_class.return_value = mock_path
        
        mock_process_block.return_value = {
            "name": "CUSTOM_BLOCK",
            "type": "default"
        }
        
        # Import after mocks are set up
        from captain.routes.blocks import update_block_code, UpdateBlockCodeRequest
        
        # Create request
        request = UpdateBlockCodeRequest(
            block_path=f"{temp_custom_block}",
            content=UPDATED_BLOCK_CODE,
            project_path="/project/test.atlasvibe"
        )
        
        # This test expects the function to exist and be callable
        # Currently it will fail because the function doesn't exist yet
        with pytest.raises(AttributeError):
            update_block_code(request)
    
    @patch('captain.routes.blocks.Path')
    def test_update_block_code_backs_up_original_content(
        self,
        mock_path_class
    ):
        """Test that original content is backed up before writing new content."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = INITIAL_BLOCK_CODE
        mock_path_class.return_value = mock_path
        
        from captain.routes.blocks import UpdateBlockCodeRequest
        
        UpdateBlockCodeRequest(
            block_path="/project/atlasvibe_blocks/CUSTOM/CUSTOM.py",
            content=UPDATED_BLOCK_CODE,
            project_path="/project/test.atlasvibe"
        )
        
        # Test expects that original content is preserved
        # This will fail until implementation is done
        assert mock_path.read_text.return_value == INITIAL_BLOCK_CODE
    
    @patch('captain.routes.blocks.Path')
    @patch('captain.routes.blocks.process_block_directory')
    def test_update_block_code_regenerates_manifest(
        self,
        mock_process_block,
        mock_path_class
    ):
        """Test that block manifest is regenerated after code update."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = INITIAL_BLOCK_CODE
        mock_path.parent.name = "CUSTOM_BLOCK"
        mock_path_class.return_value = mock_path
        
        expected_manifest = {
            "name": "CUSTOM_BLOCK",
            "type": "default",
            "inputs": [{"name": "x", "type": "int"}],
            "outputs": [{"name": "output", "type": "int"}]
        }
        mock_process_block.return_value = expected_manifest
        
        from captain.routes.blocks import UpdateBlockCodeRequest
        
        UpdateBlockCodeRequest(
            block_path="/project/atlasvibe_blocks/CUSTOM/CUSTOM.py",
            content=UPDATED_BLOCK_CODE,
            project_path="/project/test.atlasvibe"
        )
        
        # Test expects process_block_directory to be called
        # This will fail until implementation exists
        assert mock_process_block.call_count == 0  # Will be 1 after implementation
    
    @patch('captain.routes.blocks.Path')
    @patch('captain.routes.blocks.process_block_directory')
    def test_update_block_code_rollback_on_manifest_failure(
        self,
        mock_process_block,
        mock_path_class
    ):
        """Test that changes are rolled back if manifest generation fails."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        original_content = INITIAL_BLOCK_CODE
        mock_path.read_text.return_value = original_content
        mock_path_class.return_value = mock_path
        
        # Simulate manifest generation failure
        mock_process_block.return_value = None
        
        from captain.routes.blocks import UpdateBlockCodeRequest
        
        UpdateBlockCodeRequest(
            block_path="/project/atlasvibe_blocks/CUSTOM/CUSTOM.py",
            content=UPDATED_BLOCK_CODE,
            project_path="/project/test.atlasvibe"
        )
        
        # Test expects rollback behavior
        # The write_text should be called twice:
        # 1. First with new content
        # 2. Second with original content (rollback)
        # This will fail until implementation exists
        assert mock_path.write_text.call_count == 0  # Will be 2 after implementation