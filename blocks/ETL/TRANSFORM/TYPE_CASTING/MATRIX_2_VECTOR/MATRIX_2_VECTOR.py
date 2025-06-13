from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector, Matrix

@atlasvibe
def MATRIX_2_VECTOR(default: Matrix) -> Vector:
    """Convert a Matrix DataContainer to a Vector DataContainer.

    Parameters
    ----------
    default: Matrix
        The input matrix that will be transformed into vector data type.

    Returns
    -------
    Vector
        Vector that is flatten from input matrix.
    """
    rVector = default.m.flatten()

    return Vector(v=rVector)
