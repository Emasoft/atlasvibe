# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import numpy as np
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataFrame, Matrix
from pkgs.atlasvibe.atlasvibe.parameter_types import Array


@atlasvibe
def EXTRACT_COLUMNS(default: DataFrame | Matrix, columns: Array) -> DataFrame:
    """Take an input dataframe/matrix and returns a dataframe/matrix with only the specified columns.

    Parameters
    ----------
    default : DataFrame|Matrix
        Input to use as the table for column extraction
    columns : list of str or list of int
        The columns to extract from the input dataframe

    Returns
    -------
    DataFrame|Matrix
        DataFrame or Matrix with only the specified columns
    """

    if isinstance(default, DataFrame):
        df = default.m
        new_df = df[columns.unwrap()] if columns else df
        return DataFrame(df=new_df)
    else:
        matrix = default.m
        indices = np.array(columns.unwrap(), dtype=int)
        new_matrix = matrix[:, indices] if columns else matrix
        return Matrix(m=new_matrix)
