import os
from captain.internal.manager import Manager, TSManager

manager = Manager()
"""
MANAGER INSTANCE
___________________
Used for storing the current topology and websocket connections,
bridge between workers, topology, and more.
"""

ts_manager = TSManager()
"""
TEST SEQUENCER MANAGER INSTANCE
___________________
Used for communicating with the Test Sequencer UI
"""

# Get CORS origins from environment variable, default to localhost:5391
default_origin = "http://localhost:5391"
env_origins = os.environ.get("CORS_ORIGINS", default_origin)
origins = [origin.strip() for origin in env_origins.split(",")]
"""
CORS CONFIG
___________________
Used for CORS configuration
"""
