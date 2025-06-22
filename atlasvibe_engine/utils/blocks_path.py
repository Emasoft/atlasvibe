#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created blocks_path module with get_atlasvibe_dir function
# - Provides path utilities for atlasvibe configuration
#

"""Path utilities for atlasvibe configuration."""

import os
from pathlib import Path


def get_atlasvibe_dir() -> str:
    """Get the atlasvibe configuration directory path.

    Returns:
        str: Path to the .atlasvibe directory in the user's home.
    """
    return os.path.join(str(Path.home()), ".atlasvibe")
