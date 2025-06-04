from numpy import asarray
import pandas as pd
from atlasvibe import atlasvibe, Matrix, DataFrame


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
