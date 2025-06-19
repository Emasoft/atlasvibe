import numpy as np
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Matrix, Scalar


def test_CUBIC(mock_atlasvibe_decorator):
    import CUBIC

    element_a = OrderedPair(x=np.ones(50), y=np.arange(1, 51))
    res = CUBIC.CUBIC(default=element_a)

    # check that the outputs are one of the correct types.
    assert isinstance(res, Scalar | OrderedPair | Matrix)
