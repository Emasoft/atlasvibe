# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from numpy.random import permutation
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def SHUFFLE_VECTOR(
    default: Vector,
) -> Vector:
    """The SHUFFLE_VECTOR node returns a vector that is randomly shuffled.

    Parameters
    ----------
    default : Vector
        The vector to shuffle.

    Returns
    -------
    Vector
        Shuffled input vector
    """

    shuffledVector = permutation(default.v)

    return Vector(v=shuffledVector)
