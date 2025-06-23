# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from typing import Literal

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataFrame


@atlasvibe()
def SCIKIT_LEARN_DATASET(
    dataset_name: Literal[
        "iris", "diabetes", "digits", "linnerud", "wine", "breast_cancer"
    ] = "iris",
) -> DataFrame:
    """Retrieve a pandas DataFrame from the scikit-learn sample datasets.

    Parameters
    ----------
    dataset_name : str

    Returns
    -------
    DataFrame
        A DataContainer object containing the retrieved pandas DataFrame.
    """

    if dataset_name == "iris":
        from sklearn.datasets import load_iris

        iris = load_iris(as_frame=True, return_X_y=True)
        return DataFrame(df=iris[0])  # type: ignore

    elif dataset_name == "diabetes":
        from sklearn.datasets import load_diabetes

        iris = load_diabetes(as_frame=True, return_X_y=True)
        return DataFrame(df=iris[0])  # type: ignore

    elif dataset_name == "digits":
        from sklearn.datasets import load_digits

        iris = load_digits(as_frame=True, return_X_y=True)
        return DataFrame(df=iris[0])  # type: ignore

    elif dataset_name == "linnerud":
        from sklearn.datasets import load_linnerud

        iris = load_linnerud(as_frame=True, return_X_y=True)
        return DataFrame(df=iris[0])  # type: ignore

    elif dataset_name == "wine":
        from sklearn.datasets import load_wine

        iris = load_wine(as_frame=True, return_X_y=True)
        return DataFrame(df=iris[0])  # type: ignore

    elif dataset_name == "breast_cancer":
        from sklearn.datasets import load_breast_cancer

        iris = load_breast_cancer(as_frame=True, return_X_y=True)
        return DataFrame(df=iris[0])  # type: ignore

    else:
        raise ValueError(f"Failed to retrieve '{dataset_name}' from rdatasets package!")
