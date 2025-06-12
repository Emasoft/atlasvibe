import cv2
import numpy as np
from atlasvibe import Image, atlasvibe
from PIL import Image as PILImage
from PIL import ImageFilter


@atlasvibe(deps={"opencv-python-headless": "4.8.1.78"})
def EDGE_DETECTION(default: Image) -> Image:
    """Detect edges in the image that was passed to it.

    This is done through the Pillow image filter, FIND_EDGES.

    Note that the image is converted to greyscale during this processing.

    Parameters
    ----------
    default : Image
        The input image to apply edge detection to.

    Returns
    -------
    Image
        The image with detected edges in white.
    """

    r = default.r
    g = default.g
    b = default.b
    a = default.a

    if a is not None:
        rgba_image = np.stack((r, g, b, a), axis=2)

    else:
        rgba_image = np.stack((r, g, b), axis=2)

    image = PILImage.fromarray(rgba_image)
    image = image.convert("L").filter(ImageFilter.FIND_EDGES).convert("RGB")
    image = np.array(image)

    # Edge detection converts to RGB (3 channels), so no alpha channel
    r, g, b = cv2.split(image)
    
    return Image(
        r=r,
        g=g,
        b=b,
        a=None,  # Edge detection removes alpha channel
    )
