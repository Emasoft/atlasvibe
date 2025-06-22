# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Scalar, DataContainer
from typing import Optional


@atlasvibe
def SCALAR(
    _: Optional[DataContainer] = None,
    value: float = 3.0,
) -> Scalar:
    """Return a single Scalar value.

    Parameters
    ----------
    value : float
        The value set in Parameters

    Returns
    -------
    Scalar
        c: return the value being set in Parameters
    """

    return Scalar(c=value)
