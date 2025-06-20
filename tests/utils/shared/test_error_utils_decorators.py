#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for error utils decorators type annotations."""

import pytest
from captain.utils.shared.error_utils import with_error_handling, with_retry


def test_decorator_type_preservation():
    """Test that decorators preserve function type."""

    @with_error_handling(default=42)
    def my_function(x: int, y: int) -> int:
        """Add two numbers."""
        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError("Arguments must be integers")
        return x + y

    # The decorated function should still have the same signature
    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "Add two numbers."

    # Should work normally
    assert my_function(2, 3) == 5

    # Should return default on error
    assert my_function("not", "numbers") == 42


def test_retry_decorator_type_preservation():
    """Test that retry decorator preserves function type."""

    @with_retry(max_attempts=3, delay=0.1)
    def flaky_function(x: int) -> int:
        """A function that might fail."""
        if x < 0:
            raise ValueError("Negative value")
        return x * 2

    # The decorated function should still have the same signature
    assert flaky_function.__name__ == "flaky_function"
    assert flaky_function.__doc__ == "A function that might fail."

    # Should work normally
    assert flaky_function(5) == 10

    # Should raise after retries
    with pytest.raises(ValueError):
        flaky_function(-1)
