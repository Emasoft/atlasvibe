#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Common test fixtures and configuration
# - Provides a test app without signal handlers for TestClient
#

"""Common test fixtures for AtlasVibe tests."""

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import sys
import os

# Add captain to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock tm_devices before any imports that might use it
from .mock_tm_devices import install_mock

install_mock()

from captain.routes import (  # noqa: E402
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
from captain.utils.config import origins  # noqa: E402
from captain.utils.logger import logger  # noqa: E402
from captain.internal.manager import WatchManager  # noqa: E402
from captain.internal.wsmanager import ConnectionManager  # noqa: E402
from captain.services.workflow_queue_coordinator import WorkflowQueueCoordinator  # noqa: E402
from captain.services.change_queue import ChangeQueueManager  # noqa: E402


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test-friendly lifespan without signal handlers."""
    logger.info("Running test startup event")

    # Startup
    watch_manager = WatchManager.get_instance()
    watch_manager.start_thread()

    # Get WebSocket manager instance
    ws_manager = ConnectionManager.get_instance()

    # Start Workflow Queue Coordinator (manages both WCQ and WEQ)
    workflow_coordinator = WorkflowQueueCoordinator(ws_manager)
    coordinator_task = asyncio.create_task(workflow_coordinator.run())
    logger.info("Workflow Queue Coordinator started (managing WCQ and WEQ)")

    # Start ChangeQueueManager for real-time code updates
    logger.info("Starting ChangeQueueManager...")
    change_queue_manager = ChangeQueueManager.get_instance()
    logger.info("Got ChangeQueueManager instance")
    change_queue_manager.start()
    logger.info("ChangeQueueManager started")

    # Store references for shutdown
    app.state.workflow_coordinator = workflow_coordinator
    app.state.coordinator_task = coordinator_task
    app.state.change_queue_manager = change_queue_manager

    yield

    # Shutdown
    logger.info("Running test shutdown event")

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


@pytest.fixture
def test_app():
    """Create a test-friendly FastAPI app without signal handlers."""
    app = FastAPI(lifespan=test_lifespan)

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

    return app
