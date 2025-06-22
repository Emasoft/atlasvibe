# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pathlib import Path
import sys


def unload_module(path: str):
    module_name = Path(path).stem
    if module_name in sys.modules:
        del sys.modules[module_name]
