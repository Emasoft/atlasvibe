# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector, OrderedPair


@atlasvibe
def VECTOR_2_ORDERED_PAIR(default: Vector, y: Vector) -> OrderedPair:
    """Convert a Vector DataContainer to an OrderedPair DataContainer.

    Parameters
    ----------
    default : Vector
        The input vector that will be the x axis of OrderedPair.
    y : Vector
        The input vector that will be the y axis of OrderedPair.

    Returns
    -------
    OrderedPair
        The OrderedPair that is generated from the input vectors
    """

    return OrderedPair(x=default.v, y=y.v)
