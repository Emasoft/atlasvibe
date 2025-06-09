#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Real integration test for update_block_code without mocks
# - Tests the actual file system operations and API behavior
# 

"""Integration tests for update_block_code functionality without mocks."""

import pytest
import tempfile
from pathlib import Path
import json
import sys
import os
import asyncio

# Add project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from captain.routes.blocks import UpdateBlockCodeRequest, update_block_code
from captain.utils.manifest.build_manifest import create_manifest
from fastapi import HTTPException


class TestUpdateBlockCodeRealIntegration:
    """Real integration tests without mocks."""
    
    @pytest.fixture
    def real_project_setup(self):
        """Create a real temporary project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project structure
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            
            project_file = project_dir / "test_project.atlasvibe"
            project_file.write_text(json.dumps({
                "version": "0.1.0",
                "nodes": [],
                "edges": []
            }))
            
            # Create atlasvibe_blocks directory
            blocks_dir = project_dir / "atlasvibe_blocks"
            blocks_dir.mkdir()
            
            # Create a custom block
            custom_block_dir = blocks_dir / "MY_CUSTOM_BLOCK"
            custom_block_dir.mkdir()
            
            # Create __init__.py
            (custom_block_dir / "__init__.py").write_text("")
            
            # Create block Python file
            block_file = custom_block_dir / "MY_CUSTOM_BLOCK.py"
            block_file.write_text("""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def MY_CUSTOM_BLOCK(x: int = 1, y: int = 2) -> int:
    '''Add two numbers.
    
    This block adds two input numbers together.
    
    Parameters:
        x: First number
        y: Second number
        
    Returns:
        int: Sum of x and y
    '''
    return x + y
