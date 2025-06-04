import logging
from atlasvibe import (
    DataContainer,
    atlasvibe,
    get_env_var,
    get_atlasvibe_cloud_url,
    node_preflight,
    DataFrame,
    Boolean,
)
import atlasvibe_cloud
import pandas as pd


@node_preflight
def preflight():
    api_key = get_env_var("ATLASVIBE_CLOUD_WORKSPACE_SECRET")

    if api_key is None:
        raise KeyError(
            "Atlasvibe Cloud key is not found! You can set it under Settings -> Environment Variables."
        )


@atlasvibe
def ATLASVIBE_CLOUD_DOWNLOAD(
    measurement_id: str,
) -> DataContainer:
    """Download a measurement from Atlasvibe Cloud (beta).

    Parameters
    ----------
    measurement_id : str
        The data measurement id of the data to be downloaded from Atlasvibe Cloud.

    Returns
    -------
    DataContainer
        The downloaded DataContainer will be returned as it is.
    """

    api_key = get_env_var("ATLASVIBE_CLOUD_WORKSPACE_SECRET")

    if api_key is None:
        raise KeyError(
            "Atlasvibe Cloud key is not found! You can set it under Settings -> Environment Variables."
        )

    cloud = atlasvibe_cloud.AtlasvibeCloud(
        workspace_secret=api_key, api_url=get_atlasvibe_cloud_url()
    )

    measurement = cloud.get_measurement(measurement_id)
    logging.info(measurement)
    match measurement.data["type"]:
        case "dataframe":
            return DataFrame(pd.DataFrame(measurement.data["value"]))
        case "boolean":
            return Boolean(measurement.data["value"])
        case _:
            raise NotImplementedError(
                f"Type {measurement.data['type']} is not implemented"
            )
