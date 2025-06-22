# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import yaml
import os

with open(
    os.path.join(os.path.dirname(__file__), "STATUS_CODES.yml"),
    "r",
    encoding="utf-8",
) as f:
    STATUS_CODES = yaml.safe_load(f)
