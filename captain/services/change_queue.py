#!/usr/bin/env python3
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
from queue import Queue
from threading import Lock, Thread
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


class ChangeQueueManager:
    """
    Manages a queue of changes to blocks that can be applied in real-time.

    Features:
    - Queues changes while blocks are executing
    - Applies changes between executions
    - Supports transactions for atomic updates
    - Broadcasts change events via WebSocket
    - Maintains change history
    """

    _instance = None
    _lock = Lock()

    def __init__(self):
        """Initialize the change queue manager."""
        self.change_queue: Queue[ChangeTransaction] = Queue()
        self.pending_changes: Dict[str, List[BlockChange]] = defaultdict(list)
        self.executing_blocks: Set[str] = set()
        self.block_versions: Dict[str, int] = defaultdict(int)
        self.change_history: List[ChangeTransaction] = []
        self.ws_manager = ConnectionManager.get_instance()
        self._running = False
        self._processor_thread: Optional[Thread] = None

    @classmethod
    def get_instance(cls) -> "ChangeQueueManager":
        """Get singleton instance of ChangeQueueManager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self):
        """Start the change processor thread."""
        if not self._running:
            self._running = True
            self._processor_thread = Thread(target=self._process_changes, daemon=True)
            self._processor_thread.start()
            logger.info("ChangeQueueManager started")

    def stop(self):
        """Stop the change processor thread."""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
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
        self.pending_changes[change.block_id].append(change)

        # Broadcast change queued event
        asyncio.create_task(self._broadcast_change_queued(change))

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
        for change in changes:
            self.pending_changes[change.block_id].append(change)

        # Broadcast transaction queued event
        asyncio.create_task(self._broadcast_transaction_queued(transaction))

        return transaction.id

    def mark_block_executing(self, block_id: str):
        """Mark a block as currently executing."""
        self.executing_blocks.add(block_id)
        logger.debug(f"Block {block_id} marked as executing")

    def mark_block_finished(self, block_id: str):
        """
        Mark a block as finished executing.
        This triggers application of any pending changes.
        """
        self.executing_blocks.discard(block_id)
        logger.debug(f"Block {block_id} marked as finished")

        # Apply any pending changes for this block
        if block_id in self.pending_changes:
            self._apply_pending_changes(block_id)

    def get_pending_changes(self, block_id: str) -> List[BlockChange]:
        """Get pending changes for a block."""
        return self.pending_changes.get(block_id, [])

    def has_pending_changes(self, block_id: str) -> bool:
        """Check if a block has pending changes."""
        return bool(self.pending_changes.get(block_id))

    def get_block_version(self, block_id: str) -> int:
        """Get the current version number for a block."""
        return self.block_versions[block_id]

    def _process_changes(self):
        """Background thread that processes the change queue."""
        while self._running:
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

            except Exception:
                # Queue.get timeout - continue loop
                continue

    def _apply_transaction(self, transaction: ChangeTransaction):
        """Apply all changes in a transaction."""
        logger.info(
            f"Applying transaction {transaction.id} with {len(transaction.changes)} changes"
        )

        try:
            # Apply each change
            for change in transaction.changes:
                if change.block_id not in self.executing_blocks:
                    self._apply_change(change)
                else:
                    logger.debug(
                        f"Deferring change {change.id} - block {change.block_id} is executing"
                    )

            transaction.committed = True

            # Broadcast transaction applied
            asyncio.create_task(self._broadcast_transaction_applied(transaction))

        except Exception as e:
            logger.error(f"Failed to apply transaction {transaction.id}: {e}")
            transaction.rolled_back = True

            # Broadcast transaction failed
            asyncio.create_task(self._broadcast_transaction_failed(transaction, str(e)))

    def _apply_change(self, change: BlockChange):
        """Apply a single change."""
        try:
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
            if change in self.pending_changes[change.block_id]:
                self.pending_changes[change.block_id].remove(change)

            logger.info(
                f"Applied {change.change_type.value} to block {change.block_id}"
            )

        except Exception as e:
            change.error = str(e)
            logger.error(f"Failed to apply change {change.id}: {e}")
            raise

    def _apply_code_update(self, change: BlockChange):
        """Apply a code update to a block."""
        block_file = Path(change.block_path)
        if not block_file.exists():
            raise FileNotFoundError(f"Block file not found: {change.block_path}")

        # Write new code
        block_file.write_text(change.new_value)

        # Regenerate metadata
        block_dir = block_file.parent
        regenerate_block_data_json(str(block_dir))

        # Regenerate manifest
        create_manifest(str(block_file))

        # Broadcast code update
        asyncio.create_task(self._broadcast_code_updated(change))

    def _apply_parameter_update(self, change: BlockChange):
        """Apply a parameter update to a block."""
        # Parameter updates are handled by the frontend state
        # Just broadcast the update
        asyncio.create_task(self._broadcast_parameter_updated(change))

    def _apply_position_update(self, change: BlockChange):
        """Apply a position update to a block."""
        # Position updates are handled by the frontend state
        # Just broadcast the update
        asyncio.create_task(self._broadcast_position_updated(change))

    def _apply_name_update(self, change: BlockChange):
        """Apply a name update to a block."""
        # Name updates might require file/directory renaming
        # For now, just broadcast the update
        asyncio.create_task(self._broadcast_name_updated(change))

    def _apply_dependency_update(self, change: BlockChange):
        """Apply a dependency update to a block."""
        # This would trigger venv regeneration
        # For now, just broadcast the update
        asyncio.create_task(self._broadcast_dependency_updated(change))

    def _apply_pending_changes(self, block_id: str):
        """Apply all pending changes for a block."""
        pending = self.pending_changes[block_id]
        if not pending:
            return

        logger.info(f"Applying {len(pending)} pending changes for block {block_id}")

        for change in pending[:]:  # Copy list to avoid modification during iteration
            try:
                self._apply_change(change)
            except Exception as e:
                logger.error(f"Failed to apply pending change {change.id}: {e}")

    # WebSocket broadcast methods

    async def _broadcast_change_queued(self, change: BlockChange):
        """Broadcast that a change was queued."""
        await self.ws_manager.broadcast(
            {
                "type": "change_queued",
                "change_id": change.id,
                "block_id": change.block_id,
                "change_type": change.change_type.value,
                "timestamp": change.timestamp,
                "has_pending": len(self.pending_changes[change.block_id]),
            }
        )

    async def _broadcast_transaction_queued(self, transaction: ChangeTransaction):
        """Broadcast that a transaction was queued."""
        await self.ws_manager.broadcast(
            {
                "type": "transaction_queued",
                "transaction_id": transaction.id,
                "change_count": len(transaction.changes),
                "timestamp": transaction.timestamp,
            }
        )

    async def _broadcast_transaction_applied(self, transaction: ChangeTransaction):
        """Broadcast that a transaction was applied."""
        await self.ws_manager.broadcast(
            {
                "type": "transaction_applied",
                "transaction_id": transaction.id,
                "change_count": len(transaction.changes),
                "timestamp": time.time(),
            }
        )

    async def _broadcast_transaction_failed(
        self, transaction: ChangeTransaction, error: str
    ):
        """Broadcast that a transaction failed."""
        await self.ws_manager.broadcast(
            {
                "type": "transaction_failed",
                "transaction_id": transaction.id,
                "error": error,
                "timestamp": time.time(),
            }
        )

    async def _broadcast_code_updated(self, change: BlockChange):
        """Broadcast that code was updated."""
        await self.ws_manager.broadcast(
            {
                "type": "block_code_updated",
                "block_id": change.block_id,
                "block_path": change.block_path,
                "version": self.block_versions[change.block_id],
                "timestamp": time.time(),
            }
        )

    async def _broadcast_parameter_updated(self, change: BlockChange):
        """Broadcast that a parameter was updated."""
        await self.ws_manager.broadcast(
            {
                "type": "block_parameter_updated",
                "block_id": change.block_id,
                "parameter": change.old_value,  # Parameter name
                "value": change.new_value,
                "version": self.block_versions[change.block_id],
                "timestamp": time.time(),
            }
        )

    async def _broadcast_position_updated(self, change: BlockChange):
        """Broadcast that position was updated."""
        await self.ws_manager.broadcast(
            {
                "type": "block_position_updated",
                "block_id": change.block_id,
                "position": change.new_value,
                "version": self.block_versions[change.block_id],
                "timestamp": time.time(),
            }
        )

    async def _broadcast_name_updated(self, change: BlockChange):
        """Broadcast that name was updated."""
        await self.ws_manager.broadcast(
            {
                "type": "block_name_updated",
                "block_id": change.block_id,
                "old_name": change.old_value,
                "new_name": change.new_value,
                "version": self.block_versions[change.block_id],
                "timestamp": time.time(),
            }
        )

    async def _broadcast_dependency_updated(self, change: BlockChange):
        """Broadcast that dependencies were updated."""
        await self.ws_manager.broadcast(
            {
                "type": "block_dependency_updated",
                "block_id": change.block_id,
                "dependencies": change.new_value,
                "version": self.block_versions[change.block_id],
                "timestamp": time.time(),
            }
        )
