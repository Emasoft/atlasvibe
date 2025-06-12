#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created shared utility module for docstring parsing
# - Extracted common logic from build_manifest.py, block_metadata_generator.py, and generate_docstring_json.py
# - Provides unified functions for AST parsing, docstring extraction, and JSON generation
# - Improved error handling with specific exceptions and logging
# - Added explicit UTF-8 encoding for file operations
# - Improved type hints with specific types instead of Any
# 

"""
Shared utilities for parsing and extracting docstring information.

This module provides common functionality for parsing Python files, extracting
docstrings, and converting them to structured data formats. It's used by various
parts of the system including manifest generation, metadata generation, and CLI tools.
"""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docstring_parser import parse as parse_docstring
from docstring_parser.common import Docstring
from docstring_parser.google import GoogleParser
from docstring_parser.numpydoc import NumpydocParser, ParamSection

from captain.utils.constants import (
    DOCSTRING_KEY,
    PARAMETERS_KEY,
    RETURNS_KEY,
    SHORT_DESCRIPTION_KEY,
    LONG_DESCRIPTION_KEY,
    PARAMETERS_SECTION,
    RETURNS_SECTION,
)


logger = logging.getLogger(__name__)


def find_function_node(tree: ast.Module, function_name: str) -> Optional[ast.FunctionDef]:
    """
    Find a function definition node with the given name in an AST tree.
    
    Args:
        tree: The parsed AST module
        function_name: Name of the function to find
        
    Returns:
        The function definition node if found, None otherwise
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    return None


def extract_docstring_from_node(node: ast.FunctionDef) -> Optional[str]:
    """
    Extract the docstring from a function definition node.
    
    Args:
        node: The function definition AST node
        
    Returns:
        The docstring if found, None otherwise
    """
    if not node.body:
        return None
        
    first_stmt = node.body[0]
    if not isinstance(first_stmt, ast.Expr):
        return None
        
    if isinstance(first_stmt.value, ast.Str):
        # Python < 3.8 compatibility
        return first_stmt.value.s
    elif isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
        # Python >= 3.8
        return first_stmt.value.value
        
    return None


def parse_python_file(file_path: str, function_name: str) -> Tuple[Optional[ast.FunctionDef], Optional[str]]:
    """
    Parse a Python file and extract a specific function's AST node and docstring.
    
    Args:
        file_path: Path to the Python file
        function_name: Name of the function to find
        
    Returns:
        Tuple of (function_node, docstring) or (None, None) if not found
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
            
        tree = ast.parse(code)
        func_node = find_function_node(tree, function_name)
        
        if not func_node:
            return None, None
            
        docstring = extract_docstring_from_node(func_node)
        return func_node, docstring
        
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return None, None
    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return None, None
    except UnicodeDecodeError as e:
        logger.warning(f"Encoding error in {file_path}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error parsing {file_path}: {e}")
        return None, None


def create_docstring_json(parsed_docstring: Docstring, include_empty_fields: bool = True) -> Dict[str, Any]:
    """
    Convert a parsed docstring object to a JSON-compatible dictionary.
    
    Args:
        parsed_docstring: The parsed docstring object from docstring_parser
        include_empty_fields: Whether to include fields with empty values
        
    Returns:
        Dictionary with docstring data
    """
    data: Dict[str, Any] = {
        SHORT_DESCRIPTION_KEY: parsed_docstring.short_description or "",
        LONG_DESCRIPTION_KEY: parsed_docstring.long_description or "",
        PARAMETERS_KEY: [],
        RETURNS_KEY: []
    }
    
    # Extract parameters
    if hasattr(parsed_docstring, 'params'):
        data[PARAMETERS_KEY] = [
            {
                "name": param.arg_name,
                "type": param.type_name or "",
                "description": param.description or ""
            }
            for param in parsed_docstring.params
        ]
    
    # Extract returns - handle both single return and multiple returns
    if hasattr(parsed_docstring, 'many_returns') and parsed_docstring.many_returns:
        data[RETURNS_KEY] = [
            {
                "name": rtn.return_name or "",
                "type": rtn.type_name or "",
                "description": rtn.description or ""
            }
            for rtn in parsed_docstring.many_returns
        ]
    elif hasattr(parsed_docstring, 'returns') and parsed_docstring.returns:
        # Single return case
        data[RETURNS_KEY] = [{
            "name": "",
            "type": parsed_docstring.returns.type_name or "",
            "description": parsed_docstring.returns.description or ""
        }]
    
    # Remove empty fields if requested
    if not include_empty_fields:
        # Remove empty top-level fields but keep parameters and returns arrays
        cleaned_data = {}
        for k, v in data.items():
            if k in [PARAMETERS_KEY, RETURNS_KEY]:
                # Always include these arrays even if empty
                cleaned_data[k] = v
                # Clean up empty fields within each item
                for item in v:
                    for key in list(item.keys()):
                        if not item[key]:
                            del item[key]
            elif v:  # Only include non-empty values for other fields
                cleaned_data[k] = v
        data = cleaned_data
    
    return data


