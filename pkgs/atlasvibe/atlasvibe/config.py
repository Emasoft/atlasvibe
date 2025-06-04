# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import logging

LOGGER_NAME = "atlasvibe"


class AtlasVibeConfig:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AtlasVibeConfig()
        return cls._instance

    def __init__(self):
        self.is_offline = False


logger = logging.getLogger(LOGGER_NAME)
