# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import numpy as np
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Scalar, Vector


@atlasvibe
def VECTOR_MIN(default: Vector) -> Scalar:
    """The VECTOR_MIN node returns the minimum value from the Vector

    Parameters
    ----------
    v : Vector
        The input vector to use min peration

    Returns
    -------
    Scalar
        The minimum value found from the input vector
    """

    return Scalar(c=np.min(default.v))
