#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of WorkflowChangesQueue (WCQ)
# - Sequential processing of user changes with FIFO ordering
# - Support for code updates, manifest regeneration, metadata updates
# - WebSocket broadcasting for real-time progress updates
# - Completion callback mechanism to trigger WEQ restart
# - Millisecond-level enqueue response time

import asyncio
import json
import logging
from enum import Enum
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import traceback


from captain.internal.wsmanager import ConnectionManager as WebSocketManager
from captain.utils.manifest.build_manifest import create_manifest
from captain.utils.block_metadata_generator import regenerate_block_data_json
from captain.utils.project_structure import update_block_code

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes that can be queued."""

    CODE_UPDATE = "CODE_UPDATE"
    MANIFEST_REGEN = "MANIFEST_REGEN"
    METADATA_UPDATE = "METADATA_UPDATE"
    BLOCK_RENAME = "BLOCK_RENAME"
    CONNECTION_CHANGE = "CONNECTION_CHANGE"
    PARAMETER_UPDATE = "PARAMETER_UPDATE"


class WorkflowChange:
    """Represents a single workflow change."""

    def __init__(self, change_type: ChangeType, block_id: str, data: Dict[str, Any]):
        self.id = f"{datetime.now().timestamp()}_{block_id}"
        self.type = change_type
        self.block_id = block_id
        self.data = data
        self.timestamp = datetime.now()
        self.status = "pending"
        self.result = None
        self.error = None


class WorkflowChangesQueue:
    """
    Sequential queue for processing workflow changes.

    Ensures all changes are applied in the exact order they were made,
    with completion triggering workflow re-execution.
    """

    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._process_task: Optional[asyncio.Task] = None
        self._completion_callback: Optional[Callable] = None
        self._total_processed = 0
        self._current_change: Optional[WorkflowChange] = None
        self._processing_lock = asyncio.Lock()

    async def enqueue(self, change: Dict[str, Any]) -> str:
        """
        Enqueue a change for processing.

        Returns immediately (within milliseconds) with change ID.
        """
        # Create change object
        workflow_change = WorkflowChange(
            change_type=ChangeType(change["type"]),
            block_id=change["block_id"],
            data=change["data"],
        )

        # Add to queue (non-blocking)
        await self._queue.put(workflow_change)

        # Broadcast enqueue event
        await self._broadcast_status(
            "wcq_enqueued",
            {
                "change_id": workflow_change.id,
                "change_type": workflow_change.type.value,
                "block_id": workflow_change.block_id,
                "queue_length": self._queue.qsize(),
            },
        )

        # Start processing if not already running
        if not self._running:
            asyncio.create_task(self.start())

        return workflow_change.id

    async def start(self):
        """Start processing changes from the queue."""
        if self._running:
            return

        self._running = True
        logger.info("Starting WorkflowChangesQueue processing")

        try:
            while self._running:
                try:
                    # Wait for next change with timeout
                    change = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                    # Process the change
                    await self._process_change_wrapper(change)

                except asyncio.TimeoutError:
                    # No changes in queue, continue waiting
                    continue
                except Exception as e:
                    logger.error(f"Error in WCQ processing loop: {e}")
                    logger.error(traceback.format_exc())

        finally:
            self._running = False
            logger.info("WorkflowChangesQueue processing stopped")

    def stop(self):
        """Stop processing changes."""
        self._running = False
        if self._process_task:
            self._process_task.cancel()

    def set_completion_callback(self, callback: Callable):
        """Set callback to be called when a change completes processing."""
        self._completion_callback = callback

    async def _process_change_wrapper(self, change: WorkflowChange):
        """Wrapper to handle change processing with status updates."""
        async with self._processing_lock:
            self._current_change = change
            change.status = "processing"

            # Broadcast processing start
            await self._broadcast_status(
                "wcq_processing",
                {
                    "change_id": change.id,
                    "change_type": change.type.value,
                    "block_id": change.block_id,
                    "timestamp": change.timestamp.isoformat(),
                },
            )

            try:
                # Process the change
                result = await self._process_change(
                    {
                        "type": change.type,
                        "block_id": change.block_id,
                        "data": change.data,
                    }
                )

                change.status = "completed"
                change.result = result
                self._total_processed += 1

                # Broadcast completion
                await self._broadcast_status(
                    "wcq_complete",
                    {
                        "change_id": change.id,
                        "change_type": change.type.value,
                        "block_id": change.block_id,
                        "result": str(result) if result else None,
                        "total_processed": self._total_processed,
                    },
                )

                # Trigger completion callback (for WEQ restart)
                if self._completion_callback:
                    await self._completion_callback()

            except Exception as e:
                change.status = "failed"
                change.error = str(e)
                logger.error(f"Error processing change {change.id}: {e}")
                logger.error(traceback.format_exc())

                # Broadcast error
                await self._broadcast_status(
                    "wcq_error",
                    {
                        "change_id": change.id,
                        "change_type": change.type.value,
                        "block_id": change.block_id,
                        "error": str(e),
                    },
                )

            finally:
                self._current_change = None

    async def _process_change(self, change: Dict[str, Any]) -> Any:
        """
        Process a single change based on its type.
        """
        change_type = change["type"]
        block_id = change["block_id"]
        data = change["data"]

        logger.info(f"Processing {change_type.value} for block {block_id}")

        if change_type == ChangeType.CODE_UPDATE:
            return await self._process_code_update(block_id, data)

        elif change_type == ChangeType.MANIFEST_REGEN:
            return await self._process_manifest_regeneration(block_id, data)

        elif change_type == ChangeType.METADATA_UPDATE:
            return await self._process_metadata_update(block_id, data)

        elif change_type == ChangeType.BLOCK_RENAME:
            return await self._process_block_rename(block_id, data)

        elif change_type == ChangeType.CONNECTION_CHANGE:
            return await self._process_connection_change(block_id, data)

        elif change_type == ChangeType.PARAMETER_UPDATE:
            return await self._process_parameter_update(block_id, data)

        else:
            raise ValueError(f"Unknown change type: {change_type}")

    async def _process_code_update(self, block_id: str, data: Dict[str, Any]) -> bool:
        """Process a code update for a block."""
        code = data.get("code", "")
        project_path = data.get("project_path")

        # Update the block's Python file (not async)
        success = update_block_code(block_id, code, project_path)

        if success:
            # Regenerate metadata after code update
            await self._regenerate_block_metadata(block_id, project_path)

        return success

    async def _process_manifest_regeneration(self, block_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate manifest for a block."""
        project_path = data.get("project_path")

        # Find block file
        block_path = self._find_block_path(block_id, project_path)
        if not block_path:
            raise FileNotFoundError(f"Block {block_id} not found")

        # Create manifest from Python file (not async)
        manifest = create_manifest(str(block_path))

        # Broadcast manifest update
        await self._broadcast_status("manifest_update", {"block_id": block_id, "manifest": manifest})

        return manifest

    async def _process_metadata_update(self, block_id: str, data: Dict[str, Any]) -> bool:
        """Update block metadata (block_data.json)."""
        project_path = data.get("project_path")
        metadata = data.get("metadata", {})

        block_dir = self._find_block_directory(block_id, project_path)
        if not block_dir:
            raise FileNotFoundError(f"Block directory for {block_id} not found")

        # Update block_data.json
        block_data_path = block_dir / "block_data.json"
        existing_data = {}

        if block_data_path.exists():
            with open(block_data_path, "r") as f:
                existing_data = json.load(f)

        # Merge with new metadata
        existing_data.update(metadata)

        with open(block_data_path, "w") as f:
            json.dump(existing_data, f, indent=2)

        return True

    async def _process_block_rename(self, old_block_id: str, data: Dict[str, Any]) -> bool:
        """Process block renaming."""
        new_block_id = data.get("new_block_id")
        project_path = data.get("project_path")

        if not new_block_id:
            raise ValueError("new_block_id is required for block rename")

        # Find and rename block directory
        old_dir = self._find_block_directory(old_block_id, project_path)
        if not old_dir:
            raise FileNotFoundError(f"Block directory for {old_block_id} not found")

        new_dir = old_dir.parent / new_block_id
        old_dir.rename(new_dir)

        # Update Python file name
        old_py = new_dir / f"{old_block_id}.py"
        new_py = new_dir / f"{new_block_id}.py"
        if old_py.exists():
            old_py.rename(new_py)

        # Update function name in Python file
        if new_py.exists():
            content = new_py.read_text()
            # Simple replacement - might need more sophisticated AST manipulation
            content = content.replace(f"def {old_block_id}", f"def {new_block_id}")
            new_py.write_text(content)

        return True

    async def _process_connection_change(self, block_id: str, data: Dict[str, Any]) -> bool:
        """Process connection changes (edges in the graph)."""
        # Connection changes don't require file updates
        # They're handled by the topology when workflow executes
        logger.info(f"Connection change for {block_id}: {data}")
        return True

    async def _process_parameter_update(self, block_id: str, data: Dict[str, Any]) -> bool:
        """Process parameter updates for a block."""
        # Parameter updates are typically runtime values
        # They don't require file changes
        logger.info(f"Parameter update for {block_id}: {data}")
        return True

    async def _regenerate_block_metadata(self, block_id: str, project_path: Optional[str]):
        """Regenerate block_data.json from docstring."""
        block_path = self._find_block_path(block_id, project_path)
        if block_path:
            try:
                # regenerate_block_data_json is not async
                regenerate_block_data_json(str(block_path.parent))
            except Exception as e:
                logger.warning(f"Failed to regenerate metadata for {block_id}: {e}")

    def _find_block_path(self, block_id: str, project_path: Optional[str]) -> Optional[Path]:
        """Find the Python file for a block."""
        # Check project blocks first
        if project_path:
            # Handle .atlasvibe file path
            if project_path.endswith(".atlasvibe"):
                project_dir = Path(project_path).parent
            else:
                project_dir = Path(project_path)

            project_blocks = project_dir / "atlasvibe_blocks"
            if project_blocks.exists():
                block_file = project_blocks / block_id / f"{block_id}.py"
                if block_file.exists():
                    return block_file

        # Check global blocks
        global_blocks = Path(__file__).parent.parent.parent / "blocks"
        for category_dir in global_blocks.iterdir():
            if category_dir.is_dir():
                for subcat_dir in category_dir.iterdir():
                    if subcat_dir.is_dir():
                        block_file = subcat_dir / block_id / f"{block_id}.py"
                        if block_file.exists():
                            return block_file

        return None

    def _find_block_directory(self, block_id: str, project_path: Optional[str]) -> Optional[Path]:
        """Find the directory for a block."""
        block_path = self._find_block_path(block_id, project_path)
        return block_path.parent if block_path else None

    async def _broadcast_status(self, message_type: str, data: Dict[str, Any]):
        """Broadcast status update via WebSocket."""
        message = {
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        }
        await self.ws_manager.broadcast(message)

    def get_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "queue_length": self._queue.qsize(),
            "is_processing": self._current_change is not None,
            "current_change": {
                "id": self._current_change.id,
                "type": self._current_change.type.value,
                "block_id": self._current_change.block_id,
            }
            if self._current_change
            else None,
            "total_processed": self._total_processed,
        }
