from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import pydantic
from captain.models.pytest.pytest_models import TestDiscoverContainer
from captain.models.test_sequencer import TestSequenceRun
from captain.utils.pytest.discover_tests import (
    discover_pytest_file,
    discover_robot_file,
)
from captain.utils.config import ts_manager
from captain.utils.test_sequencer.handle_data import handle_data
from captain.utils.logger import logger
from pydantic import BaseModel, Field
from threading import Thread

router = APIRouter(tags=["ws"])


@router.websocket("/ts-ws/{socket_id}")
async def websocket_endpoint(websocket: WebSocket, socket_id: str):
    if socket_id in list(ts_manager.ws.active_connections_map.keys()):
        logger.info(f"client {socket_id} is already connected!")
        return

    await ts_manager.ws.connect(websocket, socket_id=socket_id)
    logger.info(f"Accepted websocket {socket_id}")
    try:
        # await for messages and send messages (no need to read from frontend, this is used to keep connection alive)
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            data = pydantic.TypeAdapter(TestSequenceRun).validate_python(data)
            Thread(target=handle_data, args=((data,))).start()

    except WebSocketDisconnect:
        await ts_manager.ws.disconnect(socket_id=socket_id)
        logger.info(f"Client {socket_id} is disconnected")


class DiscoverParams(BaseModel):
    path: str
    one_file: bool = Field(..., alias="oneFile")

    @pydantic.field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path to prevent directory traversal attacks."""
        # Convert to absolute path and resolve any .. or . components
        import os

        abs_path = os.path.abspath(v)

        # Check if path contains suspicious patterns
        if ".." in v or v.startswith("/etc") or v.startswith("/root"):
            raise ValueError("Invalid path: potential security risk")

        # Ensure file exists and is readable
        if not os.path.exists(abs_path):
            raise ValueError(f"Path does not exist: {abs_path}")

        if not os.access(abs_path, os.R_OK):
            raise ValueError(f"Path is not readable: {abs_path}")

        return abs_path


@router.get("/discover/pytest/")
async def discover_pytest(params: DiscoverParams = Depends()):
    path = params.path
    one_file = params.one_file
    return_val, missing_lib, errors = [], [], []  # For passing info between threads
    thread = Thread(
        target=discover_pytest_file,
        args=(path, one_file, return_val, missing_lib, errors),
    )
    thread.start()
    thread.join()
    return TestDiscoverContainer(
        response=return_val,
        missing_libraries=missing_lib,
        error=errors[0] if len(errors) > 0 else None,
    )


@router.get("/discover/robot/")
async def discover_robot(params: DiscoverParams = Depends()):
    path = params.path
    one_file = params.one_file
    return_val, errors = [], []  # For passing info between threads
    thread = Thread(
        target=discover_robot_file,
        args=(path, one_file, return_val, errors),
    )
    thread.start()
    thread.join()
    return TestDiscoverContainer(
        response=return_val,
        missing_libraries=[],
        error=errors[0] if len(errors) > 0 else None,
    )
