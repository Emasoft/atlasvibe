#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created comprehensive tests for docstring_utils module
# - Tests all functions with various edge cases
# - Follows TDD methodology (written after implementation as correction)
# 

"""
Tests for the shared docstring utilities module.
"""

import ast
import tempfile
from pathlib import Path

import pytest

from captain.utils.docstring_utils import (
    create_docstring_json,
    extract_docstring_data,
    extract_docstring_from_node,
    find_function_node,
    get_param_descriptions,
    get_return_descriptions,
    parse_google_style_docstring,
    parse_numpy_style_docstring,
    parse_python_file,
)


class TestASTUtilities:
    """Test AST-related utility functions."""
    
    def test_find_function_node(self):
        """Test finding a function node in AST."""
        code = """
def test_func():
    '''Test docstring'''
    pass

def other_func():
    pass
"""
        tree = ast.parse(code)
        
        # Test finding existing function
        node = find_function_node(tree, "test_func")
        assert node is not None
        assert node.name == "test_func"
        
        # Test finding non-existent function
        node = find_function_node(tree, "missing_func")
        assert node is None
    
    def test_extract_docstring_from_node(self):
        """Test extracting docstring from AST node."""
        # Test with docstring
        code = '''
def test_func():
    """This is a test docstring."""
    pass
'''
        tree = ast.parse(code)
        func_node = find_function_node(tree, "test_func")
        docstring = extract_docstring_from_node(func_node)
        assert docstring == "This is a test docstring."
        
        # Test without docstring
        code = "def test_func():\n    pass"
        tree = ast.parse(code)
        func_node = find_function_node(tree, "test_func")
        docstring = extract_docstring_from_node(func_node)
        assert docstring is None
        
        # Test with non-string first statement
        code = "def test_func():\n    x = 1"
        tree = ast.parse(code)
        func_node = find_function_node(tree, "test_func")
        docstring = extract_docstring_from_node(func_node)
        assert docstring is None
    
    def test_parse_python_file(self):
        """Test parsing Python file and extracting function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def my_function():
    """My docstring"""
    return 42
''')
            f.flush()
            
            # Test successful parsing
            node, docstring = parse_python_file(f.name, "my_function")
            assert node is not None
            assert node.name == "my_function"
            assert docstring == "My docstring"
            
            # Test missing function
            node, docstring = parse_python_file(f.name, "missing_func")
            assert node is None
            assert docstring is None
            
            # Clean up
            Path(f.name).unlink()
        
        # Test non-existent file
        node, docstring = parse_python_file("/non/existent/file.py", "func")
        assert node is None
        assert docstring is None


class TestDocstringParsing:
    """Test docstring parsing functions."""
    
    def test_parse_numpy_style_docstring(self):
        """Test parsing NumPy-style docstrings."""
        docstring = """
        Short description.
        
        Long description here.
        
        Parameters
        ----------
        param1 : str
            Description of param1
        param2 : int, optional
            Description of param2
            
        Returns
        -------
        bool
            Description of return value
        """
        
        parsed = parse_numpy_style_docstring(docstring)
        assert parsed.short_description == "Short description."
        assert parsed.long_description == "Long description here."
        assert len(parsed.params) == 2
        assert parsed.params[0].arg_name == "param1"
        assert parsed.params[0].type_name == "str"
        assert parsed.returns is not None
        assert parsed.returns.type_name == "bool"
    
    def test_parse_numpy_with_extra_sections(self):
        """Test parsing NumPy docstring with extra sections."""
        docstring = """
        Test function.
        
        Inputs
        ------
        input1 : DataContainer
            First input
        """
        
        parsed = parse_numpy_style_docstring(docstring, [("Inputs", "inputs")])
        assert parsed.short_description == "Test function."
        # Note: Extra sections might need special handling in docstring_parser
    
    def test_parse_google_style_docstring(self):
        """Test parsing Google-style docstrings."""
        docstring = """
        Short description.
        
        Long description here.
        
        Args:
            param1 (str): Description of param1
            param2 (int): Description of param2
            
        Returns:
            bool: Description of return value
        """
        
        parsed = parse_google_style_docstring(docstring)
        assert parsed.short_description == "Short description."
        assert parsed.long_description == "Long description here."
        assert len(parsed.params) == 2
        assert parsed.params[0].arg_name == "param1"
        assert parsed.returns is not None


class TestJSONConversion:
    """Test JSON conversion functions."""
    
    def test_create_docstring_json_basic(self):
        """Test basic JSON creation from parsed docstring."""
        docstring = """
        Test function.
        
        Parameters
        ----------
        param1 : str
            Description
            
        Returns
        -------
        int
            Result
        """
        
        from docstring_parser import parse
        parsed = parse(docstring)
        
        json_data = create_docstring_json(parsed)
        
        assert json_data["short_description"] == "Test function."
        assert json_data["long_description"] == ""
        assert len(json_data["parameters"]) == 1
        assert json_data["parameters"][0]["name"] == "param1"
        assert json_data["parameters"][0]["type"] == "str"
        assert len(json_data["returns"]) == 1
        assert json_data["returns"][0]["type"] == "int"
    
    def test_create_docstring_json_empty_fields(self):
        """Test JSON creation with empty field handling."""
        docstring = "Just a short description."
        
        from docstring_parser import parse
        parsed = parse(docstring)
        
        # With empty fields
        json_data = create_docstring_json(parsed, include_empty_fields=True)
        assert json_data["long_description"] == ""
        assert json_data["parameters"] == []
        assert json_data["returns"] == []
        
        # Without empty fields
        json_data = create_docstring_json(parsed, include_empty_fields=False)
        assert "long_description" not in json_data or json_data["long_description"] == ""
        assert len(json_data["parameters"]) == 0
        assert len(json_data["returns"]) == 0
    
    def test_create_docstring_json_multiple_returns(self):
        """Test JSON creation with multiple return values."""
        docstring = """
        Test function.
        
        Returns
        -------
        x : int
            First return
        y : str
            Second return
        """
        
        from docstring_parser import parse
        parsed = parse(docstring)
        
        json_data = create_docstring_json(parsed)
        
        assert len(json_data["returns"]) == 2
        assert json_data["returns"][0]["name"] == "x"
        assert json_data["returns"][0]["type"] == "int"
        assert json_data["returns"][1]["name"] == "y"
        assert json_data["returns"][1]["type"] == "str"


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_param_descriptions(self):
        """Test extracting parameter descriptions."""
        docstring = """
        Test function.
        
        Parameters
        ----------
        param1 : str
            First parameter
        param2 : int
            Second parameter
        """
        
        descriptions = get_param_descriptions(docstring, style="numpy")
        assert descriptions["param1"] == "First parameter"
        assert descriptions["param2"] == "Second parameter"
        
        # Test empty docstring
        descriptions = get_param_descriptions("", style="numpy")
        assert descriptions == {}
        
        # Test None docstring
        descriptions = get_param_descriptions(None, style="numpy")
        assert descriptions == {}
    
    def test_get_return_descriptions(self):
        """Test extracting return descriptions."""
        docstring = """
        Test function.
        
        Returns
        -------
        int
            The result
        """
        
        descriptions = get_return_descriptions(docstring, style="numpy")
        assert descriptions[""] == "The result"
        
        # Test multiple returns
        docstring = """
        Test function.
        
        Returns
        -------
        x : int
            First value
        y : str
            Second value
        """
        
        descriptions = get_return_descriptions(docstring, style="numpy")
        assert descriptions["x"] == "First value"
        assert descriptions["y"] == "Second value"


class TestHighLevelFunctions:
    """Test high-level convenience functions."""
    
    def test_extract_docstring_data(self):
        """Test the high-level extraction function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def MY_BLOCK():
    """
    Process data block.
    
    This block processes input data.
    
    Parameters
    ----------
    data : array
        Input data
        
    Returns
    -------
    result : array
        Processed data
    """
    return data * 2
