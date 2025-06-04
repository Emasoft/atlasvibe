import numpy as np
from atlasvibe import Vector


def test_DC_CONTENT_TYPE(mock_atlasvibe_decorator):
    import DC_CONTENT_TYPE

    input = Vector(v=np.arange(0, 50))
    res = DC_CONTENT_TYPE.DC_CONTENT_TYPE(input)

    assert res.s == f"v: {type(np.arange(0, 50))}"
