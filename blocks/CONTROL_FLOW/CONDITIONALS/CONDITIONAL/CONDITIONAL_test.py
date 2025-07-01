# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import pytest
from pkgs.atlasvibe.atlasvibe.data_container import Scalar, String
from blocks.test_utils import create_test_scalar, create_test_vector
import CONDITIONAL


def test_conditional_greater_than(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with greater than comparison."""
    # Test 5 > 3 (should be True)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(5.0), obj2=create_test_scalar(3.0), operator=">"
    )
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test 2 > 5 (should be False)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(2.0), obj2=create_test_scalar(5.0), operator=">"
    )
    assert result.c == 0  # False


def test_conditional_less_than(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with less than comparison."""
    # Test 3 < 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(3.0), obj2=create_test_scalar(5.0), operator="<"
    )
    assert isinstance(result, Scalar)
    assert result.c == 1  # True


def test_conditional_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with equality comparison."""
    # Test 5 == 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(5.0), obj2=create_test_scalar(5.0), operator="=="
    )
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test 5 == 3 (should be False)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(5.0), obj2=create_test_scalar(3.0), operator="=="
    )
    assert result.c == 0  # False


def test_conditional_not_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with not equal comparison."""
    # Test 5 != 3 (should be True)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(5.0), obj2=create_test_scalar(3.0), operator="!="
    )
    assert isinstance(result, Scalar)
    assert result.c == 1  # True


def test_conditional_greater_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with greater than or equal comparison."""
    # Test 5 >= 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(5.0), obj2=create_test_scalar(5.0), operator=">="
    )
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test 6 >= 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(6.0), obj2=create_test_scalar(5.0), operator=">="
    )
    assert result.c == 1  # True


def test_conditional_less_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with less than or equal comparison."""
    # Test 5 <= 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(
        obj1=create_test_scalar(5.0), obj2=create_test_scalar(5.0), operator="<="
    )
    assert isinstance(result, Scalar)
    assert result.c == 1  # True


def test_conditional_string_comparison(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with string comparison."""
    # Test string equality
    result = CONDITIONAL.CONDITIONAL(
        obj1=String(s="hello"), obj2=String(s="hello"), operator="=="
    )
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test string inequality
    result = CONDITIONAL.CONDITIONAL(
        obj1=String(s="hello"), obj2=String(s="world"), operator="!="
    )
    assert result.c == 1  # True


def test_conditional_edge_cases(mock_atlasvibe_decorator):
    """Test CONDITIONAL block edge cases and error conditions."""
    # Test with different data container types (Vector comparison)
    vec1 = create_test_vector(5, 0, 10)
    vec2 = create_test_vector(5, 5, 15)

    # Should compare first elements
    result = CONDITIONAL.CONDITIONAL(obj1=vec1, obj2=vec2, operator="<")
    assert isinstance(result, Scalar)
    assert result.c == 1  # 0 < 5 is True


def test_conditional_invalid_operator(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with invalid operator."""
    # Test with invalid operator should raise an error
    with pytest.raises((ValueError, KeyError, AttributeError)):
        CONDITIONAL.CONDITIONAL(
            obj1=create_test_scalar(5.0),
            obj2=create_test_scalar(3.0),
            operator="invalid",
        )


def test_conditional_same_object_reference(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with same object references."""
    obj = create_test_scalar(5.0)

    # Same object should be equal
    result = CONDITIONAL.CONDITIONAL(obj1=obj, obj2=obj, operator="==")
    assert result.c == 1  # True

    # Same object should not be not equal
    result = CONDITIONAL.CONDITIONAL(obj1=obj, obj2=obj, operator="!=")
    assert result.c == 0  # False
