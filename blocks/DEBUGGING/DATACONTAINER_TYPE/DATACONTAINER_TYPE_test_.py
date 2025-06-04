import numpy as np
from atlasvibe import Vector


def test_DATACONTAINER_TYPE(mock_atlasvibe_decorator):
    import DATACONTAINER_TYPE

    input = Vector(v=np.arange(0, 50))
    res = DATACONTAINER_TYPE.DATACONTAINER_TYPE(input)

    assert res.s == "Vector"
