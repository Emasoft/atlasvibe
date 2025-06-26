#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE FILE:
# - Created unit tests for LOGARITHMIC_ADJUSTMENT block
#

"""Unit tests for LOGARITHMIC_ADJUSTMENT block."""

import numpy as np
import pytest
from pkgs.atlasvibe.atlasvibe.data_container import Image


def test_logarithmic_adjustment_basic():
    """Test basic logarithmic adjustment with default parameters."""
    # Create a test image
    test_shape = (100, 100)
    r = np.ones(test_shape, dtype=np.uint8) * 100
    g = np.ones(test_shape, dtype=np.uint8) * 150
    b = np.ones(test_shape, dtype=np.uint8) * 200

    input_image = Image(r=r, g=g, b=b, a=None)

    # Import and run the function
    from blocks.COMPUTER_VISION.LOGARITHMIC_ADJUSTMENT.LOGARITHMIC_ADJUSTMENT import LOGARITHMIC_ADJUSTMENT

    result = LOGARITHMIC_ADJUSTMENT(input_image)

    # Check result type
    assert isinstance(result, Image)
    assert result.r.shape == test_shape
    assert result.g.shape == test_shape
    assert result.b.shape == test_shape

    # Check that values have changed (logarithmic adjustment should modify them)
    assert not np.array_equal(result.r, r)
    assert not np.array_equal(result.g, g)
    assert not np.array_equal(result.b, b)


def test_logarithmic_adjustment_with_gain():
    """Test logarithmic adjustment with custom gain parameter."""
    # Create a test image
    test_shape = (50, 50)
    r = np.ones(test_shape, dtype=np.uint8) * 128
    g = np.ones(test_shape, dtype=np.uint8) * 128
    b = np.ones(test_shape, dtype=np.uint8) * 128

    input_image = Image(r=r, g=g, b=b, a=None)

    from .LOGARITHMIC_ADJUSTMENT import LOGARITHMIC_ADJUSTMENT

    # Test with different gain values
    result_low_gain = LOGARITHMIC_ADJUSTMENT(input_image, gain=0.5)
    result_high_gain = LOGARITHMIC_ADJUSTMENT(input_image, gain=2.0)

    # Results should be different with different gains
    assert not np.array_equal(result_low_gain.r, result_high_gain.r)


def test_logarithmic_adjustment_inverse():
    """Test inverse logarithmic adjustment."""
    # Create a test image
    test_shape = (30, 30)
    r = np.ones(test_shape, dtype=np.uint8) * 100
    g = np.ones(test_shape, dtype=np.uint8) * 100
    b = np.ones(test_shape, dtype=np.uint8) * 100

    input_image = Image(r=r, g=g, b=b, a=None)

    from .LOGARITHMIC_ADJUSTMENT import LOGARITHMIC_ADJUSTMENT

    # Test normal vs inverse
    result_normal = LOGARITHMIC_ADJUSTMENT(input_image, inv=False)
    result_inverse = LOGARITHMIC_ADJUSTMENT(input_image, inv=True)

    # Results should be different
    assert not np.array_equal(result_normal.r, result_inverse.r)


def test_logarithmic_adjustment_with_alpha():
    """Test logarithmic adjustment with alpha channel."""
    # Create a test image with alpha
    test_shape = (40, 40)
    r = np.ones(test_shape, dtype=np.uint8) * 80
    g = np.ones(test_shape, dtype=np.uint8) * 120
    b = np.ones(test_shape, dtype=np.uint8) * 160
    a = np.ones(test_shape, dtype=np.uint8) * 255

    input_image = Image(r=r, g=g, b=b, a=a)

    from .LOGARITHMIC_ADJUSTMENT import LOGARITHMIC_ADJUSTMENT

    result = LOGARITHMIC_ADJUSTMENT(input_image)

    # Check that alpha channel is preserved
    assert result.a is not None
    assert result.a.shape == test_shape


def test_logarithmic_adjustment_invalid_dtype():
    """Test that function raises error for invalid image dtype."""
    # Create a test image with wrong dtype
    test_shape = (20, 20)
    r = np.ones(test_shape, dtype=np.float64) * 0.5  # Wrong dtype
    g = np.ones(test_shape, dtype=np.float64) * 0.5
    b = np.ones(test_shape, dtype=np.float64) * 0.5

    input_image = Image(r=r, g=g, b=b, a=None)

    from .LOGARITHMIC_ADJUSTMENT import LOGARITHMIC_ADJUSTMENT

    # Should raise ValueError
    with pytest.raises(ValueError, match="Image must be in uint8 format"):
        LOGARITHMIC_ADJUSTMENT(input_image)


def test_logarithmic_adjustment_edge_values():
    """Test logarithmic adjustment with edge values (0 and 255)."""
    # Create a test image with edge values
    test_shape = (10, 10)
    r = np.zeros(test_shape, dtype=np.uint8)  # All zeros
    g = np.ones(test_shape, dtype=np.uint8) * 255  # All max values
    b = np.ones(test_shape, dtype=np.uint8) * 128  # Middle values

    input_image = Image(r=r, g=g, b=b, a=None)

    from .LOGARITHMIC_ADJUSTMENT import LOGARITHMIC_ADJUSTMENT

    # Should not raise any errors
    result = LOGARITHMIC_ADJUSTMENT(input_image)

    assert isinstance(result, Image)
    assert result.r.dtype == np.uint8
    assert result.g.dtype == np.uint8
    assert result.b.dtype == np.uint8
