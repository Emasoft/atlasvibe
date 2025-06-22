# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import pandas as pd
import numpy as np
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import (
    DataContainer,
    DataFrame,
    OrderedPair,
    OrderedTriple,
    Matrix,
    Grayscale,
    Image,
    ParametricDataFrame,
    ParametricOrderedPair,
    ParametricOrderedTriple,
    ParametricMatrix,
    ParametricGrayscale,
    ParametricImage,
)


@atlasvibe
def NP_2_DF(default: DataContainer) -> DataFrame:
    """Infer the type of an array-like DataContainer, then convert it to a DataFrame DataContainer'.

    Parameters
    ----------
    default : DataContainer
        The input numpy array which we apply the conversion to.

    Returns
    -------
    DataFrame
        The dataframe result from the conversion of the input.
    """

    match default:
        case DataFrame() | ParametricDataFrame():
            return default

        case OrderedPair() | ParametricOrderedPair():
            df = pd.DataFrame(default.y)
            return DataFrame(df=df)

        case OrderedTriple() | ParametricOrderedTriple():
            df = pd.DataFrame(default.z)
            return DataFrame(df=df)

        case Matrix() | ParametricMatrix():
            np_array = np.asarray(default.m)
            df = pd.DataFrame(np_array)
            return DataFrame(df=df)
        case Grayscale() | ParametricGrayscale():
            np_array = np.asarray(default.m)
            df = pd.DataFrame(np_array)
            return DataFrame(df=df)

        case Image() | ParametricImage():
            red = default.r
            green = default.g
            blue = default.b

            if default.a is None:
                merge = np.stack((red, green, blue), axis=2)
                merge = merge.reshape(-1, merge.shape[-1])
                df = pd.DataFrame(merge)
                return DataFrame(df=df)
            else:
                alpha = default.a
                merge = np.stack((red, green, blue, alpha), axis=2)
                merge = merge.reshape(-1, merge.shape[-1])
                df = pd.DataFrame(merge)
                return DataFrame(df=df)
        case _:
            raise ValueError("unsupported DataContainer type passed for NP_2_DF")
