# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def SORT_VECTOR(
    default: Vector,
    reverse: bool = False,
) -> Vector:
    """The SORT_VECTOR node returns the input Vector that is sorted

    Inputs
    ------
    default : Vector
        The input vector

    Parameters
    ----------
    reverse : bool
        If False, sort in ascending order. If True, descending order.

    Returns
    -------
    Vector
        Sorted input vector
    """
    return Vector(v=sorted(default.v, reverse=reverse))
