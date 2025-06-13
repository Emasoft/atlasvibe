from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Boolean

@atlasvibe
def IMPLIES(x: Boolean, y: Boolean) -> Boolean:
    """Takes two boolean data type and computs logical IMPLIES operation on them.
    x implies y

    Parameters
    ----------
    x : Boolean
        The input boolean to which we apply the IMPLIES operation.
    y : Boolean
        The input boolean to which we apply the IMPLIES operation.

    Returns
    -------
    Boolean
        The boolean result from the operation of the inputs.
    """
    if x.b and not y.b:
        return Boolean(b=False)
    return Boolean(b=True)
