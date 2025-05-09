# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from importlib import reload

import flojoy # This import is fine, as 'flojoy' is the package name
import pytest


@pytest.fixture
def reload_atlasvibe_node_module(): # RENAMED fixture
    reload(flojoy) # Reloads the module where @atlasvibe_node is defined
