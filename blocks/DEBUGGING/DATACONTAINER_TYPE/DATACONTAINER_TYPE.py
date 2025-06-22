# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataContainer, String


@atlasvibe()
def DATACONTAINER_TYPE(
    default: DataContainer,
) -> String:
    """Return a String containing the input DataContainer type (e.g. Vector).

    Must use the TEXT_VIEW block to view the text.

    Parameters
    ----------
    default : DataContainer
        The input DataContainer to check the type.

    Returns
    -------
    DataContainer
        String: Input DataContainer type
    """

    return String(s=default.type)
