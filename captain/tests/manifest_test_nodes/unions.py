from typing import Union

import numpy as np
from pkgs.atlasvibe.atlasvibe import (
    DataContainer,
    DataFrame,
    Image,
    Matrix,
    OrderedPair,
    OrderedTriple,
    atlasvibe_node,  # CHANGED
)


@atlasvibe_node(node_type="TEST_TYPE")  # CHANGED
def UNIONS(
    a: Matrix | DataFrame | Image,
    b: OrderedPair | OrderedTriple | DataContainer,
    c: Union[Matrix, DataFrame, Image],
    d: Union[OrderedPair, OrderedTriple, DataContainer],
    # foo: str | int = "bar",
) -> OrderedPair | OrderedTriple:
    q = np.array([])
    return OrderedTriple(x=q, y=q, z=q)
