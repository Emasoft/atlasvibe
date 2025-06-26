# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import os
from typing import Literal, Optional

import numpy as np
import pandas as pd
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataFrame, Grayscale, Image, String
from PIL import Image as PIL_Image


def get_file_path(file_path: str, default_path: str | None = None):
    """Resolve file path with proper error handling and validation.

    Args:
        file_path: The file path to resolve (absolute or relative)
        default_path: Default path to use if file_path is empty

    Returns:
        Absolute path to the file

    Raises:
        ValueError: If no valid path is provided
        FileNotFoundError: If the resolved path doesn't exist
    """
    f_path = file_path if file_path != "" else default_path
    if not f_path:
        raise ValueError("The file path of the input file is missing. Please provide an input String or provide `file_path` with a value!")

    # If already absolute, validate and return
    if os.path.isabs(f_path):
        if not os.path.exists(f_path):
            raise FileNotFoundError(f"File not found: {f_path}")
        return f_path

    # For relative paths, try multiple resolution strategies
    # 1. Relative to current working directory
    cwd_path = os.path.abspath(f_path)
    if os.path.exists(cwd_path):
        return cwd_path

    # 2. Relative to the blocks directory
    try:
        # Use pathlib for more robust path handling
        from pathlib import Path

        current_file = Path(__file__).resolve()
        blocks_dir = current_file.parent.parent.parent.parent.parent  # Navigate up to blocks/
        blocks_path = blocks_dir / f_path
        if blocks_path.exists():
            return str(blocks_path.resolve())
    except Exception:
        pass

    # 3. Relative to the current block's directory
    block_dir = os.path.dirname(os.path.abspath(__file__))
    block_path = os.path.abspath(os.path.join(block_dir, f_path))
    if os.path.exists(block_path):
        return block_path

    # If none of the strategies work, raise an error with helpful message
    raise FileNotFoundError(
        f"File not found: {f_path}\nTried paths:\n  - {cwd_path} (relative to current directory)\n  - {blocks_path if 'blocks_path' in locals() else 'N/A'} (relative to blocks directory)\n  - {block_path} (relative to current block)\nPlease provide an absolute path or ensure the file exists in one of these locations."
    )


@atlasvibe(
    deps={
        "scikit-image": "0.21.0",
    }
)
def LOCAL_FILE(
    file_path: str | None = None,
    default: Optional[String] = None,
    file_type: Literal["Image", "Grayscale", "JSON", "CSV"] = "Image",
) -> Image | DataFrame | Grayscale:
    """The LOCAL_FILE node loads a local file of a different type and converts it to a DataContainer class.

    Parameters
    ----------
    file_path : str
        The path to the file to be loaded. This can be either an absolute path or
        a path relative to the "nodes" directory.

    default : Optional[String]
        If this input node is connected, the file name will be taken from
        the output of the connected node.
        To be used in conjunction with batch processing.
    file_type : str
        Type of file to load, default = image.
        If both 'file_path' and 'default' are not specified when 'file_type="Image"',
        a default image will be loaded.
        If the file path is not specified and the default input is not connected,
        a ValueError is raised.

    Returns
    -------
    Image | DataFrame
        Image for file_type 'image'.
        Grayscale from file_type 'Grayscale'.
        DataFrame for file_type 'json', 'csv'.
    """

    default_image_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets",
        "astronaut.png",
    )

    file_path = default.s if default else file_path
    file_path = "" if file_path is None else file_path

    match file_type:
        case "Image":
            file_path = get_file_path(file_path, default_image_path)
            with PIL_Image.open(file_path) as f:
                img_array = np.array(f.convert("RGBA"))
            red_channel = img_array[:, :, 0]
            green_channel = img_array[:, :, 1]
            blue_channel = img_array[:, :, 2]
            if img_array.shape[2] == 4:
                alpha_channel = img_array[:, :, 3]
            else:
                alpha_channel = None
            return Image(
                r=red_channel,
                g=green_channel,
                b=blue_channel,
                a=alpha_channel,
            )
        case "Grayscale":
            import skimage.io

            file_path = get_file_path(file_path, default_image_path)
            return Grayscale(img=skimage.io.imread(file_path, as_gray=True))
        case "CSV":
            file_path = get_file_path(file_path)
            df = pd.read_csv(file_path)
            return DataFrame(df=df)
        case "JSON":
            file_path = get_file_path(file_path)
            df = pd.read_json(file_path)
            return DataFrame(df=df)
        # TODO: we might add support for following file types later
        # case "XML":
        #     file_path = get_file_path(file_path)
        #     df = pd.read_xml(file_path)
        #     return DataFrame(df=df)
        # case "Excel":
        #     file_path = get_file_path(file_path)
        #     df = pd.read_excel(file_path)
        #     return DataFrame(df=df)
