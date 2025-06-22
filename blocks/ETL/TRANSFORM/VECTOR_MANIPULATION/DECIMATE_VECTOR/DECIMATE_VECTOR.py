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
def DECIMATE_VECTOR(
    default: Vector,
    factor: int = 1,
) -> Vector:
    """The DECIMATE_VECTOR node returns the input vector by reducing the
    number of points by given factor

    Inputs
    ------
    default : Vector
        The input vector

    Parameters
    ----------
    factor : int
        Decimate factor which determines how many elements will be skipped
        between each selected element in the output vector

    Returns
    -------
    Vector
        Decimated vector
    """

    return Vector(v=default.v[::factor])
