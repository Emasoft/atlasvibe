#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of WorkflowExecutionQueue (WEQ)
# - Topology-aware execution respecting node dependencies
# - Parallel execution of independent nodes
# - Cancellable execution when new changes arrive
# - Output tracking and comparison between executions
# - WebSocket broadcasting of execution status and results

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass, field
import traceback

from prefect import flow

from captain.internal.wsmanager import ConnectionManager as WebSocketManager
# from captain.services.consumer.blocks_executor import execute_block  # TODO: implement
# from captain.utils.import_blocks import get_block_function  # TODO: implement

# Create simple model for workflow execution
from pydantic import BaseModel


class TopologyRequest(BaseModel):
    job_id: str
    name: str
    graph: Dict[str, Any]
    project_path: Optional[str] = None


logger = logging.getLogger(__name__)


@dataclass
class NodeExecution:
    """Represents execution state of a single node."""

    node_id: str
    node_type: str
    status: str = "pending"  # pending, running, completed, failed, cancelled
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)


class WorkflowExecutionQueue:
    """
    Topology-aware queue for executing workflows.

    Executes nodes in parallel when possible, respecting dependencies.
    Can be cancelled and restarted when new changes arrive.
    """

    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self._current_execution: Optional[asyncio.Task] = None
        self._cancel_requested = False
        self._is_running = False
        self._total_executions = 0
        self._last_outputs: Optional[Dict[str, Any]] = None
        self._current_topology: Optional[TopologyRequest] = None
        self._node_executions: Dict[str, NodeExecution] = {}
        self._execution_id: Optional[str] = None

    async def execute(self, topology: TopologyRequest) -> Optional[Dict[str, Any]]:
        """
        Execute workflow topology with dependency awareness.

        Returns outputs or None if cancelled.
        """
        self._execution_id = f"exec_{datetime.now().timestamp()}"
        self._current_topology = topology
        self._cancel_requested = False
        self._is_running = True
        self._total_executions += 1

        # Broadcast execution start
        await self._broadcast_status(
            "weq_started",
            {
                "execution_id": self._execution_id,
                "job_id": topology.job_id,
                "node_count": len(topology.graph["nodes"]),
                "edge_count": len(topology.graph["edges"]),
            },
        )

        try:
            # Build execution graph
            self._build_execution_graph(topology)

            # Execute with Prefect flow
            outputs = await self._execute_workflow_flow(topology)

            if self._cancel_requested:
                await self._broadcast_status(
                    "weq_cancelled", {"execution_id": self._execution_id}
                )
                return None

            # Store outputs for comparison
            self._last_outputs = outputs

            # Broadcast completion
            await self._broadcast_status(
                "weq_complete",
                {
                    "execution_id": self._execution_id,
                    "outputs": self._serialize_outputs(outputs),
                },
            )

            return outputs

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            logger.error(traceback.format_exc())

            await self._broadcast_status(
                "weq_error", {"execution_id": self._execution_id, "error": str(e)}
            )

            return None

        finally:
            self._is_running = False
            self._node_executions.clear()

    def cancel(self):
        """Cancel current execution."""
        logger.info(f"Cancelling execution {self._execution_id}")
        self._cancel_requested = True

        if self._current_execution and not self._current_execution.done():
            self._current_execution.cancel()

    def compare_outputs(
        self, outputs1: Dict[str, Any], outputs2: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Compare outputs from two executions.

        Returns list of differences.
        """
        differences = []

        # Check all nodes from first execution
        for node_id, output1 in outputs1.items():
            output2 = outputs2.get(node_id)

            if output2 is None:
                differences.append(
                    {
                        "node_id": node_id,
                        "type": "missing_in_second",
                        "output1": output1,
                        "output2": None,
                    }
                )
            elif output1 != output2:
                differences.append(
                    {
                        "node_id": node_id,
                        "type": "value_changed",
                        "output1": output1,
                        "output2": output2,
                    }
                )

        # Check for nodes only in second execution
        for node_id, output2 in outputs2.items():
            if node_id not in outputs1:
                differences.append(
                    {
                        "node_id": node_id,
                        "type": "missing_in_first",
                        "output1": None,
                        "output2": output2,
                    }
                )

        return differences

    def _build_execution_graph(self, topology: TopologyRequest):
        """Build execution graph with dependencies."""
        self._node_executions.clear()

        # Create node execution objects
        nodes_by_id = {}
        for node_data in topology.graph["nodes"]:
            node_id = node_data["id"]
            node_exec = NodeExecution(
                node_id=node_id,
                node_type=node_data.get("type", ""),
            )
            self._node_executions[node_id] = node_exec
            nodes_by_id[node_id] = node_data

        # Build dependencies from edges
        for edge_data in topology.graph["edges"]:
            source = edge_data["source"]
            target = edge_data["target"]

            if source in self._node_executions and target in self._node_executions:
                self._node_executions[target].dependencies.add(source)
                self._node_executions[source].dependents.add(target)

    @flow(name="workflow_execution", validate_parameters=False)
    async def _execute_workflow_flow(self, topology: TopologyRequest) -> Dict[str, Any]:
        """Execute workflow as a Prefect flow."""
        outputs = {}

        # Find nodes with no dependencies (entry points)
        ready_nodes = self._get_ready_nodes()

        # Execute nodes in waves based on dependencies
        while ready_nodes and not self._cancel_requested:
            # Execute ready nodes in parallel
            tasks = []
            for node_id in ready_nodes:
                if self._cancel_requested:
                    break

                node_exec = self._node_executions[node_id]
                node_data = self._get_node_data(topology, node_id)

                # Gather inputs from dependencies
                inputs = self._gather_node_inputs(node_id, outputs)
                node_exec.inputs = inputs

                # Create execution task
                task = asyncio.create_task(
                    self._execute_node_task(node_id, node_data, inputs)
                )
                tasks.append((node_id, task))

            # Wait for parallel execution
            for node_id, task in tasks:
                try:
                    output = await task
                    if output is not None:
                        outputs[node_id] = output
                        self._node_executions[node_id].outputs = output
                        self._node_executions[node_id].status = "completed"
                except Exception as e:
                    logger.error(f"Error executing node {node_id}: {e}")
                    self._node_executions[node_id].status = "failed"
                    self._node_executions[node_id].error = str(e)

            # Get next wave of ready nodes
            ready_nodes = self._get_ready_nodes()

        return outputs

    async def _execute_node_task(
        self, node_id: str, node_data: Dict[str, Any], inputs: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute a single node."""
        node_exec = self._node_executions[node_id]
        node_exec.status = "running"
        node_exec.start_time = datetime.now()

        # Broadcast node execution start
        await self._broadcast_status(
            "node_executing",
            {
                "execution_id": self._execution_id,
                "node_id": node_id,
                "node_type": node_data.get("type", ""),
                "inputs": self._serialize_outputs(inputs),
            },
        )

        try:
            # Execute the node
            output = await self._execute_node(node_id, inputs)

            node_exec.end_time = datetime.now()

            # Broadcast node completion
            await self._broadcast_status(
                "node_complete",
                {
                    "execution_id": self._execution_id,
                    "node_id": node_id,
                    "output": self._serialize_outputs(output),
                    "duration_ms": int(
                        (node_exec.end_time - node_exec.start_time).total_seconds()
                        * 1000
                    ),
                },
            )

            return output

        except Exception as e:
            node_exec.end_time = datetime.now()

            # Broadcast node error
            await self._broadcast_status(
                "node_error",
                {
                    "execution_id": self._execution_id,
                    "node_id": node_id,
                    "error": str(e),
                },
            )

            raise

    async def _execute_node(
        self, node_id: str, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single node.

        This is where the actual block execution happens.
        In the real implementation, this would call the block executor.
        """
        # Simulate execution time
        await asyncio.sleep(0.01)

        # Check for cancellation
        if self._cancel_requested:
            raise asyncio.CancelledError("Execution cancelled")

        # In real implementation, this would:
        # 1. Get the block function for the node
        # 2. Execute it with the inputs
        # 3. Return the outputs

        # For now, simulate output
        return {"result": f"output_{node_id}", "value": 42}

    def _get_ready_nodes(self) -> Set[str]:
        """Get nodes that are ready to execute (all dependencies completed)."""
        ready = set()

        for node_id, node_exec in self._node_executions.items():
            if node_exec.status != "pending":
                continue

            # Check if all dependencies are completed
            all_deps_complete = all(
                self._node_executions[dep_id].status == "completed"
                for dep_id in node_exec.dependencies
            )

            if all_deps_complete:
                ready.add(node_id)

        return ready

    def _gather_node_inputs(
        self, node_id: str, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gather inputs for a node from its dependencies."""
        node_exec = self._node_executions[node_id]
        inputs = {}

        # Collect outputs from dependencies
        for dep_id in node_exec.dependencies:
            if dep_id in outputs:
                inputs[dep_id] = outputs[dep_id]

        return inputs

    def _get_node_data(self, topology: TopologyRequest, node_id: str) -> Dict[str, Any]:
        """Get node data from topology."""
        for node in topology.graph["nodes"]:
            if node["id"] == node_id:
                return node
        return {}

    def _serialize_outputs(self, outputs: Any) -> Any:
        """Serialize outputs for WebSocket transmission."""
        if outputs is None:
            return None

        # Handle different output types
        if isinstance(outputs, dict):
            return {k: self._serialize_outputs(v) for k, v in outputs.items()}
        elif isinstance(outputs, list):
            return [self._serialize_outputs(item) for item in outputs]
        elif isinstance(outputs, (str, int, float, bool)):
            return outputs
        else:
            # Convert complex objects to string
            return str(outputs)

    async def _broadcast_status(self, message_type: str, data: Dict[str, Any]):
        """Broadcast status update via WebSocket."""
        message = {
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        }
        await self.ws_manager.broadcast(message)

    def get_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        return {
            "is_running": self._is_running,
            "execution_id": self._execution_id,
            "total_executions": self._total_executions,
            "cancel_requested": self._cancel_requested,
            "node_statuses": {
                node_id: {
                    "status": node_exec.status,
                    "dependencies": list(node_exec.dependencies),
                    "dependents": list(node_exec.dependents),
                }
                for node_id, node_exec in self._node_executions.items()
            }
            if self._node_executions
            else {},
        }

    def get_last_outputs(self) -> Optional[Dict[str, Any]]:
        """Get outputs from the last execution."""
        return self._last_outputs
