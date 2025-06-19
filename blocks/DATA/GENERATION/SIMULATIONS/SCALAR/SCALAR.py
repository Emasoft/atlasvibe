from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Scalar, DataContainer
from typing import Optional


@atlasvibe
def SCALAR(
    _: Optional[DataContainer] = None,
    value: float = 3.0,
) -> Scalar:
    """Return a single Scalar value.

    Parameters
    ----------
    value : float
        The value set in Parameters

    Returns
    -------
    Scalar
        c: return the value being set in Parameters
    """

    return Scalar(c=value)
