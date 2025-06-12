#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created constants module to eliminate hardcoded strings
# - Centralized metadata file names and keys
# - Improved maintainability and consistency
# 

"""
Constants for AtlasVibe block system.

This module defines commonly used constants throughout the block system
to improve maintainability and ensure consistency.
"""

# Metadata file names
BLOCK_DATA_FILE = "block_data.json"
APP_JSON_FILE = "app.json"
EXAMPLE_MD_FILE = "example.md"
REQUIREMENTS_FILE = "requirements.txt"
INIT_FILE = "__init__.py"

# JSON keys
DOCSTRING_KEY = "docstring"
PARAMETERS_KEY = "parameters"
RETURNS_KEY = "returns"
SHORT_DESCRIPTION_KEY = "short_description"
LONG_DESCRIPTION_KEY = "long_description"

# Block metadata keys
NAME_KEY = "name"
TYPE_KEY = "type"
INPUTS_KEY = "inputs"
OUTPUTS_KEY = "outputs"
PATH_KEY = "path"

# Docstring section names
PARAMETERS_SECTION = "Parameters"
RETURNS_SECTION = "Returns"
INPUTS_SECTION = "Inputs"

# Default values
DEFAULT_BLOCK_TYPE = "default"
BLUEPRINT_BLOCKS_DIR = "blocks"
CUSTOM_BLOCKS_DIR = "atlasvibe_blocks"

# File extensions
PYTHON_EXT = ".py"
JSON_EXT = ".json"
MARKDOWN_EXT = ".md"