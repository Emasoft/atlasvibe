from numpy import transpose
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Matrix


@atlasvibe
def TRANSPOSE_MATRIX(default: Matrix) -> Matrix:
    """Take an input 2D matrix and transpose it.

    Parameters
    ----------
    a : Matrix
        The input matrix to be transposed

    Returns
    -------
    Matrix
        The transposed matrix
    """

    return Matrix(m=transpose(default.m, (1, 0)))
