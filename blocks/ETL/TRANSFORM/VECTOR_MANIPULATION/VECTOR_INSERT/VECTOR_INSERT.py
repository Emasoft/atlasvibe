# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from numpy import concatenate
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Vector


@atlasvibe
def VECTOR_INSERT(default: Vector, index: int = 0, value: int = 0) -> Vector:
    """The VECTOR_INSERT node inserts a value to the Vector at the
    specified index.

    Inputs
    ------
    v : Vector
        The input vector to insert value.

    Parameters
    ----------
    element: int
        The value to add to the input vector.

    index: int
        The index of the vector to insert value.

    Returns
    -------
    Vector
        The new vector that contains the inserted value
    """

    assert len(default.v) > index, "The index parameter must be less than the length of the Vector."
    assert index >= 0, "The index parameter must be greater than zero."

    if index == len(default.v) - 1:
        v = concatenate((default.v, [value]))
    else:
        v = concatenate((default.v[:index], [value], default.v[index:]))

    return Vector(v=v)
