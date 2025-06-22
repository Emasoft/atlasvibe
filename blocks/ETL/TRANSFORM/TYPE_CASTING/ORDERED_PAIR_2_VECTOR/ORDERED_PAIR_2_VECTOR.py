# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector, OrderedPair
from typing import TypedDict


class ResultSplit(TypedDict):
    x: Vector
    y: Vector


@atlasvibe
def ORDERED_PAIR_2_VECTOR(default: OrderedPair) -> ResultSplit:
    """Returns the split components (x, y) of an ordered pair as Vectors.

    Parameters
    ----------
    default : OrderedPair
        The input OrderedPair.

    Returns
    -------
    TypedDict:
        x: Vector from input x
        y: Vector from input y
    """

    return ResultSplit(x=Vector(v=default.x), y=Vector(v=default.y))
