# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pydantic import BaseModel


class PostCancelFC(BaseModel):
    jobsetId: str | None = None


class PostWFC(BaseModel):
    fc: str
    jobsetId: str
    cancelExistingJobs: bool
    observeBlocks: list[str]
    nodeDelay: float
    maximumRuntime: float
    maximumConcurrentWorkers: int
    projectPath: str | None = None


class WorkerSuccessResponse(BaseModel):
    node_id: str
    result: dict


class WorkerFailedResponse(BaseModel):
    node_id: str
    result: dict
