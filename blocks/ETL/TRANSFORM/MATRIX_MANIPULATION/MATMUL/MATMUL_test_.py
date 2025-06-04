import numpy as np
from atlasvibe import Matrix


def test_MATMUL(mock_atlasvibe_decorator):
    import MATMUL

    x = np.eye(3)
    x[2, 0] = 1

    element = Matrix(m=x)
    res = MATMUL.MATMUL(a=element, b=element)

    assert np.array_equal(res.m, np.matmul(x, x))
