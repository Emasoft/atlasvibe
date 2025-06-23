# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import numpy as np
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Scalar, Vector

from blocks.MATH.ARITHMETIC.utils.arithmetic_utils import perform_arithmetic_operation


@atlasvibe
def ADD_1(a: OrderedPair | Scalar | Vector, b: list[OrderedPair | Scalar | Vector]) -> OrderedPair | Scalar | Vector:
    """Add two or more numeric arrays, matrices, dataframes, or constants element-wise.

    When a constant is added to an array or matrix, each element in the array or matrix will be increased by the constant value.

    If two arrays or matrices of different sizes are added, the output will be the size of the larger array or matrix with only the overlapping elements changed.

    Parameters
    ----------
    a : OrderedPair|Scalar|Vector
        The input a use to compute the sum of a and b.
    b : OrderedPair|Scalar|Vector
        The input b use to compute the sum of a and b.

    Returns
    -------
    OrderedPair|Scalar|Vector
        OrderedPair if a is an OrderedPair.
        x: the x-axis of input a.
        y: the sum of input a and input b.

        Scalar if a is a Scalar.
        c: the sum of input a and input b.

        Vector if a is a Vector.
        v: the sum of input a and input b.
    """
    return perform_arithmetic_operation(a, b, np.add)
