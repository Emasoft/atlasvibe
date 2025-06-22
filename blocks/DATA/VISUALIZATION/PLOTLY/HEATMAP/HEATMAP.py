# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.data_container import (
    Plotly,
    OrderedPair,
    Matrix,
    Grayscale,
    DataFrame,
    Vector,
    OrderedTriple,
    Surface,
)
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
import plotly.graph_objects as go

import numpy as np
from blocks.DATA.VISUALIZATION.template import plot_layout


@atlasvibe
def HEATMAP(
    default: OrderedPair
    | Matrix
    | Grayscale
    | DataFrame
    | Vector
    | OrderedTriple
    | Surface,
    x_label: str = "x",
    y_label: str = "y",
    z_label: str = "z",
    title: str = "",
    show_scale: bool = True,
    reverse_y: bool = False,
    reverse_x: bool = False,
    color_scale: str = "Viridis",
) -> Plotly:
    """
    Make a heatmap from a matrix, dataframe, ordered triple, or 2D arrays.

    Data can be a Matrix, DataFrame, OrderedTriple, or OrderedPair.
    X, Y, and Z must all be the same size when OrderedTriple is used
    as the default input.

    For DataFrames a heatmap will be created for columns that
    contain continuous data (integers or floats).

    Parameters
    ----------
    default : OrderedPair | Matrix | Grayscale | DataFrame | Vector | OrderedTriple | Surface
        The input to plot
    x_label : str
        x axis label
    y_label : str
        y axis label
    z_label : str
        z axis label
    title : str
        Title of the plot
    show_scale : bool
        Whether to show the scale or not
    reverse_y : bool
        If true, reverse the y axis
    reverse_x : bool
        If true, reverse the x axis
    color_scale : str
        Sets the colorscale. The colorscale must be an array containing arrays mapping a normalized value to an rgb, rgba, hex, hsl, hsv, or named color string.

    Returns
    -------
    Plotly
        The generated Plotly heatmap
    """

    layout = plot_layout(title=title)
    layout.showlegend = False
    layout.xaxis.title = x_label
    layout.yaxis.title = y_label

    if isinstance(default, (Matrix, DataFrame)):
        if isinstance(default, DataFrame):
            z = default.m.select_dtypes(include=[np.number])
        else:
            z = default.m
        x = None
        y = None
    elif isinstance(default, OrderedPair):
        x = default.x
        y = default.y
        z = default.y
    elif isinstance(default, OrderedTriple):
        x = default.x
        y = default.y
        z = default.z
    elif isinstance(default, Grayscale):
        x = None
        y = None
        z = default.m
    elif isinstance(default, Surface):
        x = default.x
        y = default.y
        z = default.z
    elif isinstance(default, Vector):
        x = None
        y = None
        z = default.v.reshape(1, -1)  # Convert 1D vector to 2D array for heatmap
    else:
        raise ValueError(f"Invalid type: {type(default)}")

    if reverse_y:
        layout["yaxis"]["autorange"] = "reversed"
    if reverse_x:
        layout["xaxis"]["autorange"] = "reversed"

    colorbar = dict(title=z_label, titleside="right") if show_scale else None

    heatmap = go.Heatmap(
        x=x, y=y, z=z, colorscale=color_scale, colorbar=colorbar, showscale=show_scale
    )

    fig = go.Figure(data=[heatmap], layout=layout)

    return Plotly(fig=fig)
