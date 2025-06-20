from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import String, DataContainer
from typing import Optional
from pkgs.atlasvibe.atlasvibe.parameter_types import TextArea


@atlasvibe
def TEXT_1(
    _: Optional[DataContainer] = None,
    value: TextArea = TextArea("Hello World!"),
) -> String:
    """Return a String DataContainer with given input text.

    Parameters
    ----------
    value : str
        The value set in Parameters.

    Returns
    -------
    String
        Return the value being set in Parameters.
    """

    return String(s=value)
