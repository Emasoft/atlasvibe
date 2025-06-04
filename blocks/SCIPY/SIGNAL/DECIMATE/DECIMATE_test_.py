import numpy as np
from atlasvibe import OrderedPair, Matrix, Scalar


def test_DECIMATE(mock_atlasvibe_decorator):
    import DECIMATE

    element_a = OrderedPair(x=np.ones(50), y=np.arange(1, 51))
    res = DECIMATE.DECIMATE(default=element_a)

    # check that the outputs are one of the correct types.
    assert isinstance(res, Scalar | OrderedPair | Matrix)
