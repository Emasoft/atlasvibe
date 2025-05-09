# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import numpy as np
from flojoy import DataFrame, Matrix, OrderedPair, atlasvibe_node # CHANGED


@atlasvibe_node(node_type="TEST_TYPE") # CHANGED
def MULTIPLE_INPUTS(
    a: OrderedPair, b: list[OrderedPair], c: list[Matrix | DataFrame], foo: list[int]
) -> Matrix:
    return Matrix(np.array([]))
