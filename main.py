# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import os

import uvicorn

from atlasvibe_engine.utils.logger import load_log_level_from_config # Rebranded

__ignore_list = ["venv"]


if __name__ == "__main__":
    log_level = load_log_level_from_config().lower()
    is_dev = os.environ.get("DEPLOY_STATUS", "prod") == "dev"
    uvicorn.run(
        "captain.main:app",
        port=5392,
        log_level=log_level,
        reload=is_dev,
        reload_excludes=[
            os.path.join(os.getcwd(), p)
            for p in __ignore_list
            if os.path.exists(os.path.join(os.getcwd(), p))
        ],
    )
