from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import atexit
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
)
from captain.utils.config import origins
from captain.utils.logger import logger
from captain.internal.manager import WatchManager


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
    watch_manager = WatchManager.get_instance()
    watch_manager.start_thread()

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