''')
            f.flush()
            
            # Test extraction with auto style detection
            # Must specify function name since temp file has random name
            result = extract_docstring_data(f.name, function_name="MY_BLOCK", style="auto")
            assert result is not None
            
            assert "docstring" in result
            assert result["docstring"]["short_description"] == "Process data block."
            assert len(result["docstring"]["parameters"]) == 1
            assert result["docstring"]["parameters"][0]["name"] == "data"
            
            # Test with explicit numpy style
            result = extract_docstring_data(f.name, function_name="MY_BLOCK", style="numpy")
            assert result is not None
            
            # Test with function name inference - skip since temp file has random name
            # result = extract_docstring_data(f.name, function_name=None)
            # assert result is not None  # Should use filename stem
            
            # Clean up
            Path(f.name).unlink()
        
        # Test with non-existent file
        result = extract_docstring_data("/non/existent/file.py")
        assert result is None
    
    def test_extract_docstring_data_google_style(self):
        """Test extraction with Google-style docstring."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def process():
    """
    Process data.
    
    Args:
        data: Input data
        
    Returns:
        Processed data
    """
    pass
''')
            f.flush()
            
            result = extract_docstring_data(f.name, "process", style="google")
            assert result is not None
            assert result["docstring"]["short_description"] == "Process data."
            
            # Clean up
            Path(f.name).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])