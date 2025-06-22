# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Plotly
from pkgs.atlasvibe.atlasvibe.parameter_types import TextArea


@atlasvibe
def ANNOTATE_PLOTLY(
    default: Plotly,
    title: str = "",
    caption: TextArea = TextArea(""),
    # xaxis: str = "",
    # yaxis: str = "",
) -> Plotly:
    """Add context to a Plotly figure (title, caption, and axis labels).

    Parameters
    ----------
    default : Plotly
        The Plotly figure object

    Returns
    -------
    Plotly
        The annotated Plotly object
    """

    ATLASVIBE_COLORS = ["#7B61FF", "#2E83FF", "#FFA927", "#E14092"]

    fig = default.fig

    # Set marker colors to Atlasvibe brand
    for i in range(len(fig["data"])):
        if i < len(ATLASVIBE_COLORS):
            if "marker" in fig["data"][i]:
                fig["data"][i]["marker"]["color"] = ATLASVIBE_COLORS[i]

    fig["layout"]["title"] = {"text": title, "font": {"color": "rgba(0,0,0,0)"}}
    fig["layout"]["annotations"] = [
        {"text": caption, "showarrow": False, "visible": False}
    ]

    # 3d only
    if "scene" in fig["layout"]:
        fig["layout"]["scene"]["aspectratio"] = dict(x=1, y=1, z=1)
        if "marker" in fig["data"][0]:
            fig["data"][0]["marker"]["colorscale"] = "purples"

    return Plotly(fig=fig)
