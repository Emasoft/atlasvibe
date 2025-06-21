# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import os
import logging
import yaml
from atlasvibe_engine.utils.blocks_path import (
    get_atlasvibe_dir,
)  # CHANGED: Assuming this file will be part of atlasvibe_engine

logger = logging.getLogger("atlasvibe")


def load_log_level_from_config() -> str:
    atlasvibe_dir = get_atlasvibe_dir()
    atlasvibe_config_path = os.path.join(atlasvibe_dir, "atlasvibe.yaml")
    if os.path.exists(atlasvibe_config_path):
        with open(atlasvibe_config_path) as f:
            data = yaml.safe_load(f)
    else:
        # Create directory if it doesn't exist
        os.makedirs(atlasvibe_dir, exist_ok=True)
        with open(atlasvibe_config_path, "w") as f:
            data = {"LOG_LEVEL": "INFO"}
            f.write(yaml.dump(data))

    log_level = data.get("LOG_LEVEL", "INFO")
    return log_level


logging.basicConfig(
    level=load_log_level_from_config(),
    format="[%(asctime)s] - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
