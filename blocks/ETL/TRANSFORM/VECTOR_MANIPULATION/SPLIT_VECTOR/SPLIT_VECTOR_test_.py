import numpy as np
from atlasvibe import Vector


def test_SPLIT_VECTOR(mock_atlasvibe_decorator):
    import SPLIT_VECTOR

    x = np.array([3, 5, 1, 6, 5])

    inputVector = Vector(v=x)

    result = np.array([3, 5])

    splitX = SPLIT_VECTOR.SPLIT_VECTOR(inputVector, 2)

    assert np.array_equal(splitX["vector1"].v, result)
