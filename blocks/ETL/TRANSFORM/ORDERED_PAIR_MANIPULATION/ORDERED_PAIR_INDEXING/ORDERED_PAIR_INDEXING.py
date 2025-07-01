# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Scalar


@atlasvibe
def ORDERED_PAIR_INDEXING(
    default: OrderedPair,
    index: int = 0,
    x_axis: bool = False,
) -> Scalar:
    """Returns the value of the OrderedPair at the requested index.

    Parameters
    ----------
    default : OrderedPair
        The input OrderedPair to index.
    index : int
        The index of the OrderedPair to return.
    x_axis : bool
        Index x axis? If not y is indexed.

    Returns
    -------
    Scalar
        The scalar index of the input OrderedPair.
    """

    assert len(default.x) > index, "The index parameter must be less than the length of the OrderedPair."
    assert index >= 0, "The index parameter must be greater than zero."

    if x_axis:
        c = default.x[index]
    else:
        c = default.y[index]

    return Scalar(c=c)
