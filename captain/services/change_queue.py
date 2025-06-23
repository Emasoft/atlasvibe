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
Change Queue Manager for AtlasVibe

Manages real-time code changes while workflows are running.
Provides seamless updates without interrupting execution.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from threading import Lock, Thread, Event
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from captain.internal.wsmanager import ConnectionManager
from captain.utils.logger import logger
from captain.utils.manifest.build_manifest import create_manifest
from captain.utils.block_metadata_generator import regenerate_block_data_json


class ChangeType(Enum):
    """Types of changes that can be queued."""

    CODE_UPDATE = "code_update"
    PARAMETER_UPDATE = "parameter_update"
    POSITION_UPDATE = "position_update"
    NAME_UPDATE = "name_update"
    DEPENDENCY_UPDATE = "dependency_update"


@dataclass
class BlockChange:
    """Represents a change to a block."""

    id: str = field(default_factory=lambda: str(uuid4()))
    block_path: str = ""
    block_id: str = ""
    change_type: ChangeType = ChangeType.CODE_UPDATE
    old_value: Any = None
    new_value: Any = None
    timestamp: float = field(default_factory=time.time)
    applied: bool = False
    error: Optional[str] = None


@dataclass
class ChangeTransaction:
    """Groups related changes into a transaction."""

    id: str = field(default_factory=lambda: str(uuid4()))
    changes: List[BlockChange] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    committed: bool = False
    rolled_back: bool = False


@dataclass
class DeferredWrite:
    """Represents a deferred file write operation."""

    path: Path
    content: str
    original_content: str
    metadata_path: Optional[Path] = None