""")
            
            # Create metadata files
            (custom_block_dir / "app.json").write_text(json.dumps({
                "name": "MY_CUSTOM_BLOCK",
                "type": "default",
                "category": "PROJECT"
            }))
            
            (custom_block_dir / "block_data.json").write_text(json.dumps({
                "inputs": [
                    {"name": "x", "type": "int", "default": 1},
                    {"name": "y", "type": "int", "default": 2}
                ],
                "outputs": [{"name": "output", "type": "int"}]
            }))
            
            yield {
                "project_dir": project_dir,
                "project_file": str(project_file),
                "blocks_dir": blocks_dir,
                "block_file": str(block_file),
                "block_dir": custom_block_dir
            }
    
    @pytest.mark.asyncio
    async def test_update_block_code_real_file_operations(self, real_project_setup):
        """Test updating block code with real file operations."""
        block_file_path = real_project_setup["block_file"]
        project_path = real_project_setup["project_file"]
        
        # New code that changes the implementation
        new_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def MY_CUSTOM_BLOCK(x: int = 1, y: int = 2) -> int:
    '''Multiply two numbers.
    
    This block multiplies two input numbers together.
    
    Parameters:
        x: First number
        y: Second number
        
    Returns:
        int: Product of x and y
    '''
    return x * y  # Changed from addition to multiplication
"""
        
        # Create request
        request = UpdateBlockCodeRequest(
            block_path=block_file_path,
            content=new_code,
            project_path=project_path
        )
        
        # Call the actual function (no mocks)
        result = await update_block_code(request)
        
        # Verify the file was actually updated
        with open(block_file_path, 'r') as f:
            actual_content = f.read()
        
        assert actual_content == new_code
        assert "x * y" in actual_content
        assert "Multiply two numbers" in actual_content
        
        # Verify the result is a proper manifest
        assert isinstance(result, dict)
        assert result.get("name") == "MY_CUSTOM_BLOCK"
        assert "path" in result
        assert result["path"] == str(Path(block_file_path).parent)
    
    @pytest.mark.asyncio
    async def test_update_block_code_validates_custom_block_path(self, real_project_setup):
        """Test that non-custom blocks are rejected."""
        # Try to update a blueprint block (no atlasvibe_blocks in path)
        request = UpdateBlockCodeRequest(
            block_path="/blocks/MATH/ADD/ADD.py",
            content="# new content",
            project_path=real_project_setup["project_file"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await update_block_code(request)
        
        assert exc_info.value.status_code == 403
        assert "custom project blocks" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_block_code_validates_project_path(self, real_project_setup):
        """Test that invalid project paths are rejected."""
        request = UpdateBlockCodeRequest(
            block_path=real_project_setup["block_file"],
            content="# new content",
            project_path="/invalid/project/path"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await update_block_code(request)
        
        assert exc_info.value.status_code == 422
        assert "Invalid project path" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_block_code_handles_missing_file(self):
        """Test handling of non-existent block files."""
        request = UpdateBlockCodeRequest(
            block_path="/nonexistent/atlasvibe_blocks/BLOCK/BLOCK.py",
            content="# new content",
            project_path="/project/test.atlasvibe"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await update_block_code(request)
        
        assert exc_info.value.status_code == 404
        assert "Block file not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_block_code_with_syntax_error(self, real_project_setup):
        """Test that files with syntax errors are handled gracefully."""
        block_file_path = real_project_setup["block_file"]
        project_path = real_project_setup["project_file"]
        
        # Read original content for verification of rollback
        with open(block_file_path, 'r') as f:
            original_content = f.read()
        
        # Code with syntax error
        bad_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def MY_CUSTOM_BLOCK(x: int = 1, y: int = 2) -> int:
    '''This has a syntax error.'''
    return x +   # Syntax error here
"""
        
        request = UpdateBlockCodeRequest(
            block_path=block_file_path,
            content=bad_code,
            project_path=project_path
        )
        
        # The update might succeed (file is written) but manifest generation might fail
        # This depends on how process_block_directory handles syntax errors
        try:
            await update_block_code(request)
            # If it succeeds, the file should still be updated
            with open(block_file_path, 'r') as f:
                assert f.read() == bad_code
        except HTTPException:
            # If it fails, check that the original content is restored
            with open(block_file_path, 'r') as f:
                assert f.read() == original_content
    
    @pytest.mark.asyncio
    async def test_manifest_regeneration_with_real_block(self, real_project_setup):
        """Test that manifest is properly regenerated after code update."""
        block_file_path = real_project_setup["block_file"]
        block_dir = real_project_setup["block_dir"]
        project_path = real_project_setup["project_file"]
        
        # Update to add a new parameter
        new_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def MY_CUSTOM_BLOCK(x: int = 1, y: int = 2, z: int = 3) -> int:
    '''Add three numbers.
    
    Parameters:
        x: First number
        y: Second number
        z: Third number
        
    Returns:
        int: Sum of x, y and z
    '''
    return x + y + z
"""
        
        request = UpdateBlockCodeRequest(
            block_path=block_file_path,
            content=new_code,
            project_path=project_path
        )
        
        # Update the block
        await update_block_code(request)
        
        # Manually regenerate manifest to verify it would work
        manifest = create_manifest(block_file_path)
        
        # The manifest should reflect the new parameter
        assert manifest is not None
        assert "parameters" in manifest
        param_names = list(manifest["parameters"].keys())
        assert "x" in param_names
        assert "y" in param_names
        assert "z" in param_names  # New parameter should be present
    
    @pytest.mark.asyncio
    async def test_concurrent_updates_safety(self, real_project_setup):
        """Test that concurrent updates don't corrupt files."""
        import asyncio
        
        block_file_path = real_project_setup["block_file"]
        project_path = real_project_setup["project_file"]
        
        results = []
        errors = []
        
        async def update_block(content_suffix):
            try:
                new_code = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def MY_CUSTOM_BLOCK(x: int = 1) -> int:
    '''Updated by thread {content_suffix}.'''
    return x * {content_suffix}
"""
                request = UpdateBlockCodeRequest(
                    block_path=block_file_path,
                    content=new_code,
                    project_path=project_path
                )
                
                result = await update_block_code(request)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple coroutines trying to update the same file
        tasks = []
        for i in range(3):
            task = asyncio.create_task(update_block(i))
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # At least one should succeed
        assert len(results) >= 1
        
        # File should be in a valid state
        with open(block_file_path, 'r') as f:
            final_content = f.read()
        
        # Content should be valid Python
        assert "def MY_CUSTOM_BLOCK" in final_content
        assert "return x *" in final_content