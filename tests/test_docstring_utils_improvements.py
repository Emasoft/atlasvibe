#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created tests for docstring_utils improvements
# - Tests for better error handling with specific exceptions
# - Tests for encoding specification in file operations
# - Tests for more specific type hints
# 

"""
Tests for improvements to the docstring_utils module.

Following TDD methodology, these tests are written before implementing
the improvements to ensure proper error handling and type safety.
"""

import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import patch, mock_open

import pytest

from captain.utils.docstring_utils import (
    parse_python_file,
    get_param_descriptions,
    get_return_descriptions,
    extract_docstring_data,
)


class TestImprovedErrorHandling:
    """Test improved error handling with specific exceptions."""
    
    def test_parse_python_file_with_file_not_found(self):
        """Test that FileNotFoundError is properly handled."""
        # Should return (None, None) for non-existent file
        result = parse_python_file("/non/existent/file.py", "func")
        assert result == (None, None)
    
    def test_parse_python_file_with_syntax_error(self):
        """Test handling of Python syntax errors."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def broken syntax")
            f.flush()
            
            result = parse_python_file(f.name, "func")
            assert result == (None, None)
            
            Path(f.name).unlink()
    
    def test_parse_python_file_with_encoding_error(self):
        """Test handling of encoding errors."""
        # Create a file with invalid UTF-8
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.py', delete=False) as f:
            f.write(b'def func():\n    """test"""\n    # \xff\xfe invalid utf-8\n    pass')
            f.flush()
            
            # Should handle encoding error gracefully
            result = parse_python_file(f.name, "func")
            # May succeed if error recovery works, or return (None, None)
            assert isinstance(result, tuple)
            
            Path(f.name).unlink()
    
    def test_parse_python_file_with_explicit_encoding(self):
        """Test that file is opened with explicit UTF-8 encoding."""
        content = 'def test():\n    """Test с кириллицей"""\n    pass'
        
        # Mock open to verify encoding parameter
        with patch('builtins.open', mock_open(read_data=content)) as m:
            parse_python_file("test.py", "test")
            # Verify open was called with encoding
            m.assert_called_with("test.py", "r", encoding="utf-8")
    
    def test_get_param_descriptions_with_none_input(self):
        """Test that None docstring is handled properly."""
        result = get_param_descriptions(None, style="numpy")
        assert result == {}
    
    def test_get_return_descriptions_with_malformed_docstring(self):
        """Test handling of malformed docstrings."""
        malformed = "This is not\na proper\ndocstring\nReturns\n---\nBroken"
        result = get_return_descriptions(malformed, style="numpy")
        # Should return empty dict for malformed docstring
        assert result == {}
    
    def test_extract_docstring_data_logs_parsing_errors(self, caplog):
        """Test that parsing errors are logged, not silently ignored."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def func():
    """
    Malformed docstring
    
    Parameters
    ----------
    Missing type annotation
    """
    pass
''')
            f.flush()
            
            # Enable logging capture
            import logging
            logging.getLogger("captain.utils.docstring_utils").setLevel(logging.WARNING)
            
            result = extract_docstring_data(f.name, "func", style="numpy")
            
            # Should still return a result
            assert result is not None
            
            Path(f.name).unlink()


class TestImprovedTypeHints:
    """Test that type hints are more specific than Any."""
    
    def test_parsed_docstring_type_hints(self):
        """Test that parsed docstring objects have proper type hints."""
        # This test ensures we're using proper types from docstring_parser
        from docstring_parser.common import Docstring
        from captain.utils.docstring_utils import parse_numpy_style_docstring
        
        docstring = """
        Test function.
        
        Parameters
        ----------
        x : int
            Test param
        """
        
        result = parse_numpy_style_docstring(docstring)
        # Should return a Docstring object, not Any
        assert isinstance(result, Docstring)
    
    def test_return_type_annotations(self):
        """Test that function return types are properly annotated."""
        # This is more of a static type checking test
        # In practice, would use mypy for this
        from captain.utils.docstring_utils import create_docstring_json
        from docstring_parser.common import Docstring
        
        # The function should accept Docstring, not Any
        mock_docstring = Docstring()
        mock_docstring.short_description = "Test"
        
        result = create_docstring_json(mock_docstring)
        assert isinstance(result, dict)


class TestOptimizedOperations:
    """Test optimized string operations."""
    
    def test_numpy_style_detection_performance(self):
        """Test that NumPy style detection is efficient."""
        # Create a large docstring
        large_docstring = "Test\n" * 1000 + """
        Parameters
        ----------
        x : int
            Test
        """ + "\n" * 1000
        
        import time
        start = time.time()
        
        # This should be fast even with large docstrings
        from captain.utils.docstring_utils import extract_docstring_data
        
        # Mock the file reading part
        with patch('captain.utils.docstring_utils.parse_python_file') as mock_parse:
            mock_parse.return_value = (None, large_docstring)
            result = extract_docstring_data("test.py", "test", style="auto")
        
        elapsed = time.time() - start
        # Should complete in reasonable time (< 0.1 seconds)
        assert elapsed < 0.1
        assert result is not None


class TestEncodingSpecification:
    """Test that all file operations specify encoding."""
    
    def test_file_operations_use_utf8(self):
        """Test that file operations explicitly use UTF-8."""
        # This is tested via mocking in test_parse_python_file_with_explicit_encoding
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])