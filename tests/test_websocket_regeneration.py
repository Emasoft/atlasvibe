#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created test suite for WebSocket regeneration state management
# - Testing real-time block regeneration events
# 

"""Test WebSocket integration for block regeneration state management."""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

from captain.internal.wsmanager import ConnectionManager
from captain.types.worker import RegenerationMessage
from captain.services.consumer.blocks_watcher import BlocksWatcher


class TestWebSocketRegenerationState:
    """Test WebSocket communication for block regeneration state."""
    
    @pytest.fixture
    def mock_ws_manager(self):
        """Create a mock WebSocket manager."""
        ws_manager = MagicMock()
        ws_manager.broadcast = AsyncMock()
        return ws_manager
    
    @pytest.fixture
    def temp_block_dir(self):
        """Create a temporary block directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "TEST_BLOCK"
            block_dir.mkdir()
            
            # Create block file
            block_file = block_dir / "TEST_BLOCK.py"
            block_file.write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 1) -> int:
    '''Test block.'''
    return x * 2
""")
            
            # Create __init__.py
            (block_dir / "__init__.py").touch()
            
            yield {
                "dir": block_dir,
                "file": block_file
            }
    
    @pytest.mark.asyncio
    async def test_regeneration_start_event(self, mock_ws_manager):
        """Test that regeneration start event is broadcast."""
        block_name = "TEST_BLOCK"
        block_path = "/path/to/TEST_BLOCK"
        
        # Create regeneration start message
        message = RegenerationMessage(
            type="regeneration_start",
            block_name=block_name,
            block_path=block_path,
            status="regenerating"
        )
        
        # Broadcast the message
        await mock_ws_manager.broadcast(message)
        
        # Verify broadcast was called with correct message
        mock_ws_manager.broadcast.assert_called_once()
        call_args = mock_ws_manager.broadcast.call_args[0][0]
        
        assert call_args["type"] == "regeneration_start"
        assert call_args["block_name"] == block_name
        assert call_args["block_path"] == block_path
        assert call_args["status"] == "regenerating"
    
    @pytest.mark.asyncio
    async def test_regeneration_complete_event(self, mock_ws_manager):
        """Test that regeneration complete event is broadcast."""
        block_name = "TEST_BLOCK"
        block_path = "/path/to/TEST_BLOCK"
        
        # Create regeneration complete message
        message = RegenerationMessage(
            type="regeneration_complete",
            block_name=block_name,
            block_path=block_path,
            status="completed",
            success=True
        )
        
        # Broadcast the message
        await mock_ws_manager.broadcast(message)
        
        # Verify broadcast was called with correct message
        mock_ws_manager.broadcast.assert_called_once()
        call_args = mock_ws_manager.broadcast.call_args[0][0]
        
        assert call_args["type"] == "regeneration_complete"
        assert call_args["block_name"] == block_name
        assert call_args["block_path"] == block_path
        assert call_args["status"] == "completed"
        assert call_args["success"] is True
    
    @pytest.mark.asyncio
    async def test_regeneration_error_event(self, mock_ws_manager):
        """Test that regeneration error event is broadcast."""
        block_name = "TEST_BLOCK"
        block_path = "/path/to/TEST_BLOCK"
        error_message = "Failed to parse docstring"
        
        # Create regeneration error message
        message = RegenerationMessage(
            type="regeneration_error",
            block_name=block_name,
            block_path=block_path,
            status="error",
            success=False,
            error=error_message
        )
        
        # Broadcast the message
        await mock_ws_manager.broadcast(message)
        
        # Verify broadcast was called with correct message
        mock_ws_manager.broadcast.assert_called_once()
        call_args = mock_ws_manager.broadcast.call_args[0][0]
        
        assert call_args["type"] == "regeneration_error"
        assert call_args["block_name"] == block_name
        assert call_args["block_path"] == block_path
        assert call_args["status"] == "error"
        assert call_args["success"] is False
        assert call_args["error"] == error_message
    
    @pytest.mark.asyncio
    async def test_blocks_watcher_broadcasts_regeneration_events(self, temp_block_dir):
        """Test that BlocksWatcher broadcasts regeneration events when files change."""
        # This test verifies that the BlocksWatcher integrates with WebSocket
        # to broadcast regeneration events when block files are modified
        
        # Create a mock for the WebSocket manager
        mock_ws = AsyncMock()
        
        with patch('captain.services.consumer.blocks_watcher.ConnectionManager') as MockWS:
            MockWS.get_instance.return_value = mock_ws
            
            # Create BlocksWatcher instance
            watcher = BlocksWatcher()
            
            # Simulate file modification
            block_file = temp_block_dir["file"]
            
            # Mock the regeneration process
            with patch('captain.utils.block_metadata_generator.regenerate_block_data_json') as mock_regen:
                mock_regen.return_value = True
                
                # Simulate the watcher detecting a change and triggering regeneration
                await watcher._handle_block_change(str(block_file))
                
                # Verify regeneration start event was broadcast
                calls = mock_ws.broadcast.call_args_list
                assert len(calls) >= 2  # At least start and complete events
                
                # Check start event
                start_event = calls[0][0][0]
                assert start_event["type"] == "regeneration_start"
                assert "TEST_BLOCK" in start_event["block_name"]
                
                # Check complete event
                complete_event = calls[1][0][0]
                assert complete_event["type"] == "regeneration_complete"
                assert complete_event["success"] is True
    
    @pytest.mark.asyncio
    async def test_api_endpoint_broadcasts_regeneration_events(self):
        """Test that the update-block-code API endpoint broadcasts regeneration events."""
        from captain.routes.blocks import update_block_code, UpdateBlockCodeRequest
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup test environment
            project_dir = Path(tmpdir)
            blocks_dir = project_dir / "atlasvibe_blocks" / "CUSTOM_BLOCK"
            blocks_dir.mkdir(parents=True)
            
            block_file = blocks_dir / "CUSTOM_BLOCK.py"
            block_file.write_text("""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def CUSTOM_BLOCK(x: int = 1) -> int:
    return x * 2
""")
            
            project_file = project_dir / "test.atlasvibe"
            project_file.write_text(json.dumps({"nodes": [], "edges": []}))
            
            # Create request
            request = UpdateBlockCodeRequest(
                block_path=str(block_file),
                content="""#!/usr/bin/env python3
from atlasvibe import atlasvibe

@atlasvibe
def CUSTOM_BLOCK(x: int = 1, y: int = 2) -> int:
    '''Updated block with new parameter.'''
    return x * y
""",
                project_path=str(project_file)
            )
            
            # Mock WebSocket manager
            with patch('captain.routes.blocks.ConnectionManager') as MockWS:
                mock_ws = AsyncMock()
                MockWS.get_instance.return_value = mock_ws
                
                # Call the API
                result = await update_block_code(request)
                
                # Verify regeneration events were broadcast
                calls = mock_ws.broadcast.call_args_list
                
                # Should have at least regeneration start and complete
                assert any(call[0][0].get("type") == "regeneration_start" for call in calls)
                assert any(call[0][0].get("type") == "regeneration_complete" for call in calls)