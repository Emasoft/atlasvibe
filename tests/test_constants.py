#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created tests for constants module
# - Ensures constants are properly defined and accessible
# - Following TDD methodology
# 

"""
Tests for the constants module.

Verifies that all required constants are properly defined and accessible.
"""

import pytest

from captain.utils.constants import (
    BLOCK_DATA_FILE,
    APP_JSON_FILE,
    EXAMPLE_MD_FILE,
    DOCSTRING_KEY,
    PARAMETERS_KEY,
    RETURNS_KEY,
    PARAMETERS_SECTION,
    RETURNS_SECTION,
    INPUTS_SECTION,
    CUSTOM_BLOCKS_DIR,
    BLUEPRINT_BLOCKS_DIR,
    PYTHON_EXT,
)


class TestConstants:
    """Test that constants are properly defined."""
    
    def test_metadata_file_constants(self):
        """Test that metadata file name constants are defined."""
        assert BLOCK_DATA_FILE == "block_data.json"
        assert APP_JSON_FILE == "app.json"
        assert EXAMPLE_MD_FILE == "example.md"
    
    def test_json_key_constants(self):
        """Test that JSON key constants are defined."""
        assert DOCSTRING_KEY == "docstring"
        assert PARAMETERS_KEY == "parameters"
        assert RETURNS_KEY == "returns"
    
    def test_docstring_section_constants(self):
        """Test that docstring section name constants are defined."""
        assert PARAMETERS_SECTION == "Parameters"
        assert RETURNS_SECTION == "Returns"
        assert INPUTS_SECTION == "Inputs"
    
    def test_directory_constants(self):
        """Test that directory name constants are defined."""
        assert CUSTOM_BLOCKS_DIR == "atlasvibe_blocks"
        assert BLUEPRINT_BLOCKS_DIR == "blocks"
    
    def test_file_extension_constants(self):
        """Test that file extension constants are defined."""
        assert PYTHON_EXT == ".py"
    
    def test_constants_are_strings(self):
        """Test that all constants are strings (where appropriate)."""
        string_constants = [
            BLOCK_DATA_FILE,
            APP_JSON_FILE,
            EXAMPLE_MD_FILE,
            DOCSTRING_KEY,
            PARAMETERS_KEY,
            RETURNS_KEY,
            PARAMETERS_SECTION,
            RETURNS_SECTION,
            INPUTS_SECTION,
            CUSTOM_BLOCKS_DIR,
            BLUEPRINT_BLOCKS_DIR,
            PYTHON_EXT,
        ]
        
        for constant in string_constants:
            assert isinstance(constant, str), f"Constant {constant} should be a string"
            assert len(constant) > 0, f"Constant {constant} should not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])