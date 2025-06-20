#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of WorkflowQueueCoordinator
# - Coordinates between WCQ and WEQ queues
# - Handles WCQ completion triggering WEQ cancellation and restart
# - Provides unified interface for the application
# - Tracks status of both queues

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from captain.internal.wsmanager import ConnectionManager as WebSocketManager
from captain.services.workflow_changes_queue import WorkflowChangesQueue, ChangeType
from captain.services.workflow_execution_queue import (
    WorkflowExecutionQueue,
    TopologyRequest,
)

logger = logging.getLogger(__name__)


class WorkflowQueueCoordinator:
    """
    Coordinates between WorkflowChangesQueue and WorkflowExecutionQueue.

    Ensures that:
    1. Changes are processed sequentially
    2. Each completed change triggers workflow re-execution
    3. Running executions are cancelled when new changes complete
    4. Both queues operate independently in parallel
    """

    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager

        # Initialize queues
        self.wcq = WorkflowChangesQueue(ws_manager)
        self.weq = WorkflowExecutionQueue(ws_manager)

        # Set up WCQ completion callback
        self.wcq.set_completion_callback(self._on_change_complete)

        # State tracking
        self._current_topology: Optional[TopologyRequest] = None
        self._pending_execution = False
        self._execution_lock = asyncio.Lock()
        self._running = False
        self._coordinator_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = {
            "coordinator_started": datetime.now(),
            "topology_updates": 0,
            "execution_triggers": 0,
            "execution_cancellations": 0,
        }

    async def run(self):
        """Run the coordinator."""
        self._running = True
        logger.info("WorkflowQueueCoordinator started")

        # Start WCQ processing
        wcq_task = asyncio.create_task(self.wcq.start())

        try:
            # Keep coordinator running
            while self._running:
                await asyncio.sleep(0.1)

                # Check if we have a pending execution
                if self._pending_execution and self._current_topology:
                    await self._trigger_execution()

        except Exception as e:
            logger.error(f"Error in coordinator: {e}")

        finally:
            # Stop WCQ
            self.wcq.stop()
            await wcq_task
            self._running = False
            logger.info("WorkflowQueueCoordinator stopped")

    async def stop(self):
        """Stop the coordinator and both queues."""
        logger.info("Stopping WorkflowQueueCoordinator")
        self._running = False

        # Cancel any running execution
        self.weq.cancel()

        # Stop WCQ
        self.wcq.stop()

        # Wait for coordinator task to complete
        if self._coordinator_task and not self._coordinator_task.done():
            await self._coordinator_task

    def set_topology(self, topology: TopologyRequest):
        """
        Set the current workflow topology.

        This should be called whenever the workflow structure changes.
        """
        self._current_topology = topology
        self._stats["topology_updates"] += 1

        logger.info(
            f"Topology updated: {topology.job_id} with {len(topology.graph['nodes'])} nodes"
        )

        # Broadcast topology update
        asyncio.create_task(
            self._broadcast_status(
                "topology_updated",
                {
                    "job_id": topology.job_id,
                    "node_count": len(topology.graph["nodes"]),
                    "edge_count": len(topology.graph["edges"]),
                },
            )
        )

    async def enqueue_change(self, change: Dict[str, Any]) -> str:
        """
        Enqueue a change for processing.

        Returns immediately with change ID.
        """
        # Validate change
        if "type" not in change or "block_id" not in change:
            raise ValueError("Change must have 'type' and 'block_id'")

        # Add project path if we have a topology
        if self._current_topology and "project_path" not in change.get("data", {}):
            change["data"] = change.get("data", {})
            change["data"]["project_path"] = getattr(
                self._current_topology, "project_path", None
            )

        # Enqueue to WCQ
        change_id = await self.wcq.enqueue(change)

        # Broadcast coordinator status
        await self._broadcast_status(
            "change_enqueued",
            {
                "change_id": change_id,
                "change_type": change["type"],
                "wcq_status": self.wcq.get_status(),
                "weq_status": self.weq.get_status(),
            },
        )

        return change_id

    async def _on_change_complete(self):
        """
        Called when a change finishes processing in WCQ.

        This triggers workflow re-execution.
        """
        logger.info("Change processing completed, triggering workflow execution")
        self._pending_execution = True
        self._stats["execution_triggers"] += 1

        # Cancel any running execution
        if self.weq._is_running:
            logger.info("Cancelling current execution due to new change")
            self.weq.cancel()
            self._stats["execution_cancellations"] += 1

            # Wait a bit for cancellation to process
            await asyncio.sleep(0.1)

    async def _trigger_execution(self):
        """Trigger workflow execution with current topology."""
        async with self._execution_lock:
            if not self._pending_execution or not self._current_topology:
                return

            self._pending_execution = False

            logger.info(
                f"Starting workflow execution for job {self._current_topology.job_id}"
            )

            # Broadcast execution trigger
            await self._broadcast_status(
                "execution_triggered",
                {
                    "job_id": self._current_topology.job_id,
                    "trigger_reason": "change_complete",
                    "wcq_processed": self.wcq._total_processed,
                },
            )

            try:
                # Execute workflow
                outputs = await self.weq.execute(self._current_topology)

                if outputs:
                    # Compare with previous outputs if available
                    last_outputs = self.weq.get_last_outputs()
                    if last_outputs and last_outputs != outputs:
                        differences = self.weq.compare_outputs(last_outputs, outputs)

                        # Broadcast output differences
                        await self._broadcast_status(
                            "output_differences",
                            {
                                "job_id": self._current_topology.job_id,
                                "differences": differences,
                            },
                        )

            except Exception as e:
                logger.error(f"Error executing workflow: {e}")

                # Broadcast execution error
                await self._broadcast_status(
                    "execution_error",
                    {"job_id": self._current_topology.job_id, "error": str(e)},
                )

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of both queues."""
        return {
            "coordinator": {
                "running": self._running,
                "has_topology": self._current_topology is not None,
                "pending_execution": self._pending_execution,
                "stats": self._stats,
            },
            "wcq": self.wcq.get_status(),
            "weq": self.weq.get_status(),
        }

    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status including execution history."""
        status = self.get_status()

        # Add execution history if available
        if self.weq._last_outputs:
            status["last_execution"] = {
                "outputs": self.weq._last_outputs,
                "execution_id": self.weq._execution_id,
            }

        return status

    async def _broadcast_status(self, message_type: str, data: Dict[str, Any]):
        """Broadcast coordinator status update via WebSocket."""
        message = {
            "type": f"coordinator_{message_type}",
            "timestamp": datetime.now().isoformat(),
            **data,
        }
        await self.ws_manager.broadcast(message)

    # Convenience methods for common change types

    async def update_block_code(self, block_id: str, code: str) -> str:
        """Update block code."""
        return await self.enqueue_change(
            {
                "type": ChangeType.CODE_UPDATE.value,
                "block_id": block_id,
                "data": {"code": code},
            }
        )

    async def regenerate_manifest(self, block_id: str) -> str:
        """Regenerate block manifest."""
        return await self.enqueue_change(
            {"type": ChangeType.MANIFEST_REGEN.value, "block_id": block_id, "data": {}}
        )

    async def update_metadata(self, block_id: str, metadata: Dict[str, Any]) -> str:
        """Update block metadata."""
        return await self.enqueue_change(
            {
                "type": ChangeType.METADATA_UPDATE.value,
                "block_id": block_id,
                "data": {"metadata": metadata},
            }
        )

    async def rename_block(self, old_block_id: str, new_block_id: str) -> str:
        """Rename a block."""
        return await self.enqueue_change(
            {
                "type": ChangeType.BLOCK_RENAME.value,
                "block_id": old_block_id,
                "data": {"new_block_id": new_block_id},
            }
        )

    async def update_connections(
        self, block_id: str, connections: Dict[str, Any]
    ) -> str:
        """Update block connections."""
        return await self.enqueue_change(
            {
                "type": ChangeType.CONNECTION_CHANGE.value,
                "block_id": block_id,
                "data": {"connections": connections},
            }
        )

    async def update_parameters(self, block_id: str, parameters: Dict[str, Any]) -> str:
        """Update block parameters."""
        return await self.enqueue_change(
            {
                "type": ChangeType.PARAMETER_UPDATE.value,
                "block_id": block_id,
                "data": {"parameters": parameters},
            }
        )
