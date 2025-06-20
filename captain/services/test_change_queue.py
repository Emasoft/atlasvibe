#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the Change Queue Manager
"""

import asyncio
import time
from unittest.mock import patch, MagicMock
import pytest
from captain.services.change_queue import (
    ChangeQueueManager,
    BlockChange,
    ChangeType,
    ChangeTransaction,
)


class TestChangeQueueManager:
    """Test the ChangeQueueManager functionality."""

    @pytest.fixture
    def change_queue(self):
        """Create a fresh ChangeQueueManager instance."""
        # Reset singleton
        ChangeQueueManager._instance = None
        manager = ChangeQueueManager.get_instance()
        yield manager
        # Cleanup
        if manager._running:
            manager.stop()

    @pytest.fixture
    def mock_ws_manager(self):
        """Mock WebSocket manager."""
        with patch("captain.services.change_queue.ConnectionManager") as mock:
            ws_manager = MagicMock()
            ws_manager.broadcast = MagicMock(return_value=asyncio.Future())
            ws_manager.broadcast.return_value.set_result(None)
            mock.get_instance.return_value = ws_manager
            yield ws_manager

    def test_singleton_instance(self):
        """Test that ChangeQueueManager is a singleton."""
        instance1 = ChangeQueueManager.get_instance()
        instance2 = ChangeQueueManager.get_instance()
        assert instance1 is instance2

    def test_queue_change(self, change_queue, mock_ws_manager):
        """Test queuing a single change."""
        change = BlockChange(
            block_path="/test/block.py",
            block_id="test_block",
            change_type=ChangeType.CODE_UPDATE,
            old_value="old code",
            new_value="new code",
        )

        transaction_id = change_queue.queue_change(change)

        assert transaction_id is not None
        assert change_queue.has_pending_changes("test_block")
        assert len(change_queue.get_pending_changes("test_block")) == 1

    def test_mark_block_executing_prevents_changes(self, change_queue):
        """Test that marking a block as executing prevents immediate changes."""
        block_id = "test_block"

        # Mark as executing
        change_queue.mark_block_executing(block_id)
        assert block_id in change_queue.executing_blocks

        # Queue a change
        change = BlockChange(
            block_path="/test/block.py",
            block_id=block_id,
            change_type=ChangeType.CODE_UPDATE,
            new_value="new code",
        )
        change_queue.queue_change(change)

        # Change should be pending, not applied
        assert change_queue.has_pending_changes(block_id)
        assert not change.applied

    def test_mark_block_finished_applies_changes(self, change_queue, tmp_path):
        """Test that marking a block as finished applies pending changes."""
        block_id = "test_block"
        block_file = tmp_path / "test_block.py"
        block_file.write_text("old code")

        # Mark as executing
        change_queue.mark_block_executing(block_id)

        # Queue a change
        change = BlockChange(
            block_path=str(block_file),
            block_id=block_id,
            change_type=ChangeType.CODE_UPDATE,
            old_value="old code",
            new_value="new code",
        )
        change_queue.queue_change(change)

        # File should not be changed yet
        assert block_file.read_text() == "old code"

        # Mark as finished
        with patch("captain.services.change_queue.regenerate_block_data_json"):
            with patch("captain.services.change_queue.create_manifest"):
                change_queue.mark_block_finished(block_id)

        # Wait for processing
        time.sleep(0.2)

        # File should be updated
        assert block_file.read_text() == "new code"
        assert not change_queue.has_pending_changes(block_id)

    def test_async_broadcast_from_thread(self, change_queue, mock_ws_manager):
        """Test that broadcasts work correctly from thread context."""
        # This test verifies the async/thread boundary is handled properly
        change_queue.start()

        change = BlockChange(
            block_path="/test/block.py",
            block_id="test_block",
            change_type=ChangeType.CODE_UPDATE,
        )

        # Queue change from main thread
        change_queue.queue_change(change)

        # Give time for async broadcast
        time.sleep(0.1)

        # Verify broadcast was called
        assert mock_ws_manager.broadcast.called

    def test_version_tracking(self, change_queue, tmp_path):
        """Test that block versions are tracked correctly."""
        block_id = "test_block"
        block_file = tmp_path / "test_block.py"
        block_file.write_text("v1")

        # Initial version should be 0
        assert change_queue.get_block_version(block_id) == 0

        # Apply a change
        change = BlockChange(
            block_path=str(block_file),
            block_id=block_id,
            change_type=ChangeType.CODE_UPDATE,
            new_value="v2",
        )

        with patch("captain.services.change_queue.regenerate_block_data_json"):
            with patch("captain.services.change_queue.create_manifest"):
                change_queue._apply_change(change)

        # Version should increment
        assert change_queue.get_block_version(block_id) == 1

    def test_transaction_atomicity(self, change_queue, tmp_path):
        """Test that transactions apply all changes or none."""
        file1 = tmp_path / "block1.py"
        file2 = tmp_path / "block2.py"
        file1.write_text("old1")
        file2.write_text("old2")

        changes = [
            BlockChange(
                block_path=str(file1),
                block_id="block1",
                change_type=ChangeType.CODE_UPDATE,
                new_value="new1",
            ),
            BlockChange(
                block_path=str(file2),
                block_id="block2",
                change_type=ChangeType.CODE_UPDATE,
                new_value="new2",
            ),
        ]

        transaction = ChangeTransaction(changes=changes)

        with patch("captain.services.change_queue.regenerate_block_data_json"):
            with patch("captain.services.change_queue.create_manifest"):
                change_queue._apply_transaction(transaction)

        # Both files should be updated
        assert file1.read_text() == "new1"
        assert file2.read_text() == "new2"
        assert transaction.committed

    def test_deferred_writes(self, change_queue, tmp_path):
        """Test that writes are deferred when block is executing."""
        block_id = "test_block"
        block_file = tmp_path / "test_block.py"
        block_file.write_text("original code")

        # Mark as executing
        change_queue.mark_block_executing(block_id)

        # Try to apply change directly
        change = BlockChange(
            block_path=str(block_file),
            block_id=block_id,
            change_type=ChangeType.CODE_UPDATE,
            new_value="new code",
        )

        # Start the queue processor
        change_queue.start()

        # Queue the change
        change_queue.queue_change(change)

        # Give time for processing
        time.sleep(0.2)

        # File should NOT be changed (deferred)
        assert block_file.read_text() == "original code"

        # Now mark as finished
        with patch("captain.services.change_queue.regenerate_block_data_json"):
            with patch("captain.services.change_queue.create_manifest"):
                change_queue.mark_block_finished(block_id)

        # Give time for deferred write
        time.sleep(0.2)

        # Now file should be updated
        assert block_file.read_text() == "new code"

    def test_error_recovery(self, change_queue, tmp_path):
        """Test error recovery during change application."""
        block_file = tmp_path / "test_block.py"
        block_file.write_text("original")

        change = BlockChange(
            block_path=str(block_file),
            block_id="test_block",
            change_type=ChangeType.CODE_UPDATE,
            old_value="original",
            new_value="new code",
        )

        # Make file unwritable to cause error
        block_file.chmod(0o444)

        try:
            with pytest.raises(Exception):
                change_queue._apply_change(change)

            # Error should be recorded
            assert change.error is not None
            assert not change.applied
        finally:
            # Restore permissions
            block_file.chmod(0o644)
