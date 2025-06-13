from numpy import unique
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector

@atlasvibe
def REMOVE_DUPLICATES_VECTOR(
    default: Vector,
) -> Vector:
    """The REMOVE_DUPLICATES_VECTOR node returns a vector with only unique elements.

    Parameters
    ----------
    default : Vector
        The input vector

    Returns
    -------
    Vector
        Unique input vector
    """

    return Vector(v=unique(default.v))
