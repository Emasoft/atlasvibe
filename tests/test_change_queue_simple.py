#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple test to debug ChangeQueueManager."""

import sys
import os

# Add captain to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from captain.services.change_queue import ChangeQueueManager, BlockChange, ChangeType
from captain.utils.logger import logger


def test_change_queue_manager_basic():
    """Test basic ChangeQueueManager functionality."""
    logger.info("Starting test_change_queue_manager_basic")

    # Get instance
    manager = ChangeQueueManager.get_instance()
    logger.info("Got ChangeQueueManager instance")

    # Start it
    manager.start()
    logger.info("Started ChangeQueueManager")

    # Queue a change
    change = BlockChange(
        block_path="/test/path",
        block_id="test_block",
        change_type=ChangeType.CODE_UPDATE,
        old_value="old code",
        new_value="new code",
    )

    transaction_id = manager.queue_change(change)
    logger.info(f"Queued change with transaction_id: {transaction_id}")

    # Give it a moment to process
    import time

    time.sleep(0.1)

    # Stop it
    manager.stop()
    logger.info("Stopped ChangeQueueManager")

    assert transaction_id is not None


if __name__ == "__main__":
    test_change_queue_manager_basic()
