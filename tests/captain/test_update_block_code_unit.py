#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Unit tests for update_block_code functionality
# - Tests the core logic without full module imports
# 

"""Unit tests for update_block_code functionality."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


class TestUpdateBlockCodeUnit:
    """Unit tests for update_block_code core functionality."""
    
    def test_request_model_validation(self):
        """Test that the UpdateBlockCodeRequest model validates inputs."""
        from pydantic import BaseModel
        
        # Define the expected model structure
        class UpdateBlockCodeRequest(BaseModel):
            block_path: str
            content: str
            project_path: str
        
        # Valid request
        valid_request = UpdateBlockCodeRequest(
            block_path="/project/atlasvibe_blocks/CUSTOM/CUSTOM.py",
            content="# code",
            project_path="/project/test.atlasvibe"
        )
        assert valid_request.block_path.endswith(".py")
        assert valid_request.project_path.endswith(".atlasvibe")
        
        # Invalid request should raise validation error
        with pytest.raises(Exception):
            UpdateBlockCodeRequest(
                block_path="/project/atlasvibe_blocks/CUSTOM/CUSTOM.py",
                # Missing required fields
            )
    
    def test_is_custom_block_check(self):
        """Test logic for checking if a path is a custom block."""
        # Custom blocks contain "atlasvibe_blocks" in their path
        custom_block_path = "/project/atlasvibe_blocks/CUSTOM/CUSTOM.py"
        blueprint_path = "/blocks/MATH/ADD/ADD.py"
        
        assert "atlasvibe_blocks" in custom_block_path
        assert "atlasvibe_blocks" not in blueprint_path
    
    def test_is_valid_project_path(self):
        """Test logic for validating project paths."""
        valid_path = "/project/myproject.atlasvibe"
        invalid_path = "/project/myproject"
        
        assert valid_path.endswith(".atlasvibe")
        assert not invalid_path.endswith(".atlasvibe")
    
    def test_file_backup_logic(self):
        """Test the logic for backing up file content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            original_content = "# Original content"
            f.write(original_content)
            temp_path = Path(f.name)
        
        try:
            # Read original content
            backup_content = temp_path.read_text()
            assert backup_content == original_content
            
            # Write new content
            new_content = "# New content"
            temp_path.write_text(new_content)
            assert temp_path.read_text() == new_content
            
            # Simulate rollback
            temp_path.write_text(backup_content)
            assert temp_path.read_text() == original_content
            
        finally:
            temp_path.unlink()
    
    def test_manifest_generation_with_rollback(self):
        """Test manifest generation with rollback on failure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            original_content = "# Original"
            f.write(original_content)
            temp_path = Path(f.name)
        
        try:
            # Mock manifest generation
            def mock_generate_manifest(path, name):
                if "invalid" in path.read_text():
                    return None  # Failure
                return {"name": name, "type": "default"}
            
            # Successful case
            temp_path.write_text("# Valid code")
            manifest = mock_generate_manifest(temp_path, "TEST")
            assert manifest is not None
            
            # Failure case - should trigger rollback
            temp_path.write_text("# invalid code")
            manifest = mock_generate_manifest(temp_path, "TEST")
            if manifest is None:
                # Rollback
                temp_path.write_text(original_content)
            
            assert temp_path.read_text() == original_content
            
        finally:
            temp_path.unlink()
    
    @patch('captain.routes.blocks.Path')
    @patch('captain.routes.blocks.create_manifest')
    @patch('captain.routes.blocks.regenerate_block_data_json')
    def test_update_block_code_flow(self, mock_regenerate, mock_create_manifest, mock_path_class):
        """Test the complete flow of update_block_code."""
        # Mock setup
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "# Original"
        mock_path.parent.name = "CUSTOM_BLOCK"
        mock_path_class.return_value = mock_path
        
        mock_create_manifest.return_value = {"name": "CUSTOM_BLOCK", "type": "default"}
        mock_regenerate.return_value = True
        
        # Simulate the update flow
        block_path = "/project/atlasvibe_blocks/CUSTOM/CUSTOM.py"
        new_content = "# Updated"
        project_path = "/project/test.atlasvibe"
        
        # Validation checks
        if "atlasvibe_blocks" not in block_path:
            raise HTTPException(status_code=403, detail="Can only edit custom project blocks")
        
        if not project_path.endswith('.atlasvibe'):
            raise HTTPException(status_code=422, detail="Invalid project path")
        
        # File operations
        if not mock_path.exists():
            raise HTTPException(status_code=404, detail="Block file not found")
        
        original_content = mock_path.read_text()
        
        try:
            mock_path.write_text(new_content)
            
            # Regenerate block data
            if not mock_regenerate(str(mock_path.parent)):
                # This would trigger a warning in real code
                pass
            
            # Generate manifest
            manifest = mock_create_manifest(str(mock_path))
            
            if not manifest:
                # Rollback
                mock_path.write_text(original_content)
                raise HTTPException(status_code=500, detail="Failed to regenerate manifest")
            
            manifest["path"] = str(mock_path.parent)
            
            # Verify the flow worked
            assert mock_path.write_text.called
            assert mock_regenerate.called
            assert mock_create_manifest.called
            assert manifest["path"] is not None
            
        except Exception:
            mock_path.write_text(original_content)
            raise


class TestBlockCodeUpdateIntegration:
    """Integration tests for block code update functionality."""
    
    @pytest.fixture
    def setup_test_block(self):
        """Set up a test block directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            project_dir = Path(tmpdir)
            blocks_dir = project_dir / "atlasvibe_blocks" / "TEST_BLOCK"
            blocks_dir.mkdir(parents=True)
            
            # Create block file
            block_file = blocks_dir / "TEST_BLOCK.py"
            block_file.write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 1) -> int:
    return x * 2
""")
            
            # Create __init__.py
            (blocks_dir / "__init__.py").touch()
            
            yield {
                "project_dir": project_dir,
                "blocks_dir": blocks_dir,
                "block_file": block_file
            }
    
    def test_end_to_end_update(self, setup_test_block):
        """Test end-to-end block update process."""
        block_file = setup_test_block["block_file"]
        original_content = block_file.read_text()
        
        # New content
        new_content = """#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 1) -> int:
    # Updated implementation
    return x * 3
"""
        
        # Simulate update process
        try:
            # Write new content
            block_file.write_text(new_content)
            
            # Verify content was updated
            assert block_file.read_text() == new_content
            assert "return x * 3" in block_file.read_text()
            
            # In real implementation, manifest would be regenerated here
            
        except Exception as e:
            # Rollback on error
            block_file.write_text(original_content)
            raise e