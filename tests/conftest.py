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
from captain.internal.wsmanager import ConnectionManager  # noqa: E402


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test-friendly lifespan without signal handlers."""
    logger.info("Running test startup event")

    # Minimal startup - don't start background services for tests
    # Only initialize the WebSocket manager which is needed for API routes
    _ = ConnectionManager.get_instance()  # Initialize for side effects

    yield

    # Shutdown
    logger.info("Running test shutdown event")


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
