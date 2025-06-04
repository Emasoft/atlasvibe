import numpy as np
from atlasvibe import Vector


def test_VECTOR_LENGTH(mock_atlasvibe_decorator):
    import VECTOR_LENGTH

    x = np.ones(5)

    element = Vector(v=x)
    res = VECTOR_LENGTH.VECTOR_LENGTH(element)

    assert np.array_equal(res.c, 5)
