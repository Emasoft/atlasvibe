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

import scipy.stats


@atlasvibe
def SEM(
    default: OrderedPair | Matrix,
    axis: int = 0,
    ddof: int = 1,
    nan_policy: str = "propagate",
) -> OrderedPair | Matrix | Scalar:
    """The SEM node is based on a numpy or scipy function.

    The description of that function is as follows:

        Compute the standard error of the mean.

        Calculate the standard error of the mean (or standard error of measurement) of the values in the input array.

    Parameters
    ----------
    a : array_like
        An array containing the values for which the standard error is returned.
    axis : int or None, optional
        Axis along which to operate.
        Default is 0.
        If None, compute over the whole array 'a'.
    ddof : int, optional
        Delta degrees-of-freedom. How many degrees of freedom to adjust
        for bias in limited samples relative to the population estimate of variance.
        Defaults to 1.
    nan_policy : {'propagate', 'raise', 'omit'}, optional
        Defines how to handle when input contains nan.
        The following options are available (default is 'propagate'):
        'propagate' : returns nan
        'raise' : raises an error
        'omit' : performs the calculations ignoring nan values

    Returns
    -------
    DataContainer
        type 'ordered pair', 'scalar', or 'matrix'
    """

    result = scipy.stats.sem(
        a=default.y,
        axis=axis,
        ddof=ddof,
        nan_policy=nan_policy,
    )

    if isinstance(result, np.ndarray):
        result = OrderedPair(x=default.x, y=result)
    else:
        assert isinstance(result, np.number | float | int), f"Expected np.number, float or int for result, got {type(result)}"
        result = Scalar(c=float(result))

    return result
