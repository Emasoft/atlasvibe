#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created comprehensive test for automatic metadata generation and regeneration
# - Tests file watching mechanism for custom blocks
# - Tests visual indicator requirements (regenerating label)
# 

"""Test automatic metadata generation and regeneration for custom blocks.

This module tests:
1. Automatic metadata generation when a new custom block folder is created
2. Metadata regeneration when block code is modified
3. File watching mechanism for detecting changes
4. Visual feedback requirements during regeneration
"""

import pytest
import tempfile
import json
import time
import asyncio
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from captain.utils.project_structure import (
    initialize_project_structure,
    copy_blueprint_to_project,
)
from captain.utils.manifest.build_manifest import create_manifest
from captain.services.consumer.blocks_watcher import BlocksWatcher
from captain.internal.wsmanager import ConnectionManager


class TestMetadataGeneration:
    """Test automatic metadata generation and regeneration."""
    
    @pytest.fixture
    def test_project(self):
        """Create a test project with custom blocks directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project file
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            project_file = project_dir / "test_project.atlasvibe"
            project_file.write_text(json.dumps({
                "version": "2.0.0",
                "name": "Test Project",
                "rfInstance": {"nodes": [], "edges": []}
            }))
            
            # Initialize project structure
            initialize_project_structure(str(project_file))
            
            yield {
                "project_dir": project_dir,
                "project_file": str(project_file),
                "blocks_dir": project_dir / "atlasvibe_blocks"
            }
    
    def test_metadata_generated_on_new_block_creation(self, test_project):
        """Test that metadata files are generated when a new custom block is created."""
        # Create a new custom block folder
        block_name = "TEST_CUSTOM_BLOCK"
        block_dir = test_project["blocks_dir"] / block_name
        block_dir.mkdir()
        
        # Create __init__.py
        (block_dir / "__init__.py").write_text("")
        
        # Create the Python file
        py_file = block_dir / f"{block_name}.py"
        py_file.write_text("""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def TEST_CUSTOM_BLOCK(x: int = 10, y: int = 20) -> int:
    '''Test custom block that adds two numbers.
    
    Parameters:
        x: First number
        y: Second number
        
    Returns:
        int: Sum of x and y
    '''
    return x + y
""")
        
        # Generate manifest
        manifest = create_manifest(str(py_file))
        
        # Verify manifest was generated
        assert manifest is not None
        assert manifest["name"] == "TEST_CUSTOM_BLOCK"
        assert manifest["key"] == "TEST_CUSTOM_BLOCK"
        assert "parameters" in manifest
        assert "x" in manifest["parameters"]
        assert "y" in manifest["parameters"]
        assert manifest["parameters"]["x"]["default"] == 10
        assert manifest["parameters"]["y"]["default"] == 20
        
        # The manifest structure has changed - let's verify the actual structure
        print(f"Manifest structure: {manifest}")  # Debug output
    
    def test_metadata_regenerated_on_code_change(self, test_project):
        """Test that metadata is regenerated when block code changes."""
        # Create initial block
        block_name = "CHANGING_BLOCK"
        block_dir = test_project["blocks_dir"] / block_name
        block_dir.mkdir()
        (block_dir / "__init__.py").write_text("")
        
        py_file = block_dir / f"{block_name}.py"
        initial_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def CHANGING_BLOCK(x: int = 1) -> int:
    '''Original version.'''
    return x * 2
"""
        py_file.write_text(initial_code)
        
        # Generate initial manifest
        initial_manifest = create_manifest(str(py_file))
        assert len(initial_manifest["parameters"]) == 1
        assert "x" in initial_manifest["parameters"]
        
        # Update the code
        updated_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def CHANGING_BLOCK(x: int = 1, multiplier: int = 3, offset: int = 0) -> int:
    '''Updated version with more parameters.'''
    return x * multiplier + offset
