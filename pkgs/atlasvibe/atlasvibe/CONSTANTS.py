# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import os
import sys

KEY_WORKER_JOBS = "WORKER_JOBS"
KEY_ALL_JOBEST_IDS = "ALL_JOBSET_IDS"
ATLASVIBE_DIR = ".atlasvibe"
CREDENTIAL_FILE = "credentials.txt"
if sys.platform == "win32":
    ATLASVIBE_CACHE_DIR = os.path.realpath(os.path.join(os.environ["APPDATA"], ATLASVIBE_DIR))
else:
    ATLASVIBE_CACHE_DIR = os.path.realpath(os.path.join(os.environ["HOME"], ATLASVIBE_DIR))

KEYRING_KEY = "ATLASVIBE_KEYRING_KEY"
