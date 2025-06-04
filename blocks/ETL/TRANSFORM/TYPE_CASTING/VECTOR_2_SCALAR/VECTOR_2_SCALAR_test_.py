from numpy import array
from atlasvibe import Vector


def test_VECTOR_2_SCALAR(mock_atlasvibe_decorator):
    import VECTOR_2_SCALAR

    x = array([True, False, True])
    iVector = Vector(v=x)

    result = 5

    rScalar = VECTOR_2_SCALAR.VECTOR_2_SCALAR(iVector)

    assert rScalar.c == result

    x = array([5, 1, 1])
    iVector = Vector(v=x)

    result = 7

    rScalar = VECTOR_2_SCALAR.VECTOR_2_SCALAR(iVector)

    assert rScalar.c == result
