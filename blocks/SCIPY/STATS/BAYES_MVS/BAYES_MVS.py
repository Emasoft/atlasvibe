# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Matrix, Scalar

import scipy.stats


@atlasvibe
def BAYES_MVS(
    default: OrderedPair | Matrix,
    alpha: float = 0.9,
) -> OrderedPair | Matrix | Scalar:
    """The BAYES_MVS node is based on a numpy or scipy function.

    The description of that function is as follows:

        Bayesian confidence intervals for the mean, var, and std.

    Parameters
    ----------
    data : array_like
        Input data, if multi-dimensional it is flattened to 1-D by 'bayes_mvs'.
        Requires 2 or more data points.
    alpha : float, optional
        Probability that the returned confidence interval contains the true parameter.

    Returns
    -------
    DataContainer
        type 'ordered pair', 'scalar', or 'matrix'
    """

    result = OrderedPair(
        x=default.x,
        y=scipy.stats.bayes_mvs(
            data=default.y,
            alpha=alpha,
        ),
    )

    return result
