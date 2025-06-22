# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import numpy as np
from scipy.interpolate import BSpline
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

    # Create a centered B-spline basis element to match the old scipy.signal.bspline behavior
    # The old function evaluated y_i = B^n(x_i + (n+1)/2)
    x = default.y
    # Create knots for a centered B-spline
    knots = np.arange(-(n + 1) / 2, (n + 1) / 2 + 1)
    # Create the B-spline basis element
    basis = BSpline.basis_element(knots)
    # Evaluate at the shifted points
    result = basis(x + (n + 1) / 2)

    if isinstance(result, np.ndarray):
        result = OrderedPair(x=default.x, y=result)
    else:
        assert isinstance(result, np.number | float | int), (
            f"Expected np.number, float or int for result, got {type(result)}"
        )
        result = Scalar(c=float(result))

    return result
