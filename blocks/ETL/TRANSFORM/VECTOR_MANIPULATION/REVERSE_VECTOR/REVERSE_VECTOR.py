# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from numpy import flip
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def REVERSE_VECTOR(
    default: Vector,
) -> Vector:
    """The REVERSE_VECTOR node returns a vector equal to the input vector but reversed.

    Parameters
    ----------
    default : Vector
        The input vector.

    Returns
    -------
    Vector
        Reversed input vector.
    """

    return Vector(v=flip(default.v))
