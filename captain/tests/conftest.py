from importlib import reload

import atlasvibe  # This import is fine, as 'atlasvibe' is the package name
import pytest


@pytest.fixture
def reload_atlasvibe_node_module():  # RENAMED fixture
    reload(atlasvibe)  # Reloads the module where @atlasvibe_node is defined
