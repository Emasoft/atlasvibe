import numpy as np
from atlasvibe import OrderedPair, Matrix, Scalar


def test_ANDERSON(mock_atlasvibe_decorator):
    import ANDERSON

    element_a = OrderedPair(x=np.ones(50), y=np.arange(1, 51))
    res = ANDERSON.ANDERSON(default=element_a)

    # check that the outputs are one of the correct types.
    assert isinstance(res, Scalar | OrderedPair | Matrix)
