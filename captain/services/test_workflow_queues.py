#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of test suite for two-queue workflow system
# - Tests for WorkflowChangesQueue (WCQ) sequential processing
# - Tests for WorkflowExecutionQueue (WEQ) topology-aware execution
# - Tests for queue coordination and cancellation behavior
# - Tests for WebSocket broadcasting and status tracking

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel

from captain.services.workflow_changes_queue import WorkflowChangesQueue, ChangeType
from captain.services.workflow_execution_queue import WorkflowExecutionQueue
from captain.services.workflow_queue_coordinator import WorkflowQueueCoordinator
from captain.internal.wsmanager import ConnectionManager as WebSocketManager


# Create a simple TopologyRequest model for testing
class TopologyRequest(BaseModel):
    job_id: str
    name: str
    graph: Dict[str, Any]  # Contains 'nodes' and 'edges'
    project_path: Optional[str] = None


class TestWorkflowChangesQueue:
    """Test suite for WorkflowChangesQueue sequential processing."""

    @pytest.fixture
    def wcq(self):
        """Create WorkflowChangesQueue instance with mocked WebSocket."""
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.broadcast = AsyncMock()
        return WorkflowChangesQueue(ws_manager)

    @pytest.mark.asyncio
    async def test_enqueue_returns_immediately(self, wcq):
        """Test that enqueue returns within milliseconds."""
        start_time = asyncio.get_event_loop().time()

        change = {
            "type": ChangeType.CODE_UPDATE,
            "block_id": "test_block_1",
            "data": {"code": "def test(): pass"},
        }

        await wcq.enqueue(change)

        elapsed = asyncio.get_event_loop().time() - start_time
        assert elapsed < 0.01  # Should return in under 10ms

    @pytest.mark.asyncio
    async def test_changes_processed_sequentially(self, wcq):
        """Test that changes are processed in exact order."""
        processed_order = []

        async def mock_process(change):
            processed_order.append(change["block_id"])
            await asyncio.sleep(0.01)  # Simulate processing time

        wcq._process_change = mock_process

        # Enqueue multiple changes
        for i in range(5):
            await wcq.enqueue(
                {"type": ChangeType.CODE_UPDATE, "block_id": f"block_{i}", "data": {}}
            )

        # Start processing
        process_task = asyncio.create_task(wcq.start())
        await asyncio.sleep(0.1)  # Let it process
        wcq.stop()
        await process_task

        # Verify sequential order
        assert processed_order == [
            "block_0",
            "block_1",
            "block_2",
            "block_3",
            "block_4",
        ]

    @pytest.mark.asyncio
    async def test_code_update_processing(self, wcq):
        """Test code update change processing."""
        with patch(
            "captain.services.workflow_changes_queue.update_block_code",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = True

            change = {
                "type": ChangeType.CODE_UPDATE,
                "block_id": "test_block",
                "data": {"code": "def new_function(): return 42"},
            }

            result = await wcq._process_change(change)

            assert result is True
            # update_block_code takes 3 params: block_id, code, project_path
            mock_update.assert_called_once_with(
                "test_block", "def new_function(): return 42", None
            )

    @pytest.mark.asyncio
    async def test_manifest_regeneration_processing(self, wcq):
        """Test manifest regeneration processing."""
        with patch(
            "captain.services.workflow_changes_queue.regenerate_manifest",
            new_callable=AsyncMock,
        ) as mock_regen:
            mock_regen.return_value = {"inputs": [], "outputs": []}

            change = {
                "type": ChangeType.MANIFEST_REGEN,
                "block_id": "test_block",
                "data": {},
            }

            result = await wcq._process_change(change)

            assert result == {"inputs": [], "outputs": []}
            # regenerate_manifest is called with the block's file path, not just block_id
            assert mock_regen.called

    @pytest.mark.asyncio
    async def test_websocket_progress_broadcasting(self, wcq):
        """Test WebSocket messages during processing."""

        with patch(
            "captain.services.workflow_changes_queue.update_block_code",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = True

            # Use _process_change_wrapper to get full WebSocket broadcasts
            workflow_change = wcq._current_change = type(
                "obj",
                (object,),
                {
                    "id": "test_id",
                    "type": ChangeType.CODE_UPDATE,
                    "block_id": "test_block",
                    "data": {"code": "pass"},
                    "timestamp": datetime.now(),
                    "status": "pending",
                },
            )()

            await wcq._process_change_wrapper(workflow_change)

        # Check WebSocket messages
        calls = wcq.ws_manager.broadcast.call_args_list
        assert len(calls) >= 2  # Start and complete messages

        # Find processing and complete messages
        messages = [call[0][0] for call in calls]
        processing_msg = next(
            (m for m in messages if m["type"] == "wcq_processing"), None
        )
        complete_msg = next((m for m in messages if m["type"] == "wcq_complete"), None)

        assert processing_msg is not None
        assert processing_msg["change_type"] == "CODE_UPDATE"

        assert complete_msg is not None

    @pytest.mark.asyncio
    async def test_completion_callback_triggered(self, wcq):
        """Test that completion callback is called after processing."""
        callback_called = False

        async def completion_callback():
            nonlocal callback_called
            callback_called = True

        wcq.set_completion_callback(completion_callback)

        with patch(
            "captain.services.workflow_changes_queue.update_block_code",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = True

            # Use _process_change_wrapper to trigger the callback
            workflow_change = type(
                "obj",
                (object,),
                {
                    "id": "test_id",
                    "type": ChangeType.CODE_UPDATE,
                    "block_id": "test_block",
                    "data": {"code": "pass"},
                    "timestamp": datetime.now(),
                    "status": "pending",
                    "result": None,
                    "error": None,
                },
            )()

            await wcq._process_change_wrapper(workflow_change)

        assert callback_called is True


class TestWorkflowExecutionQueue:
    """Test suite for WorkflowExecutionQueue topology-aware execution."""

    @pytest.fixture
    def topology(self):
        """Create sample topology for testing."""
        return TopologyRequest(
            job_id="test_job",
            name="Test Workflow",
            graph={
                "nodes": [
                    {"id": "node1", "type": "INPUT", "data": {"value": 1}},
                    {"id": "node2", "type": "ADD", "data": {"value": 2}},
                    {"id": "node3", "type": "MULTIPLY", "data": {"value": 3}},
                    {"id": "node4", "type": "OUTPUT", "data": {}},
                ],
                "edges": [
                    {"id": "e1", "source": "node1", "target": "node2"},
                    {"id": "e2", "source": "node2", "target": "node3"},
                    {"id": "e3", "source": "node3", "target": "node4"},
                ],
            },
        )

    @pytest.fixture
    def weq(self):
        """Create WorkflowExecutionQueue instance."""
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.broadcast = AsyncMock()
        return WorkflowExecutionQueue(ws_manager)

    @pytest.mark.asyncio
    async def test_topology_aware_execution(self, weq, topology):
        """Test that execution respects node dependencies."""
        execution_order = []

        async def mock_execute_node(node_id, inputs):
            execution_order.append(node_id)
            return {"result": f"output_{node_id}"}

        with patch.object(weq, "_execute_node", mock_execute_node):
            await weq.execute(topology)

        # Verify execution order respects dependencies
        assert execution_order.index("node1") < execution_order.index("node2")
        assert execution_order.index("node2") < execution_order.index("node3")
        assert execution_order.index("node3") < execution_order.index("node4")

    @pytest.mark.asyncio
    async def test_parallel_execution_of_independent_nodes(self, weq):
        """Test parallel execution of nodes without dependencies."""
        topology = TopologyRequest(
            job_id="parallel_test",
            name="Parallel Test",
            graph={
                "nodes": [
                    {"id": "input1", "type": "INPUT", "data": {"value": 1}},
                    {"id": "input2", "type": "INPUT", "data": {"value": 2}},
                    {"id": "process1", "type": "ADD", "data": {}},
                    {"id": "process2", "type": "MULTIPLY", "data": {}},
                    {"id": "output", "type": "OUTPUT", "data": {}},
                ],
                "edges": [
                    {"id": "e1", "source": "input1", "target": "process1"},
                    {"id": "e2", "source": "input2", "target": "process2"},
                    {"id": "e3", "source": "process1", "target": "output"},
                    {"id": "e4", "source": "process2", "target": "output"},
                ],
            },
        )

        execution_times = {}

        async def mock_execute_node(node_id, inputs):
            start_time = asyncio.get_event_loop().time()
            await asyncio.sleep(0.05)  # Simulate processing
            execution_times[node_id] = start_time
            return {"result": f"output_{node_id}"}

        with patch.object(weq, "_execute_node", mock_execute_node):
            await weq.execute(topology)

        # Verify parallel execution
        # input1 and input2 should start at similar times
        time_diff = abs(execution_times["input1"] - execution_times["input2"])
        assert time_diff < 0.01  # Should be nearly simultaneous

        # process1 and process2 should also run in parallel
        time_diff = abs(execution_times["process1"] - execution_times["process2"])
        assert time_diff < 0.01

    @pytest.mark.asyncio
    async def test_execution_cancellation(self, weq, topology):
        """Test that execution can be cancelled mid-flow."""
        execution_count = 0

        async def mock_execute_node(node_id, inputs):
            nonlocal execution_count
            execution_count += 1
            if execution_count == 2:
                # Cancel after second node
                weq.cancel()
            await asyncio.sleep(0.01)
            return {"result": f"output_{node_id}"}

        with patch.object(weq, "_execute_node", mock_execute_node):
            result = await weq.execute(topology)

        assert result is None  # Cancelled execution returns None
        assert execution_count < 4  # Not all nodes executed

    @pytest.mark.asyncio
    async def test_output_tracking_and_comparison(self, weq, topology):
        """Test output tracking and difference detection."""
        # First execution
        with patch.object(weq, "_execute_node") as mock_exec:
            mock_exec.return_value = {"value": 42}
            outputs1 = await weq.execute(topology)

        # Second execution with different output
        with patch.object(weq, "_execute_node") as mock_exec:
            mock_exec.return_value = {"value": 43}
            outputs2 = await weq.execute(topology)

        # Compare outputs
        differences = weq.compare_outputs(outputs1, outputs2)
        assert len(differences) > 0
        assert any(diff["node_id"] == "node4" for diff in differences)

    @pytest.mark.asyncio
    async def test_websocket_execution_status_broadcasting(self, weq, topology):
        """Test WebSocket status updates during execution."""
        with patch.object(weq, "_execute_node") as mock_exec:
            mock_exec.return_value = {"result": "test"}
            await weq.execute(topology)

        # Check WebSocket messages
        calls = weq.ws_manager.broadcast.call_args_list
        messages = [call[0][0] for call in calls]  # Already dicts, no json.loads needed

        # Verify execution lifecycle messages
        assert any(msg["type"] == "weq_started" for msg in messages)
        assert any(msg["type"] == "node_executing" for msg in messages)
        assert any(msg["type"] == "node_complete" for msg in messages)
        assert any(msg["type"] == "weq_complete" for msg in messages)


class TestWorkflowQueueCoordinator:
    """Test suite for queue coordination."""

    @pytest.fixture
    def coordinator(self):
        """Create WorkflowQueueCoordinator instance."""
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.broadcast = AsyncMock()
        return WorkflowQueueCoordinator(ws_manager)

    @pytest.mark.asyncio
    async def test_wcq_completion_triggers_weq_restart(self, coordinator):
        """Test WCQ completion cancels and restarts WEQ."""
        topology = TopologyRequest(
            job_id="test", name="Test", graph={"nodes": [], "edges": []}
        )

        # Set topology
        coordinator.set_topology(topology)

        # Mock WEQ methods
        coordinator.weq.cancel = Mock()
        coordinator.weq.execute = AsyncMock(return_value={"result": "test"})

        # Simulate change and completion
        await coordinator.enqueue_change(
            {
                "type": ChangeType.CODE_UPDATE,
                "block_id": "test",
                "data": {"code": "pass"},
            }
        )

        # Wait for processing
        await asyncio.sleep(0.1)

        # Verify WEQ was cancelled and restarted
        coordinator.weq.cancel.assert_called()
        coordinator.weq.execute.assert_called_with(topology)

    @pytest.mark.asyncio
    async def test_multiple_changes_single_execution(self, coordinator):
        """Test multiple rapid changes result in single execution."""
        topology = TopologyRequest(
            job_id="test", name="Test", graph={"nodes": [], "edges": []}
        )

        coordinator.set_topology(topology)

        execution_count = 0

        async def mock_execute(topo):
            nonlocal execution_count
            execution_count += 1
            await asyncio.sleep(0.05)  # Simulate execution time
            return {"result": "test"}

        coordinator.weq.execute = mock_execute

        # Enqueue multiple changes rapidly
        for i in range(5):
            await coordinator.enqueue_change(
                {
                    "type": ChangeType.CODE_UPDATE,
                    "block_id": f"block_{i}",
                    "data": {"code": "pass"},
                }
            )

        # Wait for all processing
        await asyncio.sleep(0.5)

        # Should only execute once after all changes
        assert execution_count == 1

    @pytest.mark.asyncio
    async def test_status_tracking_both_queues(self, coordinator):
        """Test status tracking for both queues."""
        status = coordinator.get_status()

        assert "wcq" in status
        assert "weq" in status
        assert status["wcq"]["queue_length"] == 0
        assert status["weq"]["is_running"] is False

        # Enqueue a change
        await coordinator.enqueue_change(
            {
                "type": ChangeType.CODE_UPDATE,
                "block_id": "test",
                "data": {"code": "pass"},
            }
        )

        status = coordinator.get_status()
        assert status["wcq"]["queue_length"] > 0

    @pytest.mark.asyncio
    async def test_unified_interface(self, coordinator):
        """Test unified interface for application integration."""
        # Test topology setting
        topology = TopologyRequest(
            job_id="test", name="Test", graph={"nodes": [], "edges": []}
        )
        coordinator.set_topology(topology)

        # Test change enqueuing
        await coordinator.enqueue_change(
            {
                "type": ChangeType.CODE_UPDATE,
                "block_id": "test",
                "data": {"code": "pass"},
            }
        )

        # Test status retrieval
        status = coordinator.get_status()
        assert isinstance(status, dict)

        # Test stopping
        await coordinator.stop()
        assert coordinator._running is False


class TestIntegration:
    """Integration tests for the complete two-queue system."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_changes(self):
        """Test complete workflow with multiple changes and executions."""
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.broadcast = AsyncMock()

        coordinator = WorkflowQueueCoordinator(ws_manager)

        # Create a workflow topology
        topology = TopologyRequest(
            job_id="integration_test",
            name="Integration Test",
            graph={
                "nodes": [
                    {"id": "input", "type": "INPUT", "data": {"value": 10}},
                    {"id": "process", "type": "CUSTOM", "data": {}},
                    {"id": "output", "type": "OUTPUT", "data": {}},
                ],
                "edges": [
                    {"id": "e1", "source": "input", "target": "process"},
                    {"id": "e2", "source": "process", "target": "output"},
                ],
            },
        )

        coordinator.set_topology(topology)

        # Start coordinator
        run_task = asyncio.create_task(coordinator.run())

        # Simulate user making changes
        await coordinator.enqueue_change(
            {
                "type": ChangeType.CODE_UPDATE,
                "block_id": "process",
                "data": {"code": "def process(x): return x * 2"},
            }
        )

        await asyncio.sleep(0.1)

        await coordinator.enqueue_change(
            {
                "type": ChangeType.METADATA_UPDATE,
                "block_id": "process",
                "data": {"description": "Doubles the input"},
            }
        )

        await asyncio.sleep(0.1)

        # Stop coordinator
        await coordinator.stop()
        await run_task

        # Verify WebSocket messages were sent
        assert ws_manager.broadcast.call_count > 0

        # Verify final status
        status = coordinator.get_status()
        assert status["wcq"]["total_processed"] == 2
        assert status["weq"]["total_executions"] >= 1


# Performance tests
class TestPerformance:
    """Performance tests for queue system."""

    @pytest.mark.asyncio
    async def test_enqueue_performance(self):
        """Test that enqueue maintains millisecond response time under load."""
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.broadcast = AsyncMock()

        wcq = WorkflowChangesQueue(ws_manager)

        # Enqueue 1000 changes and measure time
        start_time = asyncio.get_event_loop().time()

        for i in range(1000):
            await wcq.enqueue(
                {
                    "type": ChangeType.CODE_UPDATE,
                    "block_id": f"block_{i}",
                    "data": {"code": f"# Change {i}"},
                }
            )

        total_time = asyncio.get_event_loop().time() - start_time
        avg_time = total_time / 1000

        # Average enqueue time should be under 1ms
        assert avg_time < 0.001

    @pytest.mark.asyncio
    async def test_topology_execution_performance(self):
        """Test execution performance with large topologies."""
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.broadcast = AsyncMock()

        weq = WorkflowExecutionQueue(ws_manager)

        # Create large topology (100 nodes)
        nodes = [{"id": f"node_{i}", "type": "PROCESS", "data": {}} for i in range(100)]
        edges = [
            {"id": f"e_{i}", "source": f"node_{i}", "target": f"node_{i + 1}"}
            for i in range(99)
        ]

        topology = TopologyRequest(
            job_id="perf_test",
            name="Performance Test",
            graph={"nodes": nodes, "edges": edges},
        )

        # Mock fast execution
        async def mock_execute_node(node_id, inputs):
            return {"result": f"output_{node_id}"}

        with patch.object(weq, "_execute_node", mock_execute_node):
            start_time = asyncio.get_event_loop().time()
            await weq.execute(topology)
            execution_time = asyncio.get_event_loop().time() - start_time

        # Should handle 100 nodes efficiently
        assert execution_time < 1.0  # Under 1 second for 100 nodes
