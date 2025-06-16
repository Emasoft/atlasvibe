#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test arithmetic utilities for edge cases and proper error handling."""

import pytest
import numpy as np
from blocks.MATH.ARITHMETIC.utils.arithmetic_utils import get_val, perform_arithmetic_operation
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Scalar, Vector


def test_get_val_handles_all_types():
    """Test get_val extracts correct values from all container types."""
    # Test OrderedPair
    op = OrderedPair(x=np.array([1, 2, 3]), y=np.array([4, 5, 6]))
    assert np.array_equal(get_val(op), np.array([4, 5, 6]))
    
    # Test Scalar
    s = Scalar(c=42.0)
    assert get_val(s) == 42.0
    
    # Test Vector
    v = Vector(v=np.array([7, 8, 9]))
    assert np.array_equal(get_val(v), np.array([7, 8, 9]))


def test_perform_arithmetic_operation_empty_list():
    """Test arithmetic operation with empty additional operands list."""
    a = Scalar(c=10.0)
    b = []
    
    # Should return the original value when b is empty
    result = perform_arithmetic_operation(a, b, np.add)
    assert isinstance(result, Scalar)
    assert result.c == 10.0


def test_perform_arithmetic_operation_type_preservation():
    """Test that operations preserve the type of the first operand."""
    # OrderedPair input should return OrderedPair
    op1 = OrderedPair(x=np.array([1, 2]), y=np.array([3, 4]))
    op2 = OrderedPair(x=np.array([5, 6]), y=np.array([7, 8]))
    result = perform_arithmetic_operation(op1, [op2], np.add)
    assert isinstance(result, OrderedPair)
    assert np.array_equal(result.x, op1.x)  # x should be preserved from first operand
    assert np.array_equal(result.y, np.array([10, 12]))
    
    # Vector input should return Vector
    v1 = Vector(v=np.array([1, 2, 3]))
    v2 = Vector(v=np.array([4, 5, 6]))
    result = perform_arithmetic_operation(v1, [v2], np.add)
    assert isinstance(result, Vector)
    assert np.array_equal(result.v, np.array([5, 7, 9]))
    
    # Scalar input should return Scalar
    s1 = Scalar(c=5.0)
    s2 = Scalar(c=3.0)
    result = perform_arithmetic_operation(s1, [s2], np.add)
    assert isinstance(result, Scalar)
    assert result.c == 8.0


def test_perform_arithmetic_operation_multiple_operands():
    """Test arithmetic operation with multiple operands."""
    a = Vector(v=np.array([1, 2, 3]))
    b = [
        Vector(v=np.array([4, 5, 6])),
        Vector(v=np.array([7, 8, 9])),
        Vector(v=np.array([10, 11, 12]))
    ]
    
    # (1,2,3) + (4,5,6) + (7,8,9) + (10,11,12) = (22,26,30)
    result = perform_arithmetic_operation(a, b, np.add)
    assert isinstance(result, Vector)
    assert np.array_equal(result.v, np.array([22, 26, 30]))


def test_perform_arithmetic_operation_different_operations():
    """Test different arithmetic operations."""
    a = Scalar(c=100.0)
    b = [Scalar(c=25.0), Scalar(c=5.0)]
    
    # Subtraction: 100 - 25 - 5 = 70
    result = perform_arithmetic_operation(a, b, np.subtract)
    assert result.c == 70.0
    
    # Multiplication: 100 * 25 * 5 = 12500
    result = perform_arithmetic_operation(a, b, np.multiply)
    assert result.c == 12500.0
    
    # Division: 100 / 25 / 5 = 0.8
    result = perform_arithmetic_operation(a, b, np.divide)
    assert result.c == 0.8


def test_perform_arithmetic_operation_mixed_types():
    """Test arithmetic operation with mixed container types in operands."""
    # This tests robustness - the function extracts values regardless of container type
    a = Vector(v=np.array([10, 20, 30]))
    b = [
        Scalar(c=5),  # Will broadcast
        Vector(v=np.array([1, 2, 3]))
    ]
    
    # (10,20,30) + 5 + (1,2,3) = (16,27,38)
    result = perform_arithmetic_operation(a, b, np.add)
    assert isinstance(result, Vector)  # Type determined by 'a'
    assert np.array_equal(result.v, np.array([16, 27, 38]))


def test_perform_arithmetic_operation_broadcasting():
    """Test numpy broadcasting rules are preserved."""
    # Vector + Scalar (broadcasting)
    a = Vector(v=np.array([1, 2, 3, 4]))
    b = [Scalar(c=10)]
    
    result = perform_arithmetic_operation(a, b, np.add)
    assert np.array_equal(result.v, np.array([11, 12, 13, 14]))
    
    # OrderedPair with different shaped arrays
    op1 = OrderedPair(x=np.array([1, 2]), y=np.array([[1, 2], [3, 4]]))
    op2 = OrderedPair(x=np.array([3, 4]), y=np.array([10, 20]))
    
    # Should broadcast [10, 20] to [[10, 20], [10, 20]] and add
    result = perform_arithmetic_operation(op1, [op2], np.add)
    expected = np.array([[11, 22], [13, 24]])
    assert np.array_equal(result.y, expected)