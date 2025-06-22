# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Boolean, Scalar


@atlasvibe
def BOOLEAN_2_SCALAR(default: Boolean) -> Scalar:
    """Takes boolean type data and converts it into scalar data type.
    1 means true and 0 means false

    Parameters
    ----------
    default : Boolean
        The input boolean to which we apply the conversion to.
    Returns
    -------
    Scalar
        The scalar result from the conversion of the input.
    """
    if default.b:
        return Scalar(c=1)
    return Scalar(c=0)
