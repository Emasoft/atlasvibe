# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

"""
Common test utilities for AtlasVibe block testing.

This module provides shared utilities for creating test data, mocking decorators,
and other common testing patterns used across block tests.
"""

import numpy as np
import pandas as pd
from typing import Any, Optional
from functools import wraps

try:
    import pytest

    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from pkgs.atlasvibe.atlasvibe.data_container import (
    DataContainer,
    OrderedPair,
    Vector,
    Scalar,
    Matrix,
    DataFrame,
    Grayscale,
    Image,
    Surface,
    OrderedTriple,
)


def create_mock_decorator(func: Any) -> Any:
    """Create a mock decorator that passes through the function unchanged.

    This is used to mock the @atlasvibe decorator during testing to avoid
    virtual environment creation and dependency installation.

    Args:
        func: The function to wrap

    Returns:
        The original function unchanged
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def create_test_scalar(value: float = 1.0) -> Scalar:
    """Create a test Scalar DataContainer.

    Args:
        value: The scalar value (default: 1.0)

    Returns:
        A Scalar DataContainer
    """
    return Scalar(c=value)


def create_test_vector(size: int = 10, start: float = 0.0, stop: float = 10.0) -> Vector:
    """Create a test Vector DataContainer.

    Args:
        size: Number of elements in the vector
        start: Start value for linspace
        stop: Stop value for linspace

    Returns:
        A Vector DataContainer
    """
    return Vector(v=np.linspace(start, stop, size))


def create_test_ordered_pair(size: int = 10, x_start: float = 0.0, x_stop: float = 10.0, y_start: float = 0.0, y_stop: float = 10.0) -> OrderedPair:
    """Create a test OrderedPair DataContainer.

    Args:
        size: Number of points
        x_start, x_stop: Range for x values
        y_start, y_stop: Range for y values

    Returns:
        An OrderedPair DataContainer
    """
    return OrderedPair(x=np.linspace(x_start, x_stop, size), y=np.linspace(y_start, y_stop, size))


def create_test_matrix(rows: int = 10, cols: int = 10, value: float = 1.0) -> Matrix:
    """Create a test Matrix DataContainer.

    Args:
        rows: Number of rows
        cols: Number of columns
        value: Value to fill the matrix with

    Returns:
        A Matrix DataContainer
    """
    return Matrix(m=np.full((rows, cols), value))


def create_test_dataframe(rows: int = 10, cols: int = 3, seed: Optional[int] = None) -> DataFrame:
    """Create a test DataFrame DataContainer.

    Args:
        rows: Number of rows
        cols: Number of columns
        seed: Random seed for reproducible data (optional)

    Returns:
        A DataFrame DataContainer with sample data
    """
    if seed is not None:
        np.random.seed(seed)
    data = {f"col_{i}": np.random.randn(rows) for i in range(cols)}
    df = pd.DataFrame(data)
    return DataFrame(df=df)


def create_test_grayscale(width: int = 100, height: int = 100) -> Grayscale:
    """Create a test Grayscale image DataContainer.

    Args:
        width: Image width
        height: Image height

    Returns:
        A Grayscale DataContainer with random values
    """
    return Grayscale(img=np.random.rand(height, width))


def create_test_image(width: int = 100, height: int = 100, has_alpha: bool = False) -> Image:
    """Create a test Image DataContainer.

    Args:
        width: Image width
        height: Image height
        has_alpha: Whether to include alpha channel

    Returns:
        An Image DataContainer with random RGB(A) values
    """
    r = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    g = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    b = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    a = np.random.randint(0, 256, (height, width), dtype=np.uint8) if has_alpha else None

    return Image(r=r, g=g, b=b, a=a)


def create_test_surface(x_size: int = 10, y_size: int = 10) -> Surface:
    """Create a test Surface DataContainer.

    Args:
        x_size: Number of x points
        y_size: Number of y points

    Returns:
        A Surface DataContainer
    """
    x = np.linspace(0, 10, x_size)
    y = np.linspace(0, 10, y_size)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(X) * np.cos(Y)

    return Surface(x=X, y=Y, z=Z)


def create_test_ordered_triple(size: int = 10) -> OrderedTriple:
    """Create a test OrderedTriple DataContainer.

    Args:
        size: Number of points

    Returns:
        An OrderedTriple DataContainer
    """
    return OrderedTriple(x=np.linspace(0, 10, size), y=np.linspace(0, 10, size), z=np.linspace(0, 10, size))


def assert_datacontainer_equal(dc1: DataContainer, dc2: DataContainer, rtol: float = 1e-5):
    """Assert that two DataContainers are equal.

    Args:
        dc1, dc2: DataContainers to compare
        rtol: Relative tolerance for numerical comparison

    Raises:
        AssertionError: If the DataContainers are not equal
    """
    assert dc1.type == dc2.type, f"Types differ: {dc1.type} != {dc2.type}"

    if isinstance(dc1, Scalar):
        np.testing.assert_allclose(dc1.c, dc2.c, rtol=rtol)
    elif isinstance(dc1, Vector):
        np.testing.assert_allclose(dc1.v, dc2.v, rtol=rtol)
    elif isinstance(dc1, OrderedPair):
        np.testing.assert_allclose(dc1.x, dc2.x, rtol=rtol)
        np.testing.assert_allclose(dc1.y, dc2.y, rtol=rtol)
    elif isinstance(dc1, Matrix):
        np.testing.assert_allclose(dc1.m, dc2.m, rtol=rtol)
    elif isinstance(dc1, DataFrame):
        pd.testing.assert_frame_equal(dc1.df, dc2.df)
    elif isinstance(dc1, Grayscale):
        np.testing.assert_allclose(dc1.img, dc2.img, rtol=rtol)
    elif isinstance(dc1, Image):
        np.testing.assert_array_equal(dc1.r, dc2.r)
        np.testing.assert_array_equal(dc1.g, dc2.g)
        np.testing.assert_array_equal(dc1.b, dc2.b)
        if dc1.a is not None:
            np.testing.assert_array_equal(dc1.a, dc2.a)
    elif isinstance(dc1, Surface):
        np.testing.assert_allclose(dc1.x, dc2.x, rtol=rtol)
        np.testing.assert_allclose(dc1.y, dc2.y, rtol=rtol)
        np.testing.assert_allclose(dc1.z, dc2.z, rtol=rtol)
    elif isinstance(dc1, OrderedTriple):
        np.testing.assert_allclose(dc1.x, dc2.x, rtol=rtol)
        np.testing.assert_allclose(dc1.y, dc2.y, rtol=rtol)
        np.testing.assert_allclose(dc1.z, dc2.z, rtol=rtol)
    else:
        raise ValueError(f"Unknown DataContainer type: {dc1.type}")


def parametrize_datacontainer_types():
    """Decorator to parametrize tests with different DataContainer types.

    Usage:
        @parametrize_datacontainer_types()
        def test_something(datacontainer_factory):
            dc = datacontainer_factory()
            # ... test with dc
    """
    if not HAS_PYTEST:
        raise ImportError("pytest is required to use parametrize_datacontainer_types")

    factories = [
        ("scalar", create_test_scalar),
        ("vector", create_test_vector),
        ("ordered_pair", create_test_ordered_pair),
        ("matrix", create_test_matrix),
        ("dataframe", create_test_dataframe),
        ("grayscale", create_test_grayscale),
        ("image", create_test_image),
        ("surface", create_test_surface),
        ("ordered_triple", create_test_ordered_triple),
    ]

    return pytest.mark.parametrize("datacontainer_factory", [f[1] for f in factories], ids=[f[0] for f in factories])
