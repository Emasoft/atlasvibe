# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Matrix, Scalar
import numpy as np
from scipy.interpolate import BSpline


@atlasvibe
def CUBIC(
    default: OrderedPair | Matrix,
) -> OrderedPair | Matrix | Scalar:
    """The CUBIC node is based on a numpy or scipy function.

    The description of that function is as follows:

        A cubic B-spline.
        This is a special case of 'bspline', and equivalent to "bspline(x, 3)".

    Parameters
    ----------
    x : array_like
        a knot vector

    Returns
    -------
    DataContainer
        type 'ordered pair', 'scalar', or 'matrix'
    """

    # Create a centered cubic B-spline basis element to match the old scipy.signal.cubic behavior
    # cubic(x) is equivalent to bspline(x, 3)
    x = default.y
    n = 3  # cubic
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
