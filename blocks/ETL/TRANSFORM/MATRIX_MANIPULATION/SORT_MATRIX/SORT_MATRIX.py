# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from numpy import sort
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Matrix


@atlasvibe
def SORT_MATRIX(a: Matrix, axis: int = -1) -> Matrix:
    """Take an input matrix and sort it along the chosen axis.

    Inputs
    ------
    a : Matrix
        The input matrix to be multiplied to input b

    Parameters
    ----------
    axis : int
        Axis along which to sort. Default is -1, which means sort along the last axis.

    Returns
    -------
    Matrix
        The matrix result from sorting.
    """
    inputMatrix = a.m
    sortedMatrix = sort(inputMatrix, axis=axis)

    return Matrix(m=sortedMatrix)
