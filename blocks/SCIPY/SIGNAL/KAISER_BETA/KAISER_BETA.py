# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Matrix, Scalar
import numpy as np

import scipy.signal


@atlasvibe
def KAISER_BETA(
    default: OrderedPair | Matrix,
) -> OrderedPair | Matrix | Scalar:
    """The KAISER_BETA node is based on a numpy or scipy function.

    The description of that function is as follows:

        Compute the Kaiser parameter 'beta', given the attenuation 'a'.

    Parameters
    ----------
    a : float
        The desired attenuation in the stopband and maximum ripple in
        the passband, in dB.  This should be a *positive* number.

    Returns
    -------
    DataContainer
        type 'ordered pair', 'scalar', or 'matrix'
    """

    result = scipy.signal.kaiser_beta(
        a=default.y,
    )

    if isinstance(result, np.ndarray):
        result = OrderedPair(x=default.x, y=result)
    else:
        assert isinstance(result, np.number | float | int), (
            f"Expected np.number, float or int for result, got {type(result)}"
        )
        result = Scalar(c=float(result))

    return result
