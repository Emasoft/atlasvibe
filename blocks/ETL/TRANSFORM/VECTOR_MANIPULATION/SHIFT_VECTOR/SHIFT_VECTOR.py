# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from numpy import roll
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def SHIFT_VECTOR(default: Vector, shift: int = 1) -> Vector:
    """The SHIFT_VECTOR node shifts the elements in the vector by the amount specified

    Inputs
    ------
    v : Vector
        The input vector to shift elements from

    Parameters
    ----------
    shift: int
        the number of places in which elements are moved (negative values will shift them to the left)

    Returns
    -------
    Vector
        The new vector with elements shifted
    """

    v = roll(default.v, shift)
    return Vector(v=v)
