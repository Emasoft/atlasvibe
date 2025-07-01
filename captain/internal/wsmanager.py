# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from captain.types.test_sequence import TestSequenceMessage
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from pkgs.atlasvibe.atlasvibe.utils import PlotlyJSONEncoder
from queue import Queue
from typing import Any, Union
import json
from captain.types.worker import WorkerJobResponse
import threading
import traceback
from captain.utils.logger import logger

socket_connection_lock = threading.Lock()
_instance_lock = threading.Lock()


class ConnectionManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        # Double-checked locking pattern for thread-safe singleton
        if cls._instance is None:
            with _instance_lock:
                if cls._instance is None:
                    cls._instance = ConnectionManager()
        return cls._instance

    def __init__(self):
        self.active_connections_map: dict[str, WebSocket] = {}
        self.log_queue: Queue[WebSocket] = Queue()

    async def connect(self, websocket: WebSocket, socket_id: str):
        await websocket.accept()

        with socket_connection_lock:
            self.active_connections_map[socket_id] = websocket

        logger.debug(f"Connected! Amt of active connections: {len(self.active_connections_map.keys())}")

    async def disconnect(self, socket_id: str):
        with socket_connection_lock:
            if socket_id not in self.active_connections_map:
                logger.debug(f"Client {socket_id} was already disconnected, skipping")
                return

            del self.active_connections_map[socket_id]

    # this method sends a message to all connected websockets
    async def broadcast(self, message: Union[dict[str, Any], WorkerJobResponse, TestSequenceMessage]):
        # Early return if no connections
        if not self.active_connections_map:
            logger.debug("No active WebSocket connections, skipping broadcast")
            return

        dead_connections: set[str] = set()

        with socket_connection_lock:
            for id, connection in self.active_connections_map.items():
                if id in dead_connections:
                    continue

                try:
                    await connection.send_text(json.dumps(message, cls=PlotlyJSONEncoder))
                except Exception as e:
                    logger.error(f"Error in broadcast to {id}: {e}\n{traceback.format_exc()}")
                    if connection.client_state == WebSocketState.DISCONNECTED:
                        logger.debug(f"Connection state for {id} is Disconnected, adding to dead_connection...")
                        dead_connections.add(id)

        for connection in dead_connections:
            await self.disconnect(socket_id=connection)
