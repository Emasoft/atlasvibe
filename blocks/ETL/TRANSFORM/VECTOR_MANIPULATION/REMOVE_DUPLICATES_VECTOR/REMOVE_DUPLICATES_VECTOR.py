# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from numpy import unique
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def REMOVE_DUPLICATES_VECTOR(
    default: Vector,
) -> Vector:
    """The REMOVE_DUPLICATES_VECTOR node returns a vector with only unique elements.

    Parameters
    ----------
    default : Vector
        The input vector

    Returns
    -------
    Vector
        Unique input vector
    """

    return Vector(v=unique(default.v))
