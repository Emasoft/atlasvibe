from functools import wraps
from unittest.mock import patch

import numpy
import pandas as pd
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Matrix, DataFrame

# Python functions are decorated at module-loading time, So we'll need to patch our decorator
#  with a simple mock ,before loading the module.


def mock_atlasvibe_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)

    return decorated_function


# Patch the atlasvibe decorator that handles connecting our node to the App.
patch(
    "pkgs.atlasvibe.atlasvibe.atlasvibe_python.atlasvibe", mock_atlasvibe_decorator
).start()

# After Patching the atlasvibe decorator, let's load the node under test.


def test_APPEND():
    # create the two ordered pair datacontainers
    import APPEND

    element_a = OrderedPair(x=numpy.linspace(0, 10, 10), y=numpy.linspace(0, 10, 10))

    element_b = OrderedPair(x=numpy.linspace(11, 12, 1), y=numpy.linspace(11, 12, 1))

    # node under test
    res = APPEND.APPEND(element_a, element_b)

    # check that the correct number of elements
    assert (len(res.y)) == 11
    assert res.y[-1] == 11

    # create the two matrix datacontainers
    element_a = Matrix(m=numpy.ones((10, 10)))
    element_b = Matrix(m=numpy.ones((1, 10)))

    # node under test
    res = APPEND.APPEND(element_a, element_b)

    # check that the correct number of elements
    assert (res.m.shape) == (11, 10)

    # create the two dataframe datacontainers
    element_a = DataFrame(df=pd.DataFrame(numpy.ones((10, 10))))
    element_b = DataFrame(df=pd.DataFrame(numpy.ones((1, 10))))

    # node under test
    res = APPEND.APPEND(element_a, element_b)

    # check that the correct number of elements
    assert (res.m.shape) == (11, 10)
