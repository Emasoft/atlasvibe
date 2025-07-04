# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from typing import Literal

try:
    from pydantic import BaseModel
except ImportError:
    from typing import Any

    BaseModel = Any  # type: ignore[misc,assignment]


class DocsVideo(BaseModel):
    source: Literal["youtube"]
    link: str
    title: str
