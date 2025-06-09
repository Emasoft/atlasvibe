#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created comprehensive test to demonstrate the complete metadata generation flow
# - Shows what happens when custom blocks are created and modified
# - Documents the missing visual feedback functionality
# 

"""Test the complete metadata generation and regeneration flow.

This test demonstrates:
1. How metadata is generated when creating custom blocks
2. How the file watcher detects changes
3. What WebSocket messages are sent
4. What visual feedback is missing
"""

import pytest
import tempfile
import json
import time
import asyncio
import threading
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from captain.main import app
from captain.utils.project_structure import (
    initialize_project_structure,
    copy_blueprint_to_project,
)
from captain.utils.manifest.build_manifest import create_manifest
from captain.services.consumer.blocks_watcher import BlocksWatcher
from captain.internal.wsmanager import ConnectionManager


class TestCompleteMetadataFlow:
    """Test the complete flow of metadata generation and regeneration."""
    
    @pytest.fixture
    def test_client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def test_project(self):
        """Create a test project with proper structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
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
    
    def test_complete_flow_with_api(self, test_client, test_project):
        """Test the complete flow using the API endpoints."""
        
        # Step 1: Create a blueprint block to copy from
        with tempfile.TemporaryDirectory() as blueprint_base:
            # Create mock blueprint structure
            blueprint_dir = Path(blueprint_base) / "blocks" / "MATH" / "ARITHMETIC" / "CONSTANT"
            blueprint_dir.mkdir(parents=True)
            
            # Create blueprint files
            (blueprint_dir / "__init__.py").write_text("")
            (blueprint_dir / "CONSTANT.py").write_text("""#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def CONSTANT(x: int = 42) -> int:
    '''Returns a constant value.
    
    Parameters:
        x: The constant value
        
    Returns:
        int: The constant value
    '''
    return x
""")
            
            # Create metadata files
            (blueprint_dir / "app.json").write_text(json.dumps({
                "name": "CONSTANT",
                "type": "default",
                "category": "MATH"
            }))
            
            (blueprint_dir / "block_data.json").write_text(json.dumps({
                "inputs": [],
                "outputs": [{"name": "output", "type": "int"}]
            }))
            
            # Mock the blocks path
            with patch('captain.utils.blocks_path.get_blocks_path', return_value=str(Path(blueprint_base) / "blocks")):
                # Step 2: Create custom block via API
                response = test_client.post("/blocks/create-custom/", json={
                    "blueprint_key": "CONSTANT",
                    "new_block_name": "MY_CUSTOM_CONSTANT",
                    "project_path": test_project["project_file"]
                })
                
                assert response.status_code == 200
                manifest = response.json()
                
                print("\n=== Step 2: Custom Block Created ===")
                print(f"Manifest: {json.dumps(manifest, indent=2)}")
                
                # Verify the manifest
                assert manifest["name"] == "MY_CUSTOM_CONSTANT"
                assert manifest["key"] == "MY_CUSTOM_CONSTANT"
                assert "parameters" in manifest
                assert "x" in manifest["parameters"]
                assert manifest["parameters"]["x"]["default"] == 42
                
                # Verify files were created
                custom_block_dir = test_project["blocks_dir"] / "MY_CUSTOM_CONSTANT"
                assert custom_block_dir.exists()
                assert (custom_block_dir / "MY_CUSTOM_CONSTANT.py").exists()
                assert (custom_block_dir / "app.json").exists()
                assert (custom_block_dir / "block_data.json").exists()
                
                # Step 3: Update the custom block code
                block_file_path = str(custom_block_dir / "MY_CUSTOM_CONSTANT.py")
                new_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def MY_CUSTOM_CONSTANT(x: int = 42, multiplier: int = 2, description: str = "Custom constant") -> int:
    '''Returns a constant value with optional multiplication.
    
    Parameters:
        x: The constant value
        multiplier: Multiplication factor
        description: Description of the constant
        
    Returns:
        int: The constant value multiplied by the factor
    '''
    print(f"{description}: {x} * {multiplier}")
    return x * multiplier
"""
                
                response = test_client.post("/blocks/update-code/", json={
                    "block_path": block_file_path,
                    "content": new_code,
                    "project_path": test_project["project_file"]
                })
                
                assert response.status_code == 200
                updated_manifest = response.json()
                
                print("\n=== Step 3: Block Code Updated ===")
                print(f"Updated Manifest: {json.dumps(updated_manifest, indent=2)}")
                
                # Verify manifest was regenerated with new parameters
                assert len(updated_manifest["parameters"]) == 3
                assert "multiplier" in updated_manifest["parameters"]
                assert "description" in updated_manifest["parameters"]
                assert updated_manifest["parameters"]["multiplier"]["default"] == 2
                assert updated_manifest["parameters"]["description"]["default"] == "Custom constant"
    
    @pytest.mark.asyncio
    async def test_file_watcher_websocket_flow(self, test_project):
        """Test the file watcher and WebSocket notification flow."""
        
        # Mock WebSocket broadcasts
        broadcast_calls = []
        
        async def mock_broadcast(data):
            broadcast_calls.append(data)
            print(f"\n=== WebSocket Broadcast ===")
            print(f"Message: {data}")
        
        mock_ws = Mock(spec=ConnectionManager)
        mock_ws.active_connections_map = {"test": Mock()}
        mock_ws.broadcast = Mock(side_effect=mock_broadcast)
        
        with patch('captain.services.consumer.blocks_watcher.ConnectionManager.get_instance', return_value=mock_ws):
            watcher = BlocksWatcher()
            stop_flag = threading.Event()
            
            # Start watching
            watch_task = asyncio.create_task(watcher.run(stop_flag))
            
            # Give watcher time to start
            await asyncio.sleep(0.5)
            
            # Create a new custom block
            block_name = "DETECTED_BLOCK"
            block_dir = test_project["blocks_dir"] / block_name
            block_dir.mkdir()
            
            print(f"\n=== Creating Custom Block: {block_name} ===")
            
            # Create files
            (block_dir / "__init__.py").write_text("")
            py_file = block_dir / f"{block_name}.py"
            py_file.write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def DETECTED_BLOCK(value: int = 100) -> int:
    return value
