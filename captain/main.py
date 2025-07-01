# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import atexit
import os
import signal
import sys
from captain.routes import (
    blocks,
    devices,
    flowchart,
    key,
    test_profile,
    ws,
    log,
    test_sequence,
    project,
    workflow_queues,
)
from captain.utils.config import origins
from captain.utils.logger import logger
from captain.internal.manager import WatchManager
from captain.internal.wsmanager import ConnectionManager
from captain.services.workflow_queue_coordinator import WorkflowQueueCoordinator
from captain.services.change_queue import ChangeQueueManager


def cleanup_mecademic_handles():
    """Clean up mecademic robot handles on shutdown."""
    try:
        # Import here to avoid circular imports and only if needed
        from PYTHON.utils.mecademic_state.mecademic_state import destruct_handle_map

        logger.info("Cleaning up mecademic robot handles...")
        destruct_handle_map()
        logger.info("Mecademic robot handles cleaned up successfully")
    except ImportError:
        # Module might not be available in all installations
        pass
    except Exception as e:
        logger.error(f"Error cleaning up mecademic handles: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with proper startup and shutdown."""
    logger.info("Running startup event")

    # Startup
    # Skip file watching in Docker tests - it can cause startup issues
    if os.environ.get("DISABLE_FILE_WATCHER", "").lower() != "true":
        watch_manager = WatchManager.get_instance()
        watch_manager.start_thread()
    else:
        logger.info(
            "File watcher disabled by DISABLE_FILE_WATCHER environment variable"
        )

    # Get WebSocket manager instance
    ws_manager = ConnectionManager.get_instance()

    # Start Workflow Queue Coordinator (manages both WCQ and WEQ)
    workflow_coordinator = WorkflowQueueCoordinator(ws_manager)
    coordinator_task = asyncio.create_task(workflow_coordinator.run())
    logger.info("Workflow Queue Coordinator started (managing WCQ and WEQ)")

    # Start ChangeQueueManager for real-time code updates
    if os.environ.get("DISABLE_CHANGE_QUEUE", "").lower() != "true":
        change_queue_manager = ChangeQueueManager.get_instance()
        change_queue_manager.start()
        logger.info("ChangeQueueManager started")
    else:
        logger.info(
            "ChangeQueueManager disabled by DISABLE_CHANGE_QUEUE environment variable"
        )
        change_queue_manager = None

    # Store references for shutdown
    app.state.workflow_coordinator = workflow_coordinator
    app.state.coordinator_task = coordinator_task
    app.state.change_queue_manager = change_queue_manager

    # Register cleanup handlers
    atexit.register(cleanup_mecademic_handles)

    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, cleaning up...")
        cleanup_mecademic_handles()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    yield

    # Shutdown
    logger.info("Running shutdown event")

    # Stop Workflow Queue Coordinator
    if hasattr(app.state, "workflow_coordinator"):
        await app.state.workflow_coordinator.stop()
        logger.info("Workflow Queue Coordinator stopped")

        # Wait for coordinator task to complete
        if hasattr(app.state, "coordinator_task"):
            try:
                await asyncio.wait_for(app.state.coordinator_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Coordinator task did not complete within timeout")

    # Stop ChangeQueueManager
    if hasattr(app.state, "change_queue_manager"):
        app.state.change_queue_manager.stop()
        logger.info("ChangeQueueManager stopped")

    cleanup_mecademic_handles()


app = FastAPI(lifespan=lifespan)

# cors middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routes
app.include_router(ws.router)
app.include_router(flowchart.router)
app.include_router(log.router)
app.include_router(key.router)
app.include_router(test_profile.router)
app.include_router(blocks.router)
app.include_router(devices.router)
app.include_router(test_sequence.router)
app.include_router(project.router)
app.include_router(workflow_queues.router)
