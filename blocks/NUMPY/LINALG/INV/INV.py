# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Matrix, Scalar
import numpy as np

import numpy.linalg


@atlasvibe
def INV(
    default: Matrix,
) -> Matrix | Scalar:
    """The INV node is based on a numpy or scipy function.

    The description of that function is as follows:

        Compute the (multiplicative) inverse of a matrix.

        Given a square matrix 'a', return the matrix 'ainv', satisfying "dot(a, ainv) = dot(ainv, a) = eye(a.shape[0])".

    Parameters
    ----------
    a : (..., M, M) array_like
        Matrix to be inverted.

    Returns
    -------
    DataContainer
        type 'ordered pair', 'scalar', or 'matrix'
    """

    result = numpy.linalg.inv(
        a=default.m,
    )

    if isinstance(result, np.ndarray):
        result = Matrix(m=result)
    else:
        assert isinstance(result, np.number | float | int), f"Expected np.number, float or int for result, got {type(result)}"
        result = Scalar(c=float(result))

    return result
