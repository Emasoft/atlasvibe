# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataFrame, Matrix


@atlasvibe
def DF_2_NP(default: DataFrame) -> Matrix:
    """Convert a DataFrame DataContainer to a Matrix DataContainer.

    Parameters
    ----------
    default : DataFrame
        The input dataframe to which we apply the conversion to.

    Returns
    -------
    Matrix
        The matrix result from the conversion of the input.
    """

    df = default.m
    df_to_numpy = df.to_numpy(dtype=object)

    return Matrix(m=df_to_numpy)
