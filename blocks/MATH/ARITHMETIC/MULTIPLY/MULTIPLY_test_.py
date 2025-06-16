import numpy as np

from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Vector, Scalar

def test_MULTIPLY_Vector_Vector(mock_atlasvibe_decorator):
    """Test multiplication of two vectors element-wise."""
    import MULTIPLY

    x = Vector(v=np.arange(10, 20, 1))
    y = Vector(v=np.arange(20, 30, 1))
    res = MULTIPLY.MULTIPLY(a=x, b=[y])

    np.testing.assert_allclose(res.v, x.v * y.v)

def test_MULTIPLY_Vector_Scalar(mock_atlasvibe_decorator):
    """Test multiplication of a vector by multiple scalar values."""
    import MULTIPLY

    x = Vector(v=np.arange(-10, 10, 1))
    res = MULTIPLY.MULTIPLY(a=x, b=[Scalar(c=2), Scalar(c=3)])

    np.testing.assert_allclose(res.v, (x.v * 2) * 3)

def test_MULTIPLY_OrderedPair_Vector(mock_atlasvibe_decorator):
    """Test multiplication of OrderedPair's y-values by a vector."""
    import MULTIPLY

    x = np.arange(10, 20, 1)
    y = np.arange(20, 30, 1)
    z = np.arange(30, 40, 1)
    res = MULTIPLY.MULTIPLY(a=OrderedPair(x=x, y=y), b=[Vector(v=z)])

    np.testing.assert_allclose(res.x, x)
    np.testing.assert_allclose(res.y, y * z)
