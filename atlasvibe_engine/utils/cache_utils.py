# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import os
from pathlib import Path

# Define the base cache directory for AtlasVibe
# This typically resides in the user's standard cache location.
# Example: ~/.cache/atlasvibe on Linux/macOS
# Example: C:\Users\<username>\AppData\Local\Emasoft\atlasvibe\Cache on Windows
USER_CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
ATLASVIBE_CACHE_DIR = USER_CACHE_DIR / "atlasvibe"

# You might want to ensure this directory exists when the module is loaded,
# though often it's better to create it on first use.
# For now, we'll just define the path.
# if not ATLASVIBE_CACHE_DIR.exists():
#     ATLASVIBE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Placeholder for other cache related utilities if needed in the future
