# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from typing import Optional

import numpy as np
from pkgs.atlasvibe.atlasvibe import DataContainer, Matrix, OrderedPair, OrderedTriple, atlasvibe_node # CHANGED


@atlasvibe_node(node_type="TEST_TYPE") # CHANGED
def OPTIONALS(
    a: Optional[OrderedPair | OrderedTriple] = None,
    b: Optional[Matrix] = None,
    c: Optional[DataContainer] = None,
    foo: Optional[str] = None,
    bar: Optional[list[int]] = None,
) -> Optional[OrderedPair]:
    q = np.array([])
    return OrderedPair(x=q, y=q)
