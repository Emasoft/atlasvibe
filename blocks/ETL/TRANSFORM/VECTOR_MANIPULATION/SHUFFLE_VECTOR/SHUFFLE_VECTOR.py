from numpy.random import permutation
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def SHUFFLE_VECTOR(
    default: Vector,
) -> Vector:
    """The SHUFFLE_VECTOR node returns a vector that is randomly shuffled.

    Parameters
    ----------
    default : Vector
        The vector to shuffle.

    Returns
    -------
    Vector
        Shuffled input vector
    """

    shuffledVector = permutation(default.v)

    return Vector(v=shuffledVector)
