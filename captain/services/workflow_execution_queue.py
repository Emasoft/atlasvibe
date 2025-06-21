#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of WorkflowExecutionQueue (WEQ)
# - Topology-aware execution respecting node dependencies
# - Parallel execution of independent nodes
# - Cancellable execution when new changes arrive
# - Output tracking and comparison between executions
# - WebSocket broadcasting of execution status and results
# - Updated to use PrefectTopologyExecutor for hybrid execution

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass, field
import traceback
import networkx as nx

from captain.internal.wsmanager import ConnectionManager as WebSocketManager
from captain.models.topology import Topology
from captain.models.workflow_queue import TopologyRequest
from captain.services.prefect_topology_executor import PrefectTopologyExecutor
from captain.utils.import_blocks import pre_import_functions


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
    Uses PrefectTopologyExecutor for hybrid Prefect-Topology execution.
    """

    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self._current_execution: Optional[asyncio.Task] = None
        self._cancel_requested = False
        self._is_running = False
        self._total_executions = 0
        self._last_outputs: Optional[Dict[str, Any]] = None
        self._current_topology_request: Optional[TopologyRequest] = None
        self._current_topology: Optional[Topology] = None
        self._prefect_executor: Optional[PrefectTopologyExecutor] = None
        self._execution_id: Optional[str] = None

    async def execute(self, topology: TopologyRequest) -> Optional[Dict[str, Any]]:
        """
        Execute workflow topology with dependency awareness using PrefectTopologyExecutor.

        Returns outputs or None if cancelled.
        """
        self._execution_id = f"exec_{datetime.now().timestamp()}"
        self._current_topology_request = topology
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
            # Convert topology request to NetworkX graph
            graph = self._build_networkx_graph(topology)

            # Create Topology instance
            self._current_topology = Topology(
                graph=graph,
                jobset_id=topology.job_id,
                node_delay=0,  # Can be configured
            )

            # Import block functions
            imported_functions, import_errors = pre_import_functions(
                self._current_topology, topology.project_path
            )

            if import_errors:
                error_msg = f"Failed to import blocks: {import_errors}"
                logger.error(error_msg)
                await self._broadcast_status(
                    "weq_error",
                    {"execution_id": self._execution_id, "error": error_msg},
                )
                return None

            # Create executor
            self._prefect_executor = PrefectTopologyExecutor(self.ws_manager)

            # Execute with PrefectTopologyExecutor
            outputs = await self._prefect_executor.execute(
                topology=self._current_topology,
                imported_functions=imported_functions,
                observe_blocks=[],  # Can be configured
                max_workers=4,  # Can be configured
            )

            if self._cancel_requested or outputs is None:
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

    def cancel(self):
        """Cancel current execution."""
        logger.info(f"Cancelling execution {self._execution_id}")
        self._cancel_requested = True

        # Cancel PrefectTopologyExecutor
        if self._prefect_executor:
            self._prefect_executor.cancel()

        if self._current_execution and not self._current_execution.done():
            self._current_execution.cancel()

    def compare_outputs(
        self, outputs1: Dict[str, Any], outputs2: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Compare outputs from two executions.

        Returns list of differences.
        """
        if self._prefect_executor:
            return self._prefect_executor.compare_outputs(outputs1, outputs2)

        # Fallback comparison
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

    def _build_networkx_graph(self, topology: TopologyRequest) -> nx.MultiDiGraph:
        """Convert TopologyRequest to NetworkX graph for Topology class."""
        graph = nx.MultiDiGraph()

        # Add nodes
        for node_data in topology.graph["nodes"]:
            node_id = node_data["id"]
            # Extract node attributes
            graph.add_node(
                node_id,
                cmd=node_data.get("type", ""),  # Block type as cmd
                label=node_data.get("label", node_id),
                ctrls=node_data.get("data", {}).get("ctrls", {}),
                init_ctrls=node_data.get("data", {}).get("init_ctrls", {}),
                **node_data,  # Include all other attributes
            )

        # Add edges
        for edge_data in topology.graph["edges"]:
            source = edge_data["source"]
            target = edge_data["target"]

            # Extract edge attributes
            graph.add_edge(
                source,
                target,
                label=edge_data.get("sourceHandle", "default"),
                target_label=edge_data.get("targetHandle", "input"),
                multiple=edge_data.get("multiple", False),
                **edge_data,  # Include all other attributes
            )

        return graph

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
        base_status = {
            "is_running": self._is_running,
            "execution_id": self._execution_id,
            "total_executions": self._total_executions,
            "cancel_requested": self._cancel_requested,
        }

        # Get detailed status from PrefectTopologyExecutor if available
        if self._prefect_executor:
            executor_status = self._prefect_executor.get_status()
            base_status.update(executor_status)

        return base_status

    def get_last_outputs(self) -> Optional[Dict[str, Any]]:
        """Get outputs from the last execution."""
        return self._last_outputs