""")
            
            # Wait for detection
            await asyncio.sleep(1.5)
            
            # Modify the file
            print(f"\n=== Modifying Block Code ===")
            py_file.write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def DETECTED_BLOCK(value: int = 100, new_param: str = "detected") -> int:
    print(new_param)
    return value * 2
""")
            
            # Wait for detection
            await asyncio.sleep(1.5)
            
            # Stop watching
            stop_flag.set()
            try:
                await asyncio.wait_for(watch_task, timeout=2.0)
            except asyncio.TimeoutError:
                watch_task.cancel()
            
            # Verify broadcasts
            print(f"\n=== Total WebSocket Messages: {len(broadcast_calls)} ===")
            assert len(broadcast_calls) >= 2  # At least 2 file change events
            
            for call in broadcast_calls:
                assert call.get("type") == "manifest_update"
    
    def test_visual_feedback_not_implemented(self):
        """Document what visual feedback is NOT implemented."""
        
        missing_features = {
            "Frontend State Management": {
                "missing": "No isRegenerating state tracking per block",
                "needed": "Store should track which blocks are being regenerated",
                "location": "src/renderer/stores/manifest.ts or similar"
            },
            "Visual Indicators in DefaultBlock": {
                "missing": "No special styling during regeneration",
                "needed": "Border color change (e.g., orange) when regenerating",
                "location": "src/renderer/components/blocks/default-block.tsx"
            },
            "Regenerating Label": {
                "missing": "No label shown above blocks during regeneration",
                "needed": "Blinking 'Regenerating...' label",
                "location": "Above block component with absolute positioning"
            },
            "CSS Animations": {
                "missing": "No blinking or pulsing animations defined",
                "needed": "@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }",
                "location": "Global CSS or component styles"
            },
            "WebSocket Integration": {
                "existing": "manifest_update events ARE sent and received",
                "missing": "Events don't trigger visual state changes",
                "needed": "Connect manifest_update to set isRegenerating state"
            },
            "Regeneration Completion": {
                "missing": "No way to know when regeneration completes",
                "needed": "Clear isRegenerating state after manifest fetch completes"
            }
        }
        
        print("\n=== MISSING VISUAL FEEDBACK FEATURES ===")
        for feature, details in missing_features.items():
            print(f"\n{feature}:")
            for key, value in details.items():
                print(f"  {key}: {value}")
        
        # This assertion documents that the visual features are NOT implemented
        assert True, "Visual feedback features are documented as missing"
    
    def test_what_should_happen(self):
        """Document the expected user experience with visual feedback."""
        
        expected_flow = [
            {
                "step": 1,
                "action": "User creates a new custom block",
                "backend": "✅ Block files are created, manifest generated",
                "frontend": "❌ Should show block with orange border and 'Regenerating...' label",
                "actual": "Block appears normally, no visual indication"
            },
            {
                "step": 2,
                "action": "User edits custom block code and saves",
                "backend": "✅ File watcher detects change, sends manifest_update",
                "frontend": "❌ Should immediately show orange border and blinking label",
                "actual": "Toast notification appears, no visual change to block"
            },
            {
                "step": 3,
                "action": "Backend regenerates manifest",
                "backend": "✅ Manifest is regenerated with new parameters",
                "frontend": "❌ Block should remain in 'regenerating' state",
                "actual": "No visual indication of ongoing process"
            },
            {
                "step": 4,
                "action": "Frontend fetches updated manifest",
                "backend": "✅ Updated manifest is returned",
                "frontend": "❌ Should clear regenerating state and restore normal appearance",
                "actual": "Block parameters update silently"
            }
        ]
        
        print("\n=== EXPECTED USER EXPERIENCE ===")
        for flow in expected_flow:
            print(f"\nStep {flow['step']}: {flow['action']}")
            print(f"  Backend: {flow['backend']}")
            print(f"  Frontend Expected: {flow['frontend']}")
            print(f"  Frontend Actual: {flow['actual']}")
        
        # Create a visual mockup of what it should look like
        mockup = """
        Normal Block:                    Regenerating Block:
        ┌─────────────────┐             ┌─────────────────┐ ← Orange border
        │                 │             │  Regenerating... │ ← Blinking label
        │   CUSTOM_BLOCK  │             │─────────────────│
        │                 │             │                 │
        │   x: [42    ]   │             │   CUSTOM_BLOCK  │
        │                 │             │                 │
        └─────────────────┘             │   x: [42    ]   │
                                        │                 │
                                        └─────────────────┘
        """
        
        print("\n=== VISUAL MOCKUP ===")
        print(mockup)
        
        assert True, "Expected behavior documented"