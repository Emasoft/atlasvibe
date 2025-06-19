from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def SORT_VECTOR(
    default: Vector,
    reverse: bool = False,
) -> Vector:
    """The SORT_VECTOR node returns the input Vector that is sorted

    Inputs
    ------
    default : Vector
        The input vector

    Parameters
    ----------
    reverse : bool
        If False, sort in ascending order. If True, descending order.

    Returns
    -------
    Vector
        Sorted input vector
    """
    return Vector(v=sorted(default.v, reverse=reverse))
