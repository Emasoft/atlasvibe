from typing import Optional

import numpy as np
from pkgs.atlasvibe.atlasvibe import (
    DataContainer,
    Matrix,
    OrderedPair,
    OrderedTriple,
    atlasvibe_node,
)  # CHANGED


@atlasvibe_node(node_type="TEST_TYPE")  # CHANGED
def OPTIONALS(
    a: Optional[OrderedPair | OrderedTriple] = None,
    b: Optional[Matrix] = None,
    c: Optional[DataContainer] = None,
    foo: Optional[str] = None,
    bar: Optional[list[int]] = None,
) -> Optional[OrderedPair]:
    q = np.array([])
    return OrderedPair(x=q, y=q)
