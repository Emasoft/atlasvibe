import numpy as np
from atlasvibe import Scalar, Vector, atlasvibe


@atlasvibe
def VECTOR_MIN(default: Vector) -> Scalar:
    """The VECTOR_MIN node returns the minimum value from the Vector

    Parameters
    ----------
    v : Vector
        The input vector to use min peration

    Returns
    -------
    Scalar
        The minimum value found from the input vector
    """

    return Scalar(c=np.min(default.v))
