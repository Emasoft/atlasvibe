# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import numpy as np
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Matrix, Scalar


@atlasvibe
def MATRIX(row: Scalar = 100, column: Scalar = 100) -> Matrix:
    """Generates a random matrix with values between 0 and 1.

    Parameters
    ----------
    row : Scalar
        number of rows
    column : Scalar
        number of columns

    Returns
    -------
    Matrix
        Randomly generated matrix
    """

    np.random.seed()

    mat = np.random.random_sample((row, column))

    return Matrix(m=mat)
