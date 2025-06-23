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
def DIVIDE(a: OrderedPair | Scalar | Vector, b: list[OrderedPair | Scalar | Vector]) -> OrderedPair | Scalar | Vector:
    """Divide two or more numeric arrays, matrices, dataframes, or constants element-wise.

    When a constant is divided into an array or matrix, each element in the array or matrix will be divided by the constant value.

    Parameters
    ----------
    a : OrderedPair|Scalar|Vector
        The input that will be divided by b.
    b : OrderedPair|Scalar|Vector
        The input that will divide a.

    Returns
    -------
    OrderedPair|Scalar|Vector
        OrderedPair if a is an OrderedPair.
        x: the x-axis of input a.
        y: the result of the division of input a by input b.

        Scalar if a is a Scalar.
        c: the result of the division of input a by input b.

        Vector if a is a Vector.
        v: the result of the division of input a by input b.
    """
    return perform_arithmetic_operation(a, b, np.divide)
