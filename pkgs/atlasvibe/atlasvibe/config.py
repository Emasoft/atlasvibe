# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import logging

LOGGER_NAME = "atlasvibe"


class AtlasvibeConfig:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AtlasvibeConfig()
        return cls._instance

    def __init__(self):
        self.is_offline = False


logger = logging.getLogger(LOGGER_NAME)
