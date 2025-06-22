import numpy as np
import pytest

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from pkgs.atlasvibe.atlasvibe.data_container import Image


@pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not installed")
def test_IMAGE_SMOOTHING(mock_atlasvibe_decorator):
    import IMAGE_SMOOTHING

    x = np.eye(3)

    rgba_image = np.stack((x, x, x, x), axis=2)
    image = cv2.blur(rgba_image, (5, 5))

    element = Image(r=x, g=x, b=x, a=x)
    res = IMAGE_SMOOTHING.IMAGE_SMOOTHING(element)

    assert np.array_equal(res.r, image[:, :, 0])
    assert np.array_equal(res.g, image[:, :, 1])
    assert np.array_equal(res.b, image[:, :, 2])
    assert np.array_equal(res.a, image[:, :, 3])