class ChangeQueueManager:
    """
    Manages a queue of changes to blocks that can be applied in real-time.

    Features:
    - Queues changes while blocks are executing
    - Defers file writes until blocks finish
    - Supports transactions for atomic updates
    - Broadcasts change events via WebSocket
    - Maintains change history
    - Thread-safe operations
    """

    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        """Thread-safe singleton implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        """Initialize the change queue manager."""
        # Prevent re-initialization
        if self._initialized:
            return
        self.__class__._initialized = True

        self.change_queue: Queue[ChangeTransaction] = Queue()
        self.pending_changes: Dict[str, List[BlockChange]] = defaultdict(list)
        self.executing_blocks: Set[str] = set()
        self.block_versions: Dict[str, int] = defaultdict(int)
        self.change_history: List[ChangeTransaction] = []
        self.deferred_writes: Dict[str, DeferredWrite] = {}

        # Thread synchronization
        self._running = False
        self._processor_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._changes_lock = Lock()
        self._executing_lock = Lock()

        # Broadcast queue for thread-safe async operations
        self._broadcast_queue: Queue[Dict[str, Any]] = Queue()
        self._broadcast_thread: Optional[Thread] = None

        # Get WebSocket manager
        try:
            logger.debug("Getting WebSocket manager instance...")
            self.ws_manager = ConnectionManager.get_instance()
            logger.debug("Got WebSocket manager instance")
        except Exception as e:
            self.ws_manager = None
            logger.warning(f"WebSocket manager not available: {e}")

    @classmethod
    def get_instance(cls) -> "ChangeQueueManager":
        """Get singleton instance of ChangeQueueManager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self):
        """Start the change processor threads."""
        if not self._running:
            self._running = True
            self._stop_event.clear()

            # Start change processor thread
            self._processor_thread = Thread(target=self._process_changes, daemon=True, name="ChangeQueueProcessor")
            self._processor_thread.start()

            # Start broadcast thread
            self._broadcast_thread = Thread(
                target=self._process_broadcasts,
                daemon=True,
                name="ChangeQueueBroadcaster",
            )
            self._broadcast_thread.start()

            logger.info("ChangeQueueManager started")

    def stop(self):
        """Stop the change processor threads."""
        self._running = False
        self._stop_event.set()

        if self._processor_thread:
            self._processor_thread.join(timeout=5)
        if self._broadcast_thread:
            self._broadcast_thread.join(timeout=5)

        logger.info("ChangeQueueManager stopped")

    def queue_change(self, change: BlockChange) -> str:
        """
        Queue a single change.

        Args:
            change: The change to queue

        Returns:
            Transaction ID
        """
        transaction = ChangeTransaction(changes=[change])
        self.change_queue.put(transaction)

        # Add to pending changes for the block
        with self._changes_lock:
            self.pending_changes[change.block_id].append(change)

        # Queue broadcast
        self._queue_broadcast(
            {
                "type": "change_queued",
                "change_id": change.id,
                "block_id": change.block_id,
                "change_type": change.change_type.value,
                "timestamp": change.timestamp,
                "has_pending": len(self.pending_changes[change.block_id]),
            }
        )

        return transaction.id

    def queue_transaction(self, changes: List[BlockChange]) -> str:
        """
        Queue multiple changes as a transaction.

        Args:
            changes: List of changes to apply atomically

        Returns:
            Transaction ID
        """
        transaction = ChangeTransaction(changes=changes)
        self.change_queue.put(transaction)

        # Add to pending changes for each block
        with self._changes_lock:
            for change in changes:
                self.pending_changes[change.block_id].append(change)

        # Queue broadcast
        self._queue_broadcast(
            {
                "type": "transaction_queued",
                "transaction_id": transaction.id,
                "change_count": len(transaction.changes),
                "timestamp": transaction.timestamp,
            }
        )

        return transaction.id

    def mark_block_executing(self, block_id: str):
        """Mark a block as currently executing."""
        with self._executing_lock:
            self.executing_blocks.add(block_id)
        logger.debug(f"Block {block_id} marked as executing")

    def mark_block_finished(self, block_id: str):
        """
        Mark a block as finished executing.
        This triggers application of any deferred writes.
        """
        with self._executing_lock:
            self.executing_blocks.discard(block_id)
        logger.debug(f"Block {block_id} marked as finished")

        # Apply deferred write if exists
        if block_id in self.deferred_writes:
            self._apply_deferred_write(block_id)

    def is_block_executing(self, block_id: str) -> bool:
        """Check if a block is currently executing."""
        with self._executing_lock:
            return block_id in self.executing_blocks

    def get_pending_changes(self, block_id: str) -> List[BlockChange]:
        """Get pending changes for a block."""
        with self._changes_lock:
            return list(self.pending_changes.get(block_id, []))

    def has_pending_changes(self, block_id: str) -> bool:
        """Check if a block has pending changes."""
        with self._changes_lock:
            return bool(self.pending_changes.get(block_id))

    def get_block_version(self, block_id: str) -> int:
        """Get the current version number for a block."""
        return self.block_versions[block_id]

    def _process_changes(self):
        """Background thread that processes the change queue."""
        while self._running and not self._stop_event.is_set():
            try:
                # Get next transaction with timeout
                transaction = self.change_queue.get(timeout=0.1)

                # Process the transaction
                self._apply_transaction(transaction)

                # Add to history
                self.change_history.append(transaction)

                # Limit history size
                if len(self.change_history) > 1000:
                    self.change_history = self.change_history[-500:]

            except Empty:
                # Queue.get timeout - continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing changes: {e}")

    def _process_broadcasts(self):
        """Background thread that processes async broadcasts."""
        while self._running and not self._stop_event.is_set():
            try:
                message = self._broadcast_queue.get(timeout=0.1)

                if self.ws_manager:
                    # Note: Creating event loops in threads is not ideal
                    # This should be refactored to use a dedicated async thread
                    # or pass messages to the main event loop
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        # Run the broadcast
                        loop.run_until_complete(self.ws_manager.broadcast(message))
                    except Exception as e:
                        logger.error(f"Broadcast error: {e}")
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in broadcast thread: {e}")

    def _queue_broadcast(self, message: Dict[str, Any]):
        """Queue a broadcast message for async sending."""
        try:
            self._broadcast_queue.put_nowait(message)
        except Exception as e:
            logger.error(f"Failed to queue broadcast: {e}")

    def _apply_transaction(self, transaction: ChangeTransaction):
        """Apply all changes in a transaction."""
        logger.info(f"Applying transaction {transaction.id} with {len(transaction.changes)} changes")

        try:
            # Apply each change
            for change in transaction.changes:
                self._apply_change(change)

            transaction.committed = True

            # Queue broadcast
            self._queue_broadcast(
                {
                    "type": "transaction_applied",
                    "transaction_id": transaction.id,
                    "change_count": len(transaction.changes),
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            logger.error(f"Failed to apply transaction {transaction.id}: {e}")
            transaction.rolled_back = True

            # Queue broadcast
            self._queue_broadcast(
                {
                    "type": "transaction_failed",
                    "transaction_id": transaction.id,
                    "error": str(e),
                    "timestamp": time.time(),
                }
            )

    def _apply_change(self, change: BlockChange):
        """Apply a single change."""
        try:
            # Check if block is executing
            if self.is_block_executing(change.block_id):
                # Defer the change
                logger.debug(f"Deferring change {change.id} - block {change.block_id} is executing")
                return

            if change.change_type == ChangeType.CODE_UPDATE:
                self._apply_code_update(change)
            elif change.change_type == ChangeType.PARAMETER_UPDATE:
                self._apply_parameter_update(change)
            elif change.change_type == ChangeType.POSITION_UPDATE:
                self._apply_position_update(change)
            elif change.change_type == ChangeType.NAME_UPDATE:
                self._apply_name_update(change)
            elif change.change_type == ChangeType.DEPENDENCY_UPDATE:
                self._apply_dependency_update(change)

            change.applied = True

            # Increment block version
            self.block_versions[change.block_id] += 1

            # Remove from pending
            with self._changes_lock:
                if change in self.pending_changes[change.block_id]:
                    self.pending_changes[change.block_id].remove(change)

            logger.info(f"Applied {change.change_type.value} to block {change.block_id}")

        except Exception as e:
            change.error = str(e)
            logger.error(f"Failed to apply change {change.id}: {e}")
            raise

    def _apply_code_update(self, change: BlockChange):
        """Apply a code update to a block."""
        block_file = Path(change.block_path)
        if not block_file.exists():
            raise FileNotFoundError(f"Block file not found: {change.block_path}")

        # Check if block is executing - defer write if so
        if self.is_block_executing(change.block_id):
            # Store deferred write
            self.deferred_writes[change.block_id] = DeferredWrite(
                path=block_file,
                content=change.new_value,
                original_content=change.old_value or block_file.read_text(),
            )
            logger.info(f"Deferred code update for executing block {change.block_id}")
            return

        # Apply immediately if not executing
        self._write_block_file(block_file, change.new_value)

        # Queue broadcast
        self._queue_broadcast(
            {
                "type": "block_code_updated",
                "block_id": change.block_id,
                "block_path": change.block_path,
                "version": self.block_versions[change.block_id] + 1,
                "timestamp": time.time(),
            }
        )

    def _apply_deferred_write(self, block_id: str):
        """Apply a deferred write for a block."""
        if block_id not in self.deferred_writes:
            return

        deferred = self.deferred_writes.pop(block_id)

        try:
            self._write_block_file(deferred.path, deferred.content)

            logger.info(f"Applied deferred write for block {block_id}")

            # Queue broadcast
            self._queue_broadcast(
                {
                    "type": "block_code_updated",
                    "block_id": block_id,
                    "block_path": str(deferred.path),
                    "version": self.block_versions[block_id] + 1,
                    "timestamp": time.time(),
                    "was_deferred": True,
                }
            )

            # Process any remaining pending changes
            self._process_pending_changes(block_id)

        except Exception as e:
            logger.error(f"Failed to apply deferred write for {block_id}: {e}")
            # Try to restore original content
            try:
                deferred.path.write_text(deferred.original_content)
            except Exception as restore_error:
                logger.error(f"Failed to restore original content: {restore_error}")

    def _write_block_file(self, block_file: Path, content: str):
        """Write content to block file and regenerate metadata."""
        # Write new code
        block_file.write_text(content)

        # Regenerate metadata
        block_dir = block_file.parent
        try:
            regenerate_block_data_json(str(block_dir))
        except Exception as e:
            logger.warning(f"Failed to regenerate block_data.json: {e}")

        # Regenerate manifest
        try:
            create_manifest(str(block_file))
        except Exception as e:
            logger.warning(f"Failed to regenerate manifest: {e}")

    def _process_pending_changes(self, block_id: str):
        """Process any remaining pending changes for a block."""
        with self._changes_lock:
            pending = list(self.pending_changes.get(block_id, []))

        if not pending:
            return

        logger.info(f"Processing {len(pending)} pending changes for block {block_id}")

        for change in pending:
            if not change.applied:
                try:
                    self._apply_change(change)
                except Exception as e:
                    logger.error(f"Failed to apply pending change {change.id}: {e}")

    def _apply_parameter_update(self, change: BlockChange):
        """Apply a parameter update to a block."""
        # Parameter updates are handled by the frontend state
        # Just queue broadcast
        self._queue_broadcast(
            {
                "type": "block_parameter_updated",
                "block_id": change.block_id,
                "parameter": change.old_value,  # Parameter name
                "value": change.new_value,
                "version": self.block_versions[change.block_id] + 1,
                "timestamp": time.time(),
            }
        )

    def _apply_position_update(self, change: BlockChange):
        """Apply a position update to a block."""
        # Position updates are handled by the frontend state
        # Just queue broadcast
        self._queue_broadcast(
            {
                "type": "block_position_updated",
                "block_id": change.block_id,
                "position": change.new_value,
                "version": self.block_versions[change.block_id] + 1,
                "timestamp": time.time(),
            }
        )

    def _apply_name_update(self, change: BlockChange):
        """Apply a name update to a block."""
        # Name updates might require file/directory renaming
        # For now, just queue broadcast
        self._queue_broadcast(
            {
                "type": "block_name_updated",
                "block_id": change.block_id,
                "old_name": change.old_value,
                "new_name": change.new_value,
                "version": self.block_versions[change.block_id] + 1,
                "timestamp": time.time(),
            }
        )

    def _apply_dependency_update(self, change: BlockChange):
        """Apply a dependency update to a block."""
        # This would trigger venv regeneration
        # For now, just queue broadcast
        self._queue_broadcast(
            {
                "type": "block_dependency_updated",
                "block_id": change.block_id,
                "dependencies": change.new_value,
                "version": self.block_versions[change.block_id] + 1,
                "timestamp": time.time(),
            }
        )

    async def submit_to_prefect(self, transaction: ChangeTransaction) -> str:
        """
        Submit a change transaction to Prefect for execution.

        This method integrates with PrefectChangeExecutor to execute
        changes as Prefect flows for better tracking and visualization.

        Args:
            transaction: The change transaction to submit

        Returns:
            Flow run ID from Prefect
        """
        try:
            # Import here to avoid circular dependency
            from captain.services.prefect_change_executor import PrefectChangeExecutor

            # Get or create Prefect executor instance
            if not hasattr(self, "_prefect_executor"):
                self._prefect_executor = PrefectChangeExecutor(self)
                self._prefect_executor.start()

            # Submit transaction to Prefect
            flow_run_id = await self._prefect_executor.submit_transaction(transaction)

            logger.info(f"Submitted transaction {transaction.id} to Prefect (flow_run_id: {flow_run_id})")

            return flow_run_id

        except Exception as e:
            logger.error(f"Failed to submit transaction to Prefect: {e}")
            # Fall back to regular processing
            self.change_queue.put(transaction)
            return transaction.id

    def get_prefect_flow_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a Prefect flow run for a transaction."""
        if hasattr(self, "_prefect_executor"):
            return self._prefect_executor.get_flow_run_status(transaction_id)
        return None

    def enable_prefect_execution(self) -> bool:
        """Enable Prefect-based change execution."""
        try:
            from captain.services.prefect_change_executor import PrefectChangeExecutor

            if not hasattr(self, "_prefect_executor"):
                self._prefect_executor = PrefectChangeExecutor(self)
                self._prefect_executor.start()
                logger.info("Prefect execution enabled for change queue")
            return True
        except Exception as e:
            logger.error(f"Failed to enable Prefect execution: {e}")
            return False

    def disable_prefect_execution(self):
        """Disable Prefect-based change execution."""
        if hasattr(self, "_prefect_executor"):
            self._prefect_executor.stop()
            delattr(self, "_prefect_executor")
            logger.info("Prefect execution disabled for change queue")
