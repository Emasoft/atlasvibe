# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import pandas as pd
import os
from pkgs.atlasvibe.atlasvibe.parameter_types import Directory
from typing import Optional
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import (
    DataFrame,
    Matrix,
    OrderedPair,
    OrderedTriple,
    DataContainer,
)


@atlasvibe
def EXPORT_CSV(
    dc: OrderedPair | OrderedTriple | DataFrame | Matrix,
    dir: Directory,
    filename: str = "exported.csv",
) -> Optional[DataContainer]:
    """Export a DataContainer into CSV format.

    Parameters
    ----------
    dc : OrderedPair|OrderedTriple|DataFrame
        The DataContainer to export.
    dir : Directory
        The directory to export to.
    filename : str
        The name of the file to output.

    Returns
    -------
    None
    """

    if dir is None:
        raise ValueError("Please select a directory to export the data to")

    path = os.path.join(dir.unwrap(), filename)

    match dc:
        case OrderedPair() | OrderedTriple():
            df = pd.DataFrame(dc)
            df = df.drop(columns=["type", "extra"])
            df.to_csv(path, index=False)
        case DataFrame():
            df = dc.m
            df.to_csv(path, index=False)
        case Matrix():
            df = pd.DataFrame(dc.m)
            df.to_csv(path, index=False, header=False)
        case _:
            raise ValueError(f"Invalid DataContainer type: {dc.type} cannot be exported as CSV.")

    return None
