# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import numpy as np
from flojoy import DataFrame, Image, Matrix, atlasvibe_node # CHANGED


@atlasvibe_node(deps={"tensorflow": "2.12.0", "torch": "2.0.1"}, node_type="TEST_TYPE") # CHANGED
def EXTRA_DEPS(mat: Matrix, data: DataFrame) -> Image:
    a = np.array([])
    return Image(r=a, g=a, b=a, a=a)
