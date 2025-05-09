# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import os
import logging
import yaml
from captain.utils.blocks_path import get_atlasvibe_dir # CHANGED

logger = logging.getLogger("atlasvibe") # CHANGED "flojoy" to "atlasvibe"


def load_log_level_from_config():
    atlasvibe_config_path = os.path.join(get_atlasvibe_dir(), "atlasvibe.yaml") # CHANGED flojoy.yaml to atlasvibe.yaml
    if os.path.exists(atlasvibe_config_path):
        with open(atlasvibe_config_path) as f:
            data = yaml.safe_load(f)
    else:
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
