# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector
from typing import TypedDict


class resultSplit(TypedDict):
    vector1: Vector
    vector2: Vector


@atlasvibe
def SPLIT_VECTOR(
    default: Vector,
    index: int = 0,
) -> resultSplit:
    """The SPLIT_VECTOR node returns a vector that is splited by a given index

    Inputs
    ------
    default : Vector
        The input vector

    Parameters
    ----------
    index : int
        index which you want to split your vector by

    Returns
    -------
    Vector
        Splited input vector
    """
    if index > len(default.v) - 1:
        raise ValueError(f"Given index is larger than the input vector, index: {index}")

    return resultSplit(
        vector1=Vector(default.v[:index]), vector2=Vector(default.v[index:])
    )
