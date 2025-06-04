# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from importlib import reload

import atlasvibe # This import is fine, as 'atlasvibe' is the package name
import pytest


@pytest.fixture
def reload_atlasvibe_node_module(): # RENAMED fixture
    reload(atlasvibe) # Reloads the module where @atlasvibe_node is defined
