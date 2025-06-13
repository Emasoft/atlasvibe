from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataContainer, String

@atlasvibe()
def DATACONTAINER_TYPE(
    default: DataContainer,
) -> String:
    """Return a String containing the input DataContainer type (e.g. Vector).

    Must use the TEXT_VIEW block to view the text.

    Parameters
    ----------
    default : DataContainer
        The input DataContainer to check the type.

    Returns
    -------
    DataContainer
        String: Input DataContainer type
    """

    return String(s=default.type)
