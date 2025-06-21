#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Queue adapter to bridge sync Queue and async operations
# - Allows Worker to consume from sync Queue in async context

import asyncio
import logging
from queue import Queue, Empty
from typing import Any, Optional
import threading

logger = logging.getLogger(__name__)


class AsyncQueueAdapter:
    """
    Adapter to make a sync Queue work with async/await.

    Runs a background thread to transfer items from sync Queue to async Queue.
    """

    def __init__(self, sync_queue: Queue):
        self.sync_queue = sync_queue
        self.async_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, loop: asyncio.AbstractEventLoop):
        """Start the adapter thread."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._transfer_items, args=(loop,), daemon=True
        )
        self._thread.start()
        logger.debug(f"AsyncQueueAdapter started for queue {id(self.sync_queue)}")

    def stop(self):
        """Stop the adapter thread."""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.debug("AsyncQueueAdapter stopped")

    def _transfer_items(self, loop: asyncio.AbstractEventLoop):
        """Transfer items from sync queue to async queue."""
        while self._running and not self._stop_event.is_set():
            try:
                # Get item from sync queue with timeout
                item = self.sync_queue.get(timeout=0.1)

                # Put item in async queue
                asyncio.run_coroutine_threadsafe(self.async_queue.put(item), loop)
                logger.debug(f"Transferred item to async queue: {type(item).__name__}")

            except Empty:
                # No item available, continue
                continue
            except Exception as e:
                logger.error(f"Error transferring item: {e}")

    async def get(self) -> Any:
        """Get an item from the async queue."""
        return await self.async_queue.get()

    async def put(self, item: Any):
        """Put an item back to the sync queue."""
        await asyncio.get_event_loop().run_in_executor(None, self.sync_queue.put, item)
