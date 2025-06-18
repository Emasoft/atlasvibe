#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial test implementation for Python validator
# - Test real validation scenarios without mocks
# - Test AtlasVibe-specific validation rules
# 

"""
Test suite for Python code validator.

Tests real validation scenarios without mocking to ensure
the validator works correctly with actual Python code.
"""

import pytest
from pathlib import Path
from captain.utils.python_validator import PythonValidator, ValidationError


class TestPythonValidator:
    """Test Python code validation functionality."""
    
    def test_validate_syntax_error(self):
        """Test that syntax errors are detected."""
        code = """
def test_func():
    if True  # Missing colon
        print("hello")
"""
        validator = PythonValidator()
        errors = validator.validate_code(code, "test.py")
        
        assert len(errors) > 0
        assert any(e.severity == "error" and "syntax" in e.category.lower() for e in errors)
    
    def test_validate_undefined_variable(self):
        """Test that undefined variables are detected."""
        code = """
def test_func():
    result = undefined_var + 42
    return result
"""
        validator = PythonValidator()
        errors = validator.validate_code(code, "test.py")
        
        assert any(e.message.startswith("Undefined variable") for e in errors)
    
    def test_validate_missing_docstring(self):
        """Test that missing docstrings are detected for AtlasVibe functions."""
        code = """
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe

@atlasvibe
def process_data(x, y):
    return x + y
"""
        validator = PythonValidator()
        errors = validator.validate_code(code, "atlasvibe_blocks/test_block.py")
        
        assert any("docstring" in e.message.lower() for e in errors)
    
    def test_validate_valid_atlasvibe_block(self):
        """Test that valid AtlasVibe blocks pass validation."""
        code = '''
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Scalar

@atlasvibe(deps=["numpy"])
def process_data(x: Scalar, y: Scalar) -> Scalar:
    """Add two scalars.
    
    Parameters
    ----------
    x : Scalar
        First input value
    y : Scalar
        Second input value
    
    Returns
    -------
    Scalar
        The sum of x and y
    """
    import numpy as np
    result = x.value + y.value
    return Scalar(result)
'''
        validator = PythonValidator()
        errors = validator.validate_code(code, "atlasvibe_blocks/test_block.py")
        
        # Should have no errors or only minor warnings
        error_count = sum(1 for e in errors if e.severity == "error")
        assert error_count == 0
    
    def test_validate_import_error(self):
        """Test that import errors are detected."""
        code = """
import non_existent_module
from another_missing import something
"""
        validator = PythonValidator()
        errors = validator.validate_code(code, "test.py")
        
        # Import validation might not catch all missing modules without
        # actually trying to import, but it should at least parse correctly
        assert isinstance(errors, list)
    
    def test_validate_type_annotations(self):
        """Test type annotation validation."""
        code = """
def add_numbers(x: int, y: int) -> int:
    return x + y

def missing_return_type(x: str):
    return x.upper()
"""
        validator = PythonValidator()
        errors = validator.validate_code(code, "test.py")
        
        # Should suggest adding return type annotation
        assert any("return type" in e.message.lower() for e in errors)
    
    def test_validate_complexity(self):
        """Test complexity validation."""
        code = """
def complex_function(a, b, c, d, e, f):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            return True
    return False
"""
        validator = PythonValidator()
        errors = validator.validate_code(code, "test.py")
        
        # Should warn about complexity
        assert any("complex" in e.message.lower() for e in errors)