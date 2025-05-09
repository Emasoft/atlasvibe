# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import numpy as np
from flojoy import OrderedTriple, atlasvibe_node # CHANGED


@atlasvibe_node(node_type="TEST_TYPE") # CHANGED
def DEFAULT_VALUES(
    default: OrderedTriple, foo: str = "bar", nums: list[int] = [1, 2, 3]
) -> OrderedTriple:
    a = np.array([])
    return OrderedTriple(x=a, y=a, z=a)
