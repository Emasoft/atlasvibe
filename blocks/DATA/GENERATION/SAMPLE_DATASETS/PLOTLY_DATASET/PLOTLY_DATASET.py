# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataFrame
from plotly.express import data
from typing import Literal


@atlasvibe
def PLOTLY_DATASET(
    dataset_key: Literal[
        "wind",
        "iris",
        "carshare",
        "tips",
        "election",
        "experiment",
        "gapminder",
        "medals_long",
        "medals_wide",
        "stocks",
    ] = "wind",
) -> DataFrame:
    """Retrieve a pandas DataFrame from one of Plotly Express's built-in datasets.

    Parameters
    ----------
    dataset_key : str

    Returns
    -------
    DataFrame
    """

    df = getattr(data, dataset_key)()

    return DataFrame(df=df)
