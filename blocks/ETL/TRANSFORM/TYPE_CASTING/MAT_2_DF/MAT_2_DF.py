from numpy import asarray
import pandas as pd
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Matrix, DataFrame


@atlasvibe
def MAT_2_DF(default: Matrix) -> DataFrame:
    """Convert a Matrix DataContainer to a DataFrame DataContainer.

    Parameters
    ----------
    default : Matrix
        The input matrix to which we apply the conversion to.

    Returns
    -------
    DataFrame
        The dataframe result from the conversion of the input.
    """

    np_data = default.m
    np_array = asarray(np_data)
    df = pd.DataFrame(np_array)

    return DataFrame(df=df)
