import numpy as np
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Matrix, Scalar

def test_STFT(mock_atlasvibe_decorator):
    import STFT

    element_a = OrderedPair(x=np.ones(50), y=np.arange(1, 51))
    res = STFT.STFT(default=element_a)

    # check that the outputs are one of the correct types.
    assert isinstance(res, Scalar | OrderedPair | Matrix)
