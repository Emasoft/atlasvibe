# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import numpy as np
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataFrame
import pandas as pd
import traceback


@atlasvibe
def TIMESERIES_1(start_date: str = "2023-01-01", end_date: str = "2023-07-20") -> DataFrame:
    """Generate a timeseries with random y values between two dates.

    Parameters
    ----------
    start_date : str
        The start date of the timeseries in the format 'YYYY:MM:DD'.
    end_date : str
        The end date of the timeseries in the format 'YYYY:MM:DD'.

    Returns
    -------
    DataFrame
        m: the resulting timeseries
    """

    try:
        # Set the random seed for reproducibility
        np.random.seed(42)

        # Generate random time series data
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        num_days = (end - start).days + 1
        timestamps = pd.date_range(start=start, end=end, freq="D")
        data = np.random.randn(num_days)  # Random data points

        df = pd.DataFrame({"Timestamp": timestamps, "Data": data})

        return DataFrame(df=df)
    except Exception as e:
        print(traceback.format_exc())
        raise e
