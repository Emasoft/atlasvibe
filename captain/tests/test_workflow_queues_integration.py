#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of integration tests for WorkflowQueueCoordinator
# - Tests two-queue system interaction (WCQ + WEQ)
# - Verifies change processing triggers workflow execution
# - Validates WebSocket event broadcasting
#

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from captain.services.workflow_queue_coordinator import WorkflowQueueCoordinator
from captain.services.workflow_changes_queue import ChangeType
from captain.services.workflow_execution_queue import TopologyRequest
from captain.internal.wsmanager import ConnectionManager as WebSocketManager


class TestWorkflowQueuesIntegration:
    """Integration tests for the two-queue workflow system."""

    @pytest.fixture
    def ws_manager(self):
        """Create a mock WebSocket manager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.broadcast = AsyncMock()
        return manager

    @pytest.fixture
    def simple_topology(self):
        """Create a simple 3-node topology for testing."""
        return TopologyRequest(
            job_id="test-job-123",
            name="Test Workflow",
            graph={
                "nodes": [
                    {
                        "id": "node1",
                        "type": "NUMBER",
                        "data": {"label": "Number Input", "parameters": {"value": 10}},
                    },
                    {
                        "id": "node2",
                        "type": "ADDITION",
                        "data": {"label": "Add Numbers", "parameters": {}},
                    },
                    {
                        "id": "node3",
                        "type": "DISPLAY",
                        "data": {"label": "Show Result", "parameters": {}},
                    },
                ],
                "edges": [
                    {
                        "source": "node1",
                        "target": "node2",
                        "sourceHandle": "output",
                        "targetHandle": "primary_dp",
                    },
                    {
                        "source": "node2",
                        "target": "node3",
                        "sourceHandle": "output",
                        "targetHandle": "input",
                    },
                ],
            },
            project_path="/test/project",
        )

    @pytest.fixture
    def coordinator(self, ws_manager):
        """Create a WorkflowQueueCoordinator instance."""
        return WorkflowQueueCoordinator(ws_manager)

    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, coordinator, ws_manager):
        """Test that coordinator initializes both queues properly."""
        assert coordinator.wcq is not None
        assert coordinator.weq is not None
        assert coordinator.ws_manager == ws_manager
        assert coordinator._running is False
        assert coordinator._pending_execution is False

    @pytest.mark.asyncio
    async def test_set_topology(self, coordinator, simple_topology, ws_manager):
        """Test setting topology in coordinator."""
        # Set topology
        coordinator.set_topology(simple_topology)

        # Verify topology is stored
        assert coordinator._current_topology == simple_topology
        assert coordinator._stats["topology_updates"] == 1

        # Wait for async broadcast
        await asyncio.sleep(0.1)

        # Verify WebSocket broadcast
        ws_manager.broadcast.assert_called()
        call_args = ws_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "coordinator_topology_updated"
        assert call_args["job_id"] == "test-job-123"
        assert call_args["node_count"] == 3
        assert call_args["edge_count"] == 2

    @pytest.mark.asyncio
    async def test_enqueue_change(self, coordinator, simple_topology, ws_manager):
        """Test enqueueing a code change."""
        # Set topology first
        coordinator.set_topology(simple_topology)

        # Enqueue a code change
        change_id = await coordinator.enqueue_change(
            {
                "type": ChangeType.CODE_UPDATE.value,
                "block_id": "node2",
                "data": {
                    "code": "# Updated code\ndef process(inputs):\n    return inputs['primary_dp'] + 5"
                },
            }
        )

        # Verify change was enqueued
        assert change_id is not None
        # Change ID format is timestamp_blockid, not change_
        assert "node2" in change_id

        # Verify WebSocket broadcast
        await asyncio.sleep(0.1)
        broadcast_calls = ws_manager.broadcast.call_args_list

        # Should have at least the enqueue broadcast
        enqueue_broadcast = None
        for call in broadcast_calls:
            if call[0][0]["type"] == "coordinator_change_enqueued":
                enqueue_broadcast = call[0][0]
                break

        assert enqueue_broadcast is not None
        assert enqueue_broadcast["change_id"] == change_id
        assert enqueue_broadcast["change_type"] == ChangeType.CODE_UPDATE.value

    async def _cleanup_coordinator(self, coordinator):
        """Helper to cleanup coordinator after tests."""
        if coordinator and coordinator._running:
            try:
                await coordinator.stop()
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_change_triggers_execution(
        self, coordinator, simple_topology, ws_manager
    ):
        """Test that completing a change triggers workflow execution."""
        # Mock the actual code update and execution to avoid file system operations
        with (
            patch.object(
                coordinator.wcq, "_process_code_update", new_callable=AsyncMock
            ),
            patch.object(
                coordinator.weq, "execute", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_execute.return_value = {"node3": {"output": 15}}

            # Set topology
            coordinator.set_topology(simple_topology)

            # Start coordinator in background
            coordinator_task = asyncio.create_task(coordinator.run())

            try:
                # Give coordinator time to start
                await asyncio.sleep(0.1)

                # Enqueue a change
                await coordinator.enqueue_change(
                    {
                        "type": ChangeType.CODE_UPDATE.value,
                        "block_id": "node2",
                        "data": {"code": "# Updated code"},
                    }
                )

                # Wait for change to be processed and execution to trigger
                await asyncio.sleep(0.5)

                # Verify execution was triggered
                assert coordinator._stats["execution_triggers"] >= 1
                mock_execute.assert_called_once()

                # Verify the topology passed to execute
                executed_topology = mock_execute.call_args[0][0]
                assert executed_topology.job_id == "test-job-123"

            finally:
                # Stop coordinator
                await coordinator.stop()
                try:
                    await asyncio.wait_for(coordinator_task, timeout=2.0)
                except asyncio.TimeoutError:
                    # Force cancel if still running
                    coordinator_task.cancel()
                    try:
                        await coordinator_task
                    except asyncio.CancelledError:
                        pass

    @pytest.mark.asyncio
    async def test_multiple_changes_queued(
        self, coordinator, simple_topology, ws_manager
    ):
        """Test that multiple changes can be queued."""
        # Simple test to verify multiple changes can be enqueued
        coordinator.set_topology(simple_topology)

        # Enqueue multiple changes
        change_ids = []

        # Enqueue first change
        change_id1 = await coordinator.enqueue_change(
            {
                "type": ChangeType.CODE_UPDATE.value,
                "block_id": "node2",
                "data": {"code": "# First update"},
            }
        )
        change_ids.append(change_id1)

        # Enqueue second change
        change_id2 = await coordinator.enqueue_change(
            {
                "type": ChangeType.PARAMETER_UPDATE.value,
                "block_id": "node1",
                "data": {"parameters": {"value": 20}},
            }
        )
        change_ids.append(change_id2)

        # Enqueue third change
        change_id3 = await coordinator.regenerate_manifest("node3")
        change_ids.append(change_id3)

        # Verify all changes were queued
        assert len(change_ids) == 3
        assert all(id is not None for id in change_ids)
        assert len(set(change_ids)) == 3  # All IDs are unique

        # Verify queue status
        status = coordinator.get_status()
        assert status["wcq"]["queue_length"] == 3

    @pytest.mark.asyncio
    async def test_get_status(self, coordinator, simple_topology):
        """Test status reporting."""
        coordinator.set_topology(simple_topology)

        status = coordinator.get_status()

        # Verify status structure
        assert "coordinator" in status
        assert "wcq" in status
        assert "weq" in status

        # Check coordinator status
        assert status["coordinator"]["running"] is False
        assert status["coordinator"]["has_topology"] is True
        assert status["coordinator"]["pending_execution"] is False
        assert "stats" in status["coordinator"]

        # Check queue statuses - based on actual WCQ status structure
        assert "queue_length" in status["wcq"]
        assert "is_processing" in status["wcq"]
        assert "is_running" in status["weq"]

    @pytest.mark.asyncio
    async def test_convenience_methods(self, coordinator, simple_topology):
        """Test convenience methods for common change types."""
        coordinator.set_topology(simple_topology)

        # Test code update
        change_id = await coordinator.update_block_code("node1", "# New code")
        assert change_id is not None

        # Test manifest regeneration
        change_id = await coordinator.regenerate_manifest("node1")
        assert change_id is not None

        # Test metadata update
        change_id = await coordinator.update_metadata(
            "node1", {"description": "Updated"}
        )
        assert change_id is not None

        # Test block rename
        change_id = await coordinator.rename_block("node1", "new_node1")
        assert change_id is not None

        # Test parameter update
        change_id = await coordinator.update_parameters("node1", {"value": 20})
        assert change_id is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, coordinator, simple_topology, ws_manager):
        """Test error handling in execution."""
        # Mock execution to raise an error
        with patch.object(
            coordinator.weq, "execute", side_effect=Exception("Test error")
        ):
            coordinator.set_topology(simple_topology)

            # Manually trigger execution
            coordinator._pending_execution = True
            await coordinator._trigger_execution()

            # Verify error broadcast
            await asyncio.sleep(0.1)

            # Find error broadcast
            error_broadcast = None
            for call in ws_manager.broadcast.call_args_list:
                if call[0][0]["type"] == "coordinator_execution_error":
                    error_broadcast = call[0][0]
                    break

            assert error_broadcast is not None
            assert error_broadcast["job_id"] == "test-job-123"
            assert "Test error" in error_broadcast["error"]

    @pytest.mark.asyncio
    async def test_wcq_completion_callback(self, coordinator, simple_topology):
        """Test that WCQ completion callback is properly set up."""
        # Verify callback is set
        assert coordinator.wcq._completion_callback is not None
        assert coordinator.wcq._completion_callback == coordinator._on_change_complete

        # Test callback directly
        await coordinator._on_change_complete()

        # Verify it sets pending execution
        assert coordinator._pending_execution is True
        assert coordinator._stats["execution_triggers"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
