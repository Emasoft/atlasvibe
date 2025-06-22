# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Boolean


@atlasvibe
def OR(default: Boolean, a: Boolean) -> Boolean:
    """Takes two boolean data type and computs logical OR operation on them.

    Parameters
    ----------
    default : Boolean
        The input boolean to which we apply the OR operation.
    a : Boolean
        The input boolean to which we apply the OR operation.

    Returns
    -------
    Boolean
        The boolean result from the operation of the inputs.
    """
    if default.b or a.b:
        return Boolean(b=True)
    return Boolean(b=False)
