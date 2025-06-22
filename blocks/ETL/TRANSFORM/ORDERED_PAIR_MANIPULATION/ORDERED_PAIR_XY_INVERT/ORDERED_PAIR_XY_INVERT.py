# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair


@atlasvibe
def ORDERED_PAIR_XY_INVERT(
    default: OrderedPair,
) -> OrderedPair:
    """Return an OrderedPair with the axes inverted.

    Parameters
    ----------
    default : OrderedPair
        The input OrderedPair that we would like to invert the axes.

    Returns
    -------
    OrderedPair
        The OrderedPair that is inverted.
    """

    return OrderedPair(x=default.y, y=default.x)
