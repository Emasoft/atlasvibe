# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from numpy import transpose
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Matrix


@atlasvibe
def TRANSPOSE_MATRIX(default: Matrix) -> Matrix:
    """Take an input 2D matrix and transpose it.

    Parameters
    ----------
    a : Matrix
        The input matrix to be transposed

    Returns
    -------
    Matrix
        The transposed matrix
    """

    return Matrix(m=transpose(default.m, (1, 0)))
