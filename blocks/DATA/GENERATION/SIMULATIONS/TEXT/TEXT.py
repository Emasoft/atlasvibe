# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import String, DataContainer
from typing import Optional
from pkgs.atlasvibe.atlasvibe.parameter_types import TextArea


@atlasvibe
def TEXT(
    _: Optional[DataContainer] = None,
    value: TextArea = TextArea("Hello World!"),
) -> String:
    """Return a String DataContainer with given input text.

    Parameters
    ----------
    value : str
        The value set in Parameters.

    Returns
    -------
    String
        Return the value being set in Parameters.
    """

    return String(s=value)
