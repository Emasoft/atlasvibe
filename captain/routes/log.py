# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import logging

from fastapi import APIRouter, Response

from captain.types.log import LogLevel
from captain.utils.blocks_path import get_atlasvibe_dir  # CHANGED
import os
import yaml

router = APIRouter(tags=["log_level"])


@router.get("/log_level")
async def get_log_level() -> LogLevel:
    return LogLevel(level=logging.getLevelName(logging.getLogger().level))


@router.post("/log_level")
async def set_log_level(log_level: LogLevel):
    level = log_level.level
    logging.getLogger().setLevel(level)
    logging.getLogger("uvicorn").setLevel(level)

    atlasvibe_config_path = os.path.join(
        get_atlasvibe_dir(), "atlasvibe.yaml"
    )  # CHANGED
    # Persist log level to disk
    with open(atlasvibe_config_path) as f:
        data = yaml.safe_load(f)

    data["LOG_LEVEL"] = level
    with open(atlasvibe_config_path, "w+") as f:
        yaml.safe_dump(data, f)

    return Response(status_code=200)
