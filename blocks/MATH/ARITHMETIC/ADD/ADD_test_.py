import numpy as np
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Vector, Scalar

def test_ADD_Vector_Vector(mock_atlasvibe_decorator):
    """Test ADD function correctly adds two vectors element-wise."""
    import ADD

    x = Vector(v=np.arange(-10, 10, 1))
    y = Vector(v=np.arange(-20, 20, 2))
    res = ADD.ADD(a=x, b=[y])

    np.testing.assert_allclose(res.v, x.v + y.v)

def test_ADD_Vector_Scalar(mock_atlasvibe_decorator):
    """Verify ADD function can add multiple scalar values to a vector."""
    import ADD

    x = Vector(v=np.arange(-10, 10, 1))
    res = ADD.ADD(a=x, b=[Scalar(c=2), Scalar(c=3)])

    np.testing.assert_allclose(res.v, x.v + 2 + 3)

def test_ADD_OrderedPair_Vector(mock_atlasvibe_decorator):
    """Test ADD function adds vector to y-coordinates of OrderedPair while preserving x-coordinates."""
    import ADD

    x = np.arange(-10, 10, 1)
    y = np.arange(-20, 20, 2)
    z = np.arange(-30, 30, 3)
    res = ADD.ADD(a=OrderedPair(x=x, y=y), b=[Vector(v=z)])

    np.testing.assert_allclose(res.x, x)
    np.testing.assert_allclose(res.y, y + z)
