#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of PrefectTopologyExecutor
# - Hybrid executor using Prefect for orchestration
# - Maintains Topology's graph logic and state management
# - Dynamic task creation as nodes become ready
# - Parallel execution of independent nodes
# - Support for loops and conditional paths
# - Cancellation and restart capabilities
# - Output capture and comparison

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime
from dataclasses import dataclass
import traceback
from queue import Queue
import uuid

# NOTE: Prefect integration is planned but not yet implemented
# This executor uses a hybrid approach with existing Topology class

from captain.models.topology import Topology
from captain.services.sync_async_worker import SyncAsyncWorker
from captain.services.queue_adapter import AsyncQueueAdapter
from pkgs.atlasvibe.atlasvibe import JobSuccess, JobFailure
from captain.internal.wsmanager import ConnectionManager as WebSocketManager
from captain.utils.broadcast import Signaler

logger = logging.getLogger(__name__)


@dataclass
class NodeExecutionState:
    """Track execution state for a node."""

    node_id: str
    status: str = "pending"  # pending, ready, running, completed, failed, cancelled
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    task_future: Optional[asyncio.Task] = None
    iteration_count: int = 0


class PrefectTopologyExecutor:
    """
    Hybrid executor that uses Prefect for orchestration while maintaining
    Topology's graph execution logic.

    Key features:
    - Wraps existing Topology class for graph management
    - Creates Prefect tasks dynamically as nodes become ready
    - Executes independent nodes in parallel
    - Handles loops and conditional paths
    - Supports cancellation and restart
    - Tracks outputs for comparison
    """

    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self._current_flow_run = None
        self._cancel_requested = False
        self._is_running = False
        self._executed_nodes: Set[str] = set()
        self._node_outputs: Dict[str, Any] = {}
        self._node_states: Dict[str, NodeExecutionState] = {}
        self._execution_id: Optional[str] = None
        self._topology: Optional[Topology] = None
        self._imported_functions: Optional[Dict[str, Callable]] = None
        self._task_queue: Queue[Any] = Queue()
        self._finish_queue: Queue[Any] = Queue()
        self._task_queue_adapter: Optional[AsyncQueueAdapter] = None
        self._finish_queue_adapter: Optional[AsyncQueueAdapter] = None
        self._worker_tasks: List[asyncio.Task] = []
        self._signaler: Optional[Signaler] = None

    async def execute(
        self,
        topology: Topology,
        imported_functions: Dict[str, Callable],
        observe_blocks: List[str] = None,
        max_workers: int = 4,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute workflow using Prefect with Topology's graph logic.

        Args:
            topology: Topology instance with graph
            imported_functions: Map of node_id to callable functions
            observe_blocks: List of blocks to observe
            max_workers: Maximum parallel workers

        Returns:
            Dict of node outputs or None if cancelled
        """
        self._execution_id = f"prefect_exec_{uuid.uuid4()}"
        self._topology = topology
        self._imported_functions = imported_functions
        self._cancel_requested = False
        self._is_running = True
        self._executed_nodes.clear()
        self._node_outputs.clear()
        self._node_states.clear()

        # Initialize signaler for WebSocket broadcasting
        self._signaler = Signaler(self.ws_manager)

        if observe_blocks is None:
            observe_blocks = []

        try:
            # Initialize node states
            self._initialize_node_states()

            # Broadcast flow start
            await self._broadcast_status(
                "prefect_flow_started",
                {
                    "execution_id": self._execution_id,
                    "jobset_id": topology.jobset_id,
                    "node_count": len(topology.original_graph.nodes),
                },
            )

            # Execute with Prefect flow
            outputs = await self._execute_prefect_flow(observe_blocks, max_workers)

            if self._cancel_requested:
                await self._broadcast_status(
                    "prefect_flow_cancelled", {"execution_id": self._execution_id}
                )
                return None

            # Store outputs
            self._node_outputs = outputs

            # Broadcast completion
            await self._broadcast_status(
                "prefect_flow_complete",
                {
                    "execution_id": self._execution_id,
                    "outputs": self._serialize_outputs(outputs),
                },
            )

            return outputs

        except Exception as e:
            logger.error(f"Error in Prefect execution: {e}")
            logger.error(traceback.format_exc())

            await self._broadcast_status(
                "prefect_flow_error",
                {"execution_id": self._execution_id, "error": str(e)},
            )

            return None

        finally:
            self._is_running = False
            # Clean up workers
            await self._cleanup_workers()

    def cancel(self):
        """Cancel current execution."""
        logger.info(f"Cancelling Prefect execution {self._execution_id}")
        self._cancel_requested = True

        # Cancel Topology
        if self._topology:
            self._topology.cancel()

        # Cancel all running node tasks
        for state in self._node_states.values():
            if state.task_future and not state.task_future.done():
                state.task_future.cancel()

    def compare_outputs(
        self, outputs1: Dict[str, Any], outputs2: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compare outputs from two executions."""
        differences = []

        all_nodes = set(outputs1.keys()) | set(outputs2.keys())

        for node_id in all_nodes:
            output1 = outputs1.get(node_id)
            output2 = outputs2.get(node_id)

            if output1 is None and output2 is not None:
                differences.append(
                    {
                        "node_id": node_id,
                        "type": "missing_in_first",
                        "output1": None,
                        "output2": output2,
                    }
                )
            elif output1 is not None and output2 is None:
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

        return differences

    def _initialize_node_states(self):
        """Initialize execution state for all nodes."""
        for node_id in self._topology.original_graph.nodes:
            self._node_states[node_id] = NodeExecutionState(node_id=node_id)

    async def _execute_prefect_flow(
        self, observe_blocks: List[str], max_workers: int
    ) -> Dict[str, Any]:
        """Execute workflow as a Prefect flow with dynamic task creation."""

        # Start workers
        await self._start_workers(observe_blocks, max_workers)

        # Give workers a moment to start
        await asyncio.sleep(0.1)

        # Start topology execution
        self._topology.run(self._task_queue)

        logger.info(
            f"Started topology execution with {len(self._worker_tasks)} workers"
        )

        # Process tasks dynamically
        outputs = {}
        completed_nodes = set()

        while not self._topology.is_finished() and not self._cancel_requested:
            try:
                # Get finished job from worker (non-blocking with timeout)
                logger.debug(
                    f"Waiting for response, queue size: {self._finish_queue.qsize()}"
                )
                response = self._finish_queue.get(block=True, timeout=0.1)
                logger.info(f"Got response: {response}")

                if isinstance(response, JobSuccess):
                    node_id = response.node_id
                    completed_nodes.add(node_id)
                    outputs[node_id] = response.result
                    self._node_states[node_id].status = "completed"
                    self._node_states[node_id].output = response.result
                    self._node_states[node_id].end_time = datetime.now()

                    # Process in topology to get next jobs
                    next_jobs = self._topology.process_worker_response(response)

                    if next_jobs:
                        # Queue next jobs
                        for job_id in next_jobs:
                            if job_id not in completed_nodes:
                                self._topology.run_job(job_id, self._task_queue)
                                self._node_states[job_id].status = "ready"

                elif isinstance(response, JobFailure):
                    node_id = response.node_id
                    self._node_states[node_id].status = "failed"
                    self._node_states[node_id].error = response.error
                    self._node_states[node_id].end_time = datetime.now()

                    # Let topology handle the failure
                    self._topology.process_worker_response(response)

                    # Topology will cancel itself on failure
                    break

            except Exception:
                # Queue timeout, continue checking
                await asyncio.sleep(0.01)
                # Also check if workers are done
                if all(task.done() for task in self._worker_tasks):
                    logger.warning("All workers finished but topology not complete")
                    break
                continue

        # Send poison pills to workers
        from captain.types.worker import PoisonPill

        for _ in range(max_workers):
            self._task_queue.put(PoisonPill())

        # Wait for workers to finish
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        return outputs

    async def _start_workers(self, observe_blocks: List[str], max_workers: int):
        """Start worker tasks."""
        # Determine optimal number of workers
        optimal_workers = min(
            max_workers, self._topology.get_maximum_workers(max_workers)
        )

        logger.info(f"Starting {optimal_workers} workers for execution")

        # Create workers
        for i in range(optimal_workers):
            worker = SyncAsyncWorker(
                task_queue=self._task_queue,
                finish_queue=self._finish_queue,
                imported_functions=self._imported_functions,
                observe_blocks=observe_blocks,
                signaler=self._signaler,
                node_delay=self._topology.node_delay,
            )

            # Create worker task
            worker_task = self._create_worker_task(worker, i)
            self._worker_tasks.append(worker_task)

    def _create_worker_task(self, worker: SyncAsyncWorker, worker_id: int):
        """Create an async task for a worker."""

        async def worker_wrapper():
            logger.info(f"Worker {worker_id} starting")

            try:
                await worker.run()
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                raise
            finally:
                logger.info(f"Worker {worker_id} finished")

        return asyncio.create_task(worker_wrapper())

    async def _cleanup_workers(self):
        """Clean up worker tasks."""
        # Cancel any remaining tasks
        for task in self._worker_tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        self._worker_tasks.clear()

    def _serialize_outputs(self, outputs: Any) -> Any:
        """Serialize outputs for WebSocket transmission."""
        if outputs is None:
            return None

        if isinstance(outputs, dict):
            return {k: self._serialize_outputs(v) for k, v in outputs.items()}
        elif isinstance(outputs, list):
            return [self._serialize_outputs(item) for item in outputs]
        elif isinstance(outputs, (str, int, float, bool)):
            return outputs
        else:
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
            "cancel_requested": self._cancel_requested,
            "node_states": {
                node_id: {
                    "status": state.status,
                    "iteration_count": state.iteration_count,
                    "has_output": state.output is not None,
                    "error": state.error,
                }
                for node_id, state in self._node_states.items()
            },
            "topology_status": {
                "finished": self._topology.is_finished() if self._topology else False,
                "cancelled": self._topology.is_cancelled() if self._topology else False,
                "finished_jobs": list(self._topology.finished_jobs)
                if self._topology
                else [],
                "queued_jobs": list(self._topology.queued_jobs)
                if self._topology
                else [],
                "loop_nodes": self._topology.loop_nodes if self._topology else [],
            },
        }

    def get_last_outputs(self) -> Optional[Dict[str, Any]]:
        """Get outputs from the last execution."""
        return self._node_outputs.copy() if self._node_outputs else None
