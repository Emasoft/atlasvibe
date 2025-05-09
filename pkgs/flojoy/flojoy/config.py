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
