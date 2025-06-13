from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector, Scalar

@atlasvibe
def VECTOR_LENGTH(default: Vector) -> Scalar:
    """The VECTOR_LENGTH node returns the length of the input vector.

    Parameters
    ----------
    v : Vector
        The input vector to find the length of.

    Returns
    -------
    Scalar
        The length of the input vector.
    """

    return Scalar(c=len(default.v))
