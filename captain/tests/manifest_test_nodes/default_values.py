import numpy as np
from pkgs.atlasvibe.atlasvibe import OrderedTriple, atlasvibe_node  # CHANGED


@atlasvibe_node(node_type="TEST_TYPE")  # CHANGED
def DEFAULT_VALUES(
    default: OrderedTriple, foo: str = "bar", nums: list[int] = None
) -> OrderedTriple:
    if nums is None:
        nums = [1, 2, 3]
    a = np.array([])
    return OrderedTriple(x=a, y=a, z=a)
