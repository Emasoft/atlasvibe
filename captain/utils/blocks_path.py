# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import os
from pathlib import Path


def get_blocks_path() -> str:
    return os.path.join(os.getcwd(), "blocks")


def get_atlasvibe_dir():  # RENAMED
    dir_path = os.path.abspath(
        os.path.join(Path.home(), ".atlasvibe")
    )  # CHANGED .atlasvibe to .atlasvibe
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    return dir_path
