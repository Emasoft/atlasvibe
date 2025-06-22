# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector, Matrix


@atlasvibe
def VECTOR_2_MATRIX(default: Vector, row: int, col: int) -> Matrix:
    """Convert a Vector DataContainer to a Matrix DataContainer.

    Inputs
    ------
    default: Vector
        The input vector that will be transformed into matrix.

    Parameters
    ----------
    row: int
        number of rows for the new matrix
    col: int
        number of columns for the new matrix
    Returns
    -------
    Matrix
        The matrix that is generated from the given vector and the parameters.
    """
    try:
        matrix = default.v.reshape((row, col))
        return Matrix(m=matrix)
    except Exception as e:
        print(e)
