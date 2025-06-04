import numpy as np
from atlasvibe import OrderedPair, Matrix, Scalar


def test_JARQUE_BERA(mock_atlasvibe_decorator):
    import JARQUE_BERA

    element_a = OrderedPair(x=np.ones(50), y=np.arange(1, 51))
    res = JARQUE_BERA.JARQUE_BERA(default=element_a)

    # check that the outputs are one of the correct types.
    assert isinstance(res, Scalar | OrderedPair | Matrix)
