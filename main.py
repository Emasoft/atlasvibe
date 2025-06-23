# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import os

import uvicorn

from atlasvibe_engine.utils.logger import load_log_level_from_config  # Rebranded

__ignore_list = ["venv"]


if __name__ == "__main__":
    log_level = load_log_level_from_config().lower()
    is_dev = os.environ.get("DEPLOY_STATUS", "prod") == "dev"
    uvicorn.run(
        "captain.main:app",
        port=5392,
        log_level=log_level,
        reload=is_dev,
        reload_excludes=[os.path.join(os.getcwd(), p) for p in __ignore_list if os.path.exists(os.path.join(os.getcwd(), p))],
    )
