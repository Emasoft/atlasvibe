import numpy as np
from atlasvibe import Matrix


def test_INVERT(mock_atlasvibe_decorator):
    import INVERT

    x = np.eye(3)
    x[2, 0] = 1

    element = Matrix(m=x)
    res = INVERT.INVERT(element)

    print(x.T, res.m)

    assert np.array_equal(res.m, np.linalg.inv(x))
