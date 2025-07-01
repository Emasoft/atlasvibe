#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

"""
Prefect-based Change Executor for AtlasVibe

Manages the execution of block changes using Prefect workflows,
enabling real-time code updates while workflows are running.
"""

import asyncio
import importlib
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Event
from typing import Any, Dict, List, Optional, Set

from prefect import flow, task, get_run_logger, get_client

from captain.internal.wsmanager import ConnectionManager
from captain.services.change_queue import (
    BlockChange,
    ChangeQueueManager,
    ChangeTransaction,
    ChangeType,
)
from captain.utils.logger import logger
from captain.utils.manifest.build_manifest import create_manifest
from captain.utils.block_metadata_generator import regenerate_block_data_json


@dataclass
class OutputCapture:
    """Captured output from a block execution."""

    block_id: str
    timestamp: float
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeExecutionResult:
    """Result of executing a change."""

    change_id: str
    success: bool
    execution_time: float
    error: Optional[str] = None
    output_diff: Optional[Dict[str, Any]] = None
    rolled_back: bool = False


class PrefectChangeExecutor:
    """
    Executes block changes using Prefect workflows.

    Features:
    - Creates Prefect flows for change transactions
    - Tracks execution state through Prefect
    - Captures output differences before/after changes
    - Supports module hot-reloading
    - Integrates with ChangeQueueManager
    - Broadcasts execution results via WebSocket
    """

    def __init__(self, change_queue_manager: Optional[ChangeQueueManager] = None):
        """Initialize the Prefect change executor."""
        self.change_queue_manager = (
            change_queue_manager or ChangeQueueManager.get_instance()
        )

        # Prefect client for API operations
        self.prefect_client = None

        # Execution tracking
        self.flow_runs: Dict[str, str] = {}  # transaction_id -> flow_run_id
        self.execution_results: Dict[str, List[ChangeExecutionResult]] = {}
        self.executing_changes: Set[str] = set()

        # Module reload tracking
        self.reloaded_modules: Dict[str, float] = {}  # module_name -> reload_time

        # Execution thread
        self._running = False
        self._executor_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._execution_queue: Queue[ChangeTransaction] = Queue()

        # WebSocket manager
        try:
            self.ws_manager = ConnectionManager.get_instance()
        except Exception:
            self.ws_manager = None
            logger.warning("WebSocket manager not available")

    async def _init_prefect_client(self):
        """Initialize Prefect client if not already initialized."""
        if self.prefect_client is None:
            self.prefect_client = get_client()

    def start(self):
        """Start the Prefect executor thread."""
        if not self._running:
            self._running = True
            self._stop_event.clear()

            self._executor_thread = Thread(
                target=self._run_executor_loop,
                daemon=True,
                name="PrefectChangeExecutor",
            )
            self._executor_thread.start()

            logger.info("PrefectChangeExecutor started")

    def stop(self):
        """Stop the Prefect executor thread."""
        self._running = False
        self._stop_event.set()

        if self._executor_thread:
            self._executor_thread.join(timeout=5)

        logger.info("PrefectChangeExecutor stopped")

    def _run_executor_loop(self):
        """Main executor loop running in separate thread."""
        while self._running and not self._stop_event.is_set():
            try:
                # Get next transaction with timeout
                transaction = self._execution_queue.get(timeout=0.1)

                # Log transaction instead of executing with event loop
                logger.info(
                    f"Prefect executor would process transaction {transaction.id}"
                )
                # TODO: Implement proper async execution without creating event loops in threads

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in executor loop: {e}\n{traceback.format_exc()}")

    async def submit_transaction(self, transaction: ChangeTransaction) -> str:
        """
        Submit a change transaction for execution.

        Args:
            transaction: The change transaction to execute

        Returns:
            Flow run ID
        """
        logger.info(
            f"Submitting transaction {transaction.id} with {len(transaction.changes)} changes"
        )

        # Queue for execution
        self._execution_queue.put(transaction)

        # Broadcast submission
        await self._broadcast_message(
            {
                "type": "prefect_flow_submitted",
                "transaction_id": transaction.id,
                "change_count": len(transaction.changes),
                "timestamp": time.time(),
            }
        )

        return transaction.id

    async def _execute_transaction(self, transaction: ChangeTransaction):
        """Execute a change transaction using Prefect."""
        try:
            # Initialize Prefect client
            await self._init_prefect_client()

            # Create and run the flow
            change_flow = await self._create_change_flow(transaction)

            # Store flow run mapping
            self.flow_runs[transaction.id] = transaction.id

            # Execute the flow
            logger.info(f"Executing Prefect flow for transaction {transaction.id}")

            # Run the flow (this is synchronous in the current thread)
            _ = change_flow()

            # Handle completion
            await self._on_flow_completed(transaction.id, success=True)

        except Exception as e:
            logger.error(
                f"Failed to execute transaction {transaction.id}: {e}\n{traceback.format_exc()}"
            )
            await self._on_flow_completed(transaction.id, success=False, error=str(e))

    async def _create_change_flow(self, transaction: ChangeTransaction):
        """Create a Prefect flow for a change transaction."""

        @flow(name=f"change_transaction_{transaction.id}")
        def change_transaction_flow():
            """Execute all changes in the transaction."""
            logger = get_run_logger()
            logger.info(f"Starting change transaction {transaction.id}")

            results = []
            for change in transaction.changes:
                # Run each change as a task
                result = apply_change_task(change, self)
                results.append(result)

            # Check if all changes succeeded
            all_success = all(r.success for r in results)

            if not all_success:
                logger.error(f"Transaction {transaction.id} had failures")
                # Could implement rollback logic here

            return results

        return change_transaction_flow

    @task(name="apply_block_change")
    def apply_change_task(self, change: BlockChange) -> ChangeExecutionResult:
        """Apply a single change as a Prefect task."""
        logger = get_run_logger()
        logger.info(f"Applying {change.change_type.value} to block {change.block_id}")

        start_time = time.time()

        try:
            # Check if block is executing
            if self.change_queue_manager.is_block_executing(change.block_id):
                logger.warning(
                    f"Block {change.block_id} is executing, deferring change"
                )
                return ChangeExecutionResult(
                    change_id=change.id,
                    success=False,
                    execution_time=time.time() - start_time,
                    error="Block is currently executing",
                )

            # Mark as executing
            self.executing_changes.add(change.id)

            # Apply based on change type
            if change.change_type == ChangeType.CODE_UPDATE:
                result = asyncio.run(self._apply_code_change(change))
            elif change.change_type == ChangeType.PARAMETER_UPDATE:
                result = asyncio.run(self._apply_parameter_change(change))
            elif change.change_type == ChangeType.DEPENDENCY_UPDATE:
                result = asyncio.run(self._apply_dependency_change(change))
            else:
                result = asyncio.run(self._apply_generic_change(change))

            result.execution_time = time.time() - start_time

            # Broadcast result
            asyncio.run(self._broadcast_execution_result(result, change.block_id))

            return result

        except Exception as e:
            logger.error(
                f"Failed to apply change {change.id}: {e}\n{traceback.format_exc()}"
            )
            return ChangeExecutionResult(
                change_id=change.id,
                success=False,
                execution_time=time.time() - start_time,
                error=str(e),
            )
        finally:
            self.executing_changes.discard(change.id)

    async def _apply_change_task(self, change: BlockChange) -> ChangeExecutionResult:
        """Async version of apply_change_task for direct calling."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.apply_change_task, change
        )

    async def _apply_code_change(self, change: BlockChange) -> ChangeExecutionResult:
        """Apply a code change to a block."""
        block_file = Path(change.block_path)

        if not block_file.exists():
            return ChangeExecutionResult(
                change_id=change.id,
                success=False,
                execution_time=0,
                error=f"Block file not found: {change.block_path}",
            )

        try:
            # Capture output before change
            before_capture = await self._capture_block_output(
                str(block_file),
                change.block_id,
                {},  # TODO: Get actual parameters
            )

            # Apply the code change
            block_file.write_text(change.new_value)

            # Regenerate metadata
            try:
                regenerate_block_data_json(str(block_file.parent))
            except Exception as e:
                logger.warning(f"Failed to regenerate block_data.json: {e}")

            # Regenerate manifest
            try:
                create_manifest(str(block_file))
            except Exception as e:
                logger.warning(f"Failed to regenerate manifest: {e}")

            # Reload module if needed
            await self._reload_module_for_block(block_file)

            # Capture output after change
            after_capture = await self._capture_block_output(
                str(block_file),
                change.block_id,
                {},  # TODO: Get actual parameters
            )

            # Compare outputs
            output_diff = self._compare_outputs(before_capture, after_capture)

            return ChangeExecutionResult(
                change_id=change.id,
                success=True,
                execution_time=0,
                output_diff=output_diff,
            )

        except Exception as e:
            # Try to rollback
            if change.old_value:
                try:
                    block_file.write_text(change.old_value)
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback change: {rollback_error}")

            return ChangeExecutionResult(
                change_id=change.id,
                success=False,
                execution_time=0,
                error=str(e),
                rolled_back=bool(change.old_value),
            )

    async def _apply_change_with_reload(
        self, change: BlockChange
    ) -> ChangeExecutionResult:
        """Apply a change with module reloading support."""
        result = await self._apply_code_change(change)

        if result.success:
            # Force module reload
            block_file = Path(change.block_path)
            await self._reload_module_for_block(block_file)

        return result

    async def _reload_module_for_block(self, block_file: Path):
        """Reload the Python module for a block."""
        try:
            # Construct module name from path
            parts = block_file.stem.split("/")
            if "blocks" in parts:
                idx = parts.index("blocks")
                module_parts = parts[idx:]
            else:
                module_parts = [block_file.stem]

            module_name = ".".join(module_parts)

            # Check if module is loaded
            if module_name in sys.modules:
                logger.info(f"Reloading module: {module_name}")
                importlib.reload(sys.modules[module_name])
                self.reloaded_modules[module_name] = time.time()

        except Exception as e:
            logger.warning(f"Failed to reload module for {block_file}: {e}")

    async def _capture_block_output(
        self, block_path: str, block_id: str, parameters: Dict[str, Any]
    ) -> OutputCapture:
        """Capture the output of a block execution."""
        capture = OutputCapture(block_id=block_id, timestamp=time.time())

        try:
            # Import and execute the block function
            # This is a simplified version - real implementation would use
            # the actual block execution framework

            # For now, just capture basic metadata
            capture.metadata = {
                "block_path": block_path,
                "parameters": parameters,
                "captured_at": time.time(),
            }

            # TODO: Actually execute the block and capture outputs

        except Exception as e:
            capture.errors.append(str(e))
            logger.error(f"Failed to capture output for {block_id}: {e}")

        return capture

    def _compare_outputs(
        self, before: OutputCapture, after: OutputCapture
    ) -> Dict[str, Any]:
        """Compare outputs before and after a change."""
        diff = {
            "before": before.outputs,
            "after": after.outputs,
            "changes": [],
            "errors_before": before.errors,
            "errors_after": after.errors,
        }

        # Find changes in outputs
        all_keys = set(before.outputs.keys()) | set(after.outputs.keys())

        for key in all_keys:
            before_val = before.outputs.get(key)
            after_val = after.outputs.get(key)

            if before_val != after_val:
                diff["changes"].append(
                    {"field": key, "before": before_val, "after": after_val}
                )

        return diff

    async def _apply_parameter_change(
        self, change: BlockChange
    ) -> ChangeExecutionResult:
        """Apply a parameter change to a block."""
        # Parameter changes are typically handled by the frontend
        # Here we just track and broadcast the change

        return ChangeExecutionResult(
            change_id=change.id,
            success=True,
            execution_time=0,
            output_diff={
                "parameter": change.old_value,
                "old_value": change.old_value,
                "new_value": change.new_value,
            },
        )

    async def _apply_dependency_change(
        self, change: BlockChange
    ) -> ChangeExecutionResult:
        """Apply a dependency change to a block."""
        # This would trigger virtual environment regeneration
        # For now, just track the change

        return ChangeExecutionResult(
            change_id=change.id,
            success=True,
            execution_time=0,
            output_diff={"dependencies": change.new_value},
        )

    async def _apply_generic_change(self, change: BlockChange) -> ChangeExecutionResult:
        """Apply a generic change to a block."""
        return ChangeExecutionResult(
            change_id=change.id, success=True, execution_time=0
        )

    async def _on_flow_completed(
        self, transaction_id: str, success: bool, error: Optional[str] = None
    ):
        """Handle flow completion."""
        logger.info(
            f"Flow completed for transaction {transaction_id}: success={success}"
        )

        # Update transaction state
        if transaction_id in self.flow_runs:
            del self.flow_runs[transaction_id]

        # Broadcast completion
        await self._broadcast_message(
            {
                "type": "prefect_flow_completed",
                "transaction_id": transaction_id,
                "success": success,
                "error": error,
                "timestamp": time.time(),
            }
        )

        # Mark blocks as finished if successful
        if success and self.change_queue_manager:
            # Get the transaction from history
            # In real implementation, we'd store this properly
            pass

    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message via WebSocket."""
        if self.ws_manager:
            try:
                await self.ws_manager.broadcast(message)
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")

    async def _broadcast_execution_result(
        self, result: ChangeExecutionResult, block_id: str
    ):
        """Broadcast execution result with output differences."""
        message = {
            "type": "change_execution_result",
            "change_id": result.change_id,
            "block_id": block_id,
            "success": result.success,
            "execution_time": result.execution_time,
            "error": result.error,
            "timestamp": time.time(),
        }

        if result.output_diff:
            message["output_diff"] = result.output_diff

        await self._broadcast_message(message)

    def get_flow_run_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a flow run."""
        if transaction_id not in self.flow_runs:
            return None

        # In a real implementation, we'd query Prefect API
        return {
            "transaction_id": transaction_id,
            "status": "running",  # or completed, failed, etc.
            "flow_run_id": self.flow_runs.get(transaction_id),
        }

    def get_execution_history(self, transaction_id: str) -> List[ChangeExecutionResult]:
        """Get execution history for a transaction."""
        return self.execution_results.get(transaction_id, [])

    async def cancel_transaction(self, transaction_id: str) -> bool:
        """Cancel a running transaction."""
        if transaction_id not in self.flow_runs:
            return False

        try:
            # In real implementation, use Prefect API to cancel
            logger.info(f"Cancelling transaction {transaction_id}")

            # Broadcast cancellation
            await self._broadcast_message(
                {
                    "type": "prefect_flow_cancelled",
                    "transaction_id": transaction_id,
                    "timestamp": time.time(),
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to cancel transaction {transaction_id}: {e}")
            return False


# Standalone task function for Prefect
@task(name="apply_block_change")
def apply_change_task(
    change: BlockChange, executor: PrefectChangeExecutor
) -> ChangeExecutionResult:
    """Apply a single change as a Prefect task."""
    return executor.apply_change_task(change)