def parse_numpy_style_docstring(docstring: str, extra_sections: Optional[List[Tuple[str, str]]] = None) -> Docstring:
    """
    Parse a NumPy-style docstring with optional extra sections.
    
    Args:
        docstring: The docstring to parse
        extra_sections: List of (section_title, section_key) tuples for additional sections
        
    Returns:
        Parsed docstring object
    """
    parser = NumpydocParser()
    
    # Add extra sections if provided
    if extra_sections:
        for title, key in extra_sections:
            parser.add_section(ParamSection(title, key))
    
    return parser.parse(docstring)


def parse_google_style_docstring(docstring: str) -> Docstring:
    """
    Parse a Google-style docstring.
    
    Args:
        docstring: The docstring to parse
        
    Returns:
        Parsed docstring object
    """
    parser = GoogleParser()
    return parser.parse(docstring)


def extract_docstring_data(file_path: str, function_name: Optional[str] = None, 
                          style: str = "auto") -> Optional[Dict[str, Any]]:
    """
    Extract and parse docstring data from a Python file.
    
    This is a high-level convenience function that combines file parsing,
    docstring extraction, and JSON conversion.
    
    Args:
        file_path: Path to the Python file
        function_name: Name of the function (defaults to filename stem)
        style: Docstring style - "numpy", "google", or "auto" (default)
        
    Returns:
        Dictionary with docstring data or None if extraction fails
    """
    if function_name is None:
        function_name = Path(file_path).stem
    
    # Parse the file and extract docstring
    func_node, docstring = parse_python_file(file_path, function_name)
    if not docstring:
        return None
    
    # Parse the docstring based on style
    if style == "auto":
        # Try to auto-detect style by looking for common patterns
        # Quick check for NumPy-style sections without splitting all lines
        has_numpy_style = False
        
        # Look for NumPy-style section markers with possible indentation
        # Split into lines for more accurate detection
        lines = docstring.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check for Parameters or Returns section headers
            if stripped in [PARAMETERS_SECTION, RETURNS_SECTION] and i + 1 < len(lines):
                # Check if next line contains dashes
                next_line = lines[i + 1].strip()
                if next_line.startswith("---"):
                    has_numpy_style = True
                    break
        
        style = "numpy" if has_numpy_style else "google"
    
    try:
        if style == "numpy":
            parsed = parse_numpy_style_docstring(docstring)
        else:
            parsed = parse_google_style_docstring(docstring)
            
        return {DOCSTRING_KEY: create_docstring_json(parsed)}
        
    except Exception as e:
        logger.warning(f"Failed to parse {style} style docstring: {e}")
        # Fall back to generic parser
        try:
            parsed = parse_docstring(docstring)
            return {DOCSTRING_KEY: create_docstring_json(parsed)}
        except Exception as e2:
            logger.error(f"Failed to parse docstring with generic parser: {e2}")
            return None


def get_param_descriptions(docstring: Optional[str], style: str = "numpy") -> Dict[str, str]:
    """
    Extract parameter descriptions from a docstring.
    
    Args:
        docstring: The docstring to parse
        style: Docstring style - "numpy" or "google"
        
    Returns:
        Dictionary mapping parameter names to descriptions
    """
    if not docstring:
        return {}
        
    try:
        if style == "numpy":
            parsed = parse_numpy_style_docstring(docstring)
        else:
            parsed = parse_google_style_docstring(docstring)
            
        if hasattr(parsed, 'params'):
            return {p.arg_name: p.description for p in parsed.params if p.description}
            
    except Exception as e:
        logger.debug(f"Failed to parse docstring for parameters: {e}")
        
    return {}


def get_return_descriptions(docstring: Optional[str], style: str = "numpy") -> Dict[str, str]:
    """
    Extract return value descriptions from a docstring.
    
    Args:
        docstring: The docstring to parse
        style: Docstring style - "numpy" or "google"
        
    Returns:
        Dictionary mapping return names to descriptions
    """
    if not docstring:
        return {}
        
    try:
        if style == "numpy":
            parsed = parse_numpy_style_docstring(docstring)
        else:
            parsed = parse_google_style_docstring(docstring)
            
        descriptions = {}
        
        # Handle multiple returns
        if hasattr(parsed, 'many_returns') and parsed.many_returns:
            for ret in parsed.many_returns:
                if ret.return_name and ret.description:
                    descriptions[ret.return_name] = ret.description
                elif ret.description:  # Single return without name
                    descriptions[""] = ret.description
                    
        # Handle single return
        elif hasattr(parsed, 'returns') and parsed.returns:
            # For single returns, use empty string as key
            descriptions[""] = parsed.returns.description or ""
            
        return descriptions
        
    except Exception as e:
        logger.debug(f"Failed to parse docstring for returns: {e}")
        
    return {}