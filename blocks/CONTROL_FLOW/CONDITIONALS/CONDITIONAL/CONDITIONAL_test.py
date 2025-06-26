# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.data_container import Scalar, String
from blocks.test_utils import create_test_scalar


def test_conditional_greater_than(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with greater than comparison."""
    import CONDITIONAL

    # Test 5 > 3 (should be True)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(5.0), obj2=create_test_scalar(3.0), operator=">")
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test 2 > 5 (should be False)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(2.0), obj2=create_test_scalar(5.0), operator=">")
    assert result.c == 0  # False


def test_conditional_less_than(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with less than comparison."""
    import CONDITIONAL

    # Test 3 < 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(3.0), obj2=create_test_scalar(5.0), operator="<")
    assert isinstance(result, Scalar)
    assert result.c == 1  # True


def test_conditional_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with equality comparison."""
    import CONDITIONAL

    # Test 5 == 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(5.0), obj2=create_test_scalar(5.0), operator="==")
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test 5 == 3 (should be False)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(5.0), obj2=create_test_scalar(3.0), operator="==")
    assert result.c == 0  # False


def test_conditional_not_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with not equal comparison."""
    import CONDITIONAL

    # Test 5 != 3 (should be True)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(5.0), obj2=create_test_scalar(3.0), operator="!=")
    assert isinstance(result, Scalar)
    assert result.c == 1  # True


def test_conditional_greater_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with greater than or equal comparison."""
    import CONDITIONAL

    # Test 5 >= 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(5.0), obj2=create_test_scalar(5.0), operator=">=")
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test 6 >= 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(6.0), obj2=create_test_scalar(5.0), operator=">=")
    assert result.c == 1  # True


def test_conditional_less_equal(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with less than or equal comparison."""
    import CONDITIONAL

    # Test 5 <= 5 (should be True)
    result = CONDITIONAL.CONDITIONAL(obj1=create_test_scalar(5.0), obj2=create_test_scalar(5.0), operator="<=")
    assert isinstance(result, Scalar)
    assert result.c == 1  # True


def test_conditional_string_comparison(mock_atlasvibe_decorator):
    """Test CONDITIONAL block with string comparison."""
    import CONDITIONAL

    # Test string equality
    result = CONDITIONAL.CONDITIONAL(obj1=String(s="hello"), obj2=String(s="hello"), operator="==")
    assert isinstance(result, Scalar)
    assert result.c == 1  # True

    # Test string inequality
    result = CONDITIONAL.CONDITIONAL(obj1=String(s="hello"), obj2=String(s="world"), operator="!=")
    assert result.c == 1  # True
