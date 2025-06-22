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


@atlasvibe
def ABS(default: OrderedPair | Vector | Scalar) -> OrderedPair:
    """Take an OrderedPair, Vector, or Scalar as input and return its absolute value.

    Parameters
    ----------
    default : OrderedPair|Vector|Scalar
        The input to apply the absolute value to.

    Returns
    -------
    OrderedPair
        x: the x-axis of the input.
        y: the absolute value of the input.
    """

    match default:
        case OrderedPair():
            x = default.x
            y = np.abs(default.y)
        case Scalar():
            x = default.c
            y = np.abs(x)
        case Vector():
            x = default.v
            y = np.abs(x)

    return OrderedPair(x=x, y=y)
