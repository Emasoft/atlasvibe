import numpy as np
from pkgs.atlasvibe.atlasvibe import DataFrame, Image, Matrix, atlasvibe_node  # CHANGED


@atlasvibe_node(deps={"tensorflow": "2.12.0", "torch": "2.0.1"}, node_type="TEST_TYPE")  # CHANGED
def EXTRA_DEPS(mat: Matrix, data: DataFrame) -> Image:
    a = np.array([])
    return Image(r=a, g=a, b=a, a=a)
