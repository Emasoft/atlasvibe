# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import numpy as np
from flojoy import DataContainer, OrderedPair, atlasvibe_node # CHANGED


@atlasvibe_node(node_type="TEST_TYPE") # CHANGED
def BASIC(default: OrderedPair, other: DataContainer, some_param: int) -> OrderedPair:
    return OrderedPair(x=np.array([]), y=np.array([]))
