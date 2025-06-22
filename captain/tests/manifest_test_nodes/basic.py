import numpy as np
from pkgs.atlasvibe.atlasvibe import (
    DataContainer,
    OrderedPair,
    atlasvibe_node,
)  # CHANGED


@atlasvibe_node(node_type="TEST_TYPE")  # CHANGED
def BASIC(default: OrderedPair, other: DataContainer, some_param: int) -> OrderedPair:
    return OrderedPair(x=np.array([]), y=np.array([]))
