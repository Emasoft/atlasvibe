from numpy import stack
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def INTERLEAVE_VECTOR(
    default: Vector,
    a: list[Vector],
) -> Vector:
    """The INTERLEAVE_VECTOR node combine multiple vectors into a single vector type by interleaving their elements.

    Parameters
    ----------
    default : Vector
        The input vector

    Returns
    -------
    Vector
        Interleaved vector
    """
    interleavedVectors = [default.v]

    for i in range(len(a)):
        interleavedVectors = interleavedVectors + [a[i].v]

    interleavedVector = stack(interleavedVectors)
    interleavedVector = interleavedVector.T.flatten()

    return Vector(v=interleavedVector)
