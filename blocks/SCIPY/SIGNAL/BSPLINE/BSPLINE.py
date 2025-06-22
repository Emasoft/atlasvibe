# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import numpy as np
import scipy.signal
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Matrix, OrderedPair, Scalar


@atlasvibe
def BSPLINE(
    default: OrderedPair | Matrix,
    n: int = 2,
) -> OrderedPair | Matrix | Scalar:
    """The BSPLINE node is based on a numpy or scipy function.

    The description of that function is as follows:

        B-spline basis function of order n.

    Parameters
    ----------
    x : array_like
        A knot vector.
    n : int
        The order of the spline. Must be non-negative, i.e. n >= 0.

    Returns
    -------
    DataContainer
        type 'ordered pair', 'scalar', or 'matrix'
    """

    result = scipy.signal.bspline(
        x=default.y,
        n=n,
    )

    if isinstance(result, np.ndarray):
        result = OrderedPair(x=default.x, y=result)
    else:
        assert isinstance(result, np.number | float | int), (
            f"Expected np.number, float or int for result, got {type(result)}"
        )
        result = Scalar(c=float(result))

    return result
