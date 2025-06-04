# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import os
from pathlib import Path


def get_blocks_path() -> str:
    return os.path.join(os.getcwd(), "blocks")


def get_atlasvibe_dir(): # RENAMED
    dir_path = os.path.abspath(os.path.join(Path.home(), ".atlasvibe")) # CHANGED .atlasvibe to .atlasvibe
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    return dir_path