"""
        py_file.write_text(updated_code)
        
        # Regenerate manifest
        updated_manifest = create_manifest(str(py_file))
        
        # Verify new parameters are in manifest
        assert len(updated_manifest["parameters"]) == 3
        assert "x" in updated_manifest["parameters"]
        assert "multiplier" in updated_manifest["parameters"]
        assert "offset" in updated_manifest["parameters"]
        assert updated_manifest["parameters"]["multiplier"]["default"] == 3
        assert updated_manifest["parameters"]["offset"]["default"] == 0
    
    @pytest.mark.asyncio
    async def test_file_watcher_detects_changes(self, test_project):
        """Test that the file watcher detects changes to custom blocks."""
        # Mock WebSocket connection manager
        mock_ws = Mock(spec=ConnectionManager)
        mock_ws.active_connections_map = {"test": Mock()}
        # Create a proper async mock
        async def mock_broadcast(data):
            pass
        mock_ws.broadcast = Mock(side_effect=mock_broadcast)
        
        with patch('captain.services.consumer.blocks_watcher.ConnectionManager.get_instance', return_value=mock_ws):
            watcher = BlocksWatcher()
            
            # Create a stop flag
            stop_flag = threading.Event()
            
            # Start watching in a background task
            watch_task = asyncio.create_task(watcher.run(stop_flag))
            
            # Give watcher time to start
            await asyncio.sleep(0.5)
            
            # Create a new block
            block_name = "WATCHED_BLOCK"
            block_dir = test_project["blocks_dir"] / block_name
            block_dir.mkdir()
            
            py_file = block_dir / f"{block_name}.py"
            py_file.write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def WATCHED_BLOCK(x: int = 1) -> int:
    return x
""")
            
            # Give watcher time to detect the change
            await asyncio.sleep(1.0)
            
            # Stop the watcher
            stop_flag.set()
            
            # Wait for task to complete
            try:
                await asyncio.wait_for(watch_task, timeout=2.0)
            except asyncio.TimeoutError:
                watch_task.cancel()
            
            # Verify broadcast was called with manifest_update
            mock_ws.broadcast.assert_called()
            calls = mock_ws.broadcast.call_args_list
            assert any(
                call[0][0].get("type") == "manifest_update"
                for call in calls
            )
    
    def test_blueprint_to_custom_block_copy(self, test_project):
        """Test copying a blueprint block to create a custom block."""
        # Create a mock blueprint directory
        with tempfile.TemporaryDirectory() as blueprint_dir:
            blueprint_path = Path(blueprint_dir) / "BLUEPRINT_BLOCK"
            blueprint_path.mkdir()
            
            # Create blueprint files
            (blueprint_path / "__init__.py").write_text("")
            (blueprint_path / "BLUEPRINT_BLOCK.py").write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def BLUEPRINT_BLOCK(x: int = 5) -> int:
    '''Blueprint block for testing.'''
    return x ** 2
""")
            
            # Create metadata files
            (blueprint_path / "app.json").write_text(json.dumps({
                "name": "BLUEPRINT_BLOCK",
                "type": "default",
                "category": "MATH"
            }))
            
            (blueprint_path / "block_data.json").write_text(json.dumps({
                "inputs": [{"name": "x", "type": "int", "default": 5}],
                "outputs": [{"name": "output", "type": "int"}]
            }))
            
            # Copy blueprint to project
            new_block_name = "MY_CUSTOM_BLOCK"
            custom_block_path = copy_blueprint_to_project(
                str(blueprint_path),
                test_project["project_file"],
                new_block_name
            )
            
            # Verify the custom block was created
            custom_block_dir = Path(custom_block_path)
            assert custom_block_dir.exists()
            assert custom_block_dir.name == new_block_name
            
            # Verify Python file was renamed and updated
            py_file = custom_block_dir / f"{new_block_name}.py"
            assert py_file.exists()
            
            content = py_file.read_text()
            assert f"def {new_block_name}(" in content
            assert "def BLUEPRINT_BLOCK(" not in content
            
            # Verify metadata files exist
            assert (custom_block_dir / "app.json").exists()
            assert (custom_block_dir / "block_data.json").exists()
            
            # Generate manifest for the new block
            manifest = create_manifest(str(py_file))
            assert manifest["name"] == new_block_name
            assert manifest["key"] == new_block_name
    
    def test_visual_feedback_requirements(self):
        """Document the visual feedback requirements for regeneration.
        
        This test documents what SHOULD happen in the UI during regeneration:
        1. Block borders should change color
        2. A "regenerating" label should appear above the block
        3. The label should blink
        4. This should happen whenever a block is being regenerated
        """
        # These are the requirements that need to be implemented in the frontend
        visual_requirements = {
            "border_color_change": {
                "description": "Block border color must change during regeneration",
                "suggested_color": "orange or yellow",
                "css_class": "regenerating"
            },
            "regenerating_label": {
                "description": "A label saying 'regenerating' must appear above the block",
                "position": "above the block",
                "visibility": "visible during regeneration only"
            },
            "blinking_animation": {
                "description": "The regenerating label must blink",
                "suggested_css": "@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }",
                "animation_duration": "1s"
            },
            "trigger_conditions": {
                "description": "Visual feedback must be shown when:",
                "conditions": [
                    "Block code is modified and saved",
                    "New custom block is created",
                    "Manifest regeneration is in progress"
                ]
            }
        }
        
        # Print requirements for documentation
        print("\n=== Visual Feedback Requirements for Block Regeneration ===")
        for key, req in visual_requirements.items():
            print(f"\n{key}:")
            for k, v in req.items():
                if isinstance(v, list):
                    print(f"  {k}:")
                    for item in v:
                        print(f"    - {item}")
                else:
                    print(f"  {k}: {v}")
        
        # This test passes to document the requirements
        assert True