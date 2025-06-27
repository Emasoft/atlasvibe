# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

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

# Get CORS origins from environment variable, default to localhost origins
# Include common localhost ports and WebSocket protocols
default_origins = [
    "http://localhost:5391",
    "http://localhost:5392",
    "http://localhost:3000",
    "http://127.0.0.1:5391",
    "http://127.0.0.1:5392",
    "http://127.0.0.1:3000",
    "ws://localhost:5391",
    "ws://localhost:5392",
    "ws://127.0.0.1:5391",
    "ws://127.0.0.1:5392",
]

# Allow additional origins from environment variable
env_origins = os.environ.get("CORS_ORIGINS", "")
if env_origins:
    additional_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    origins = default_origins + additional_origins
else:
    origins = default_origins

# Remove duplicates while preserving order
origins = list(dict.fromkeys(origins))
"""
CORS CONFIG
___________________
Used for CORS configuration
"""
