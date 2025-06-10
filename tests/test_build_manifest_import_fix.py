#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created tests for import namespace fix in build_manifest.py
# - Tests verify that 'atlasvibe' imports are redirected to 'pkgs.atlasvibe.atlasvibe'
# - Follows TDD methodology (written after implementation as correction)
# 

"""
Tests for the import namespace fix in build_manifest.py.

This module tests that the custom import hook correctly redirects
'atlasvibe' imports to 'pkgs.atlasvibe.atlasvibe' during manifest generation.
"""

import tempfile
from pathlib import Path

import pytest

from captain.utils.manifest.build_manifest import create_manifest


class TestImportNamespaceFix:
    """Test the import namespace redirection in manifest generation."""
    
    def test_atlasvibe_import_redirection(self):
        """Test that 'import atlasvibe' is redirected correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
import atlasvibe
from atlasvibe import atlasvibe_node, DataContainer

@atlasvibe_node(node_type="TEST", deps={"numpy": "1.0.0"})
def TEST_IMPORT():
    """Test function with atlasvibe imports."""
    return DataContainer(type="scalar", value=42)
''')
            f.flush()
            
            # Should not raise ImportError
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert manifest["name"] == "TEST_IMPORT"
            assert manifest["key"] == "TEST_IMPORT"
            assert manifest["type"] == "TEST"
            assert manifest["pip_dependencies"] == [{"name": "numpy", "v": "1.0.0"}]
            
            Path(f.name).unlink()
    
    def test_atlasvibe_submodule_import(self):
        """Test that 'from atlasvibe.data_container import ...' works."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from atlasvibe.data_container import OrderedPair, Scalar
from atlasvibe import atlasvibe_node

@atlasvibe_node(node_type="MATH")
def MATH_OP(a: Scalar, b: Scalar) -> OrderedPair:
    """Math operation using atlasvibe types."""
    return OrderedPair(x=a.value, y=b.value)
''')
            f.flush()
            
            # Should successfully parse types
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert manifest["name"] == "MATH_OP"
            assert len(manifest["inputs"]) == 2
            assert manifest["inputs"][0]["type"] == "Scalar"
            assert manifest["inputs"][1]["type"] == "Scalar"
            assert manifest["outputs"][0]["type"] == "OrderedPair"
            
            Path(f.name).unlink()
    
    def test_parameter_types_import(self):
        """Test importing parameter types from atlasvibe."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from atlasvibe import atlasvibe_node, TextArea, Secret, File, Directory

@atlasvibe_node
def PARAM_TEST(text: TextArea = TextArea("default text"),
               secret: Secret = Secret(""),
               file: File = File(""),
               directory: Directory = Directory("")):
    """Test various parameter types."""
    pass
''')
            f.flush()
            
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert "parameters" in manifest
            assert manifest["parameters"]["text"]["type"] == "TextArea"
            assert manifest["parameters"]["text"]["default"] == "default text"
            assert manifest["parameters"]["secret"]["type"] == "Secret"
            assert manifest["parameters"]["file"]["type"] == "File"
            assert manifest["parameters"]["directory"]["type"] == "Directory"
            
            Path(f.name).unlink()
    
    def test_hardware_types_import(self):
        """Test importing hardware-related types."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from atlasvibe import (
    atlasvibe_node, 
    CameraDevice, 
    SerialDevice,
    VisaDevice,
    HardwareConnection
)

@atlasvibe_node
def HARDWARE_TEST(
    camera: CameraDevice,
    serial: SerialDevice,
    visa: VisaDevice,
    connection: HardwareConnection
):
    """Test hardware parameter types."""
    pass
''')
            f.flush()
            
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert "parameters" in manifest
            assert manifest["parameters"]["camera"]["type"] == "CameraDevice"
            assert manifest["parameters"]["serial"]["type"] == "SerialDevice"
            assert manifest["parameters"]["visa"]["type"] == "VisaDevice"
            assert manifest["parameters"]["connection"]["type"] == "HardwareConnection"
            
            Path(f.name).unlink()
    
    def test_atlasvibe_decorator_import(self):
        """Test that @atlasvibe decorator works (not just @atlasvibe_node)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from atlasvibe import atlasvibe, Matrix, Vector

@atlasvibe(deps={"scipy": "1.10.0"})  
def SIGNAL_PROCESS(signal: Vector) -> Matrix:
    """Process signal data."""
    return Matrix([[1, 2], [3, 4]])
''')
            f.flush()
            
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert manifest["name"] == "SIGNAL_PROCESS"
            assert manifest["inputs"][0]["type"] == "Vector"
            assert manifest["outputs"][0]["type"] == "Matrix"
            assert manifest["pip_dependencies"] == [{"name": "scipy", "v": "1.10.0"}]
            
            Path(f.name).unlink()
    
    def test_data_container_types_comprehensive(self):
        """Test all DataContainer subclasses can be imported."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from atlasvibe import (
    atlasvibe_node,
    OrderedPair,
    Scalar, 
    Vector,
    Matrix,
    DataFrame,
    Image,
    Surface,
    OrderedTriple,
    Stateful,
    DataContainer
)

@atlasvibe_node
def ALL_TYPES_TEST() -> DataContainer:
    """Test that all types are available."""
    # Just checking imports work
    return Scalar(42)
''')
            f.flush()
            
            # Should not raise any import errors
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert manifest["name"] == "ALL_TYPES_TEST"
            assert manifest["outputs"][0]["type"] == "Any"  # DataContainer becomes Any
            
            Path(f.name).unlink()
    
    def test_non_atlasvibe_imports_unchanged(self):
        """Test that non-atlasvibe imports are not affected."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
import numpy as np
import pandas as pd
from typing import Any
from atlasvibe import atlasvibe_node, Vector

@atlasvibe_node
def NUMPY_TEST(data: Vector) -> Vector:
    """Test with regular imports alongside atlasvibe."""
    # numpy and pandas imports should work normally
    arr = np.array([1, 2, 3])
    return Vector(arr)
''')
            f.flush()
            
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert manifest["name"] == "NUMPY_TEST"
            assert manifest["inputs"][0]["type"] == "Vector"
            assert manifest["outputs"][0]["type"] == "Vector"
            
            Path(f.name).unlink()
    
    def test_import_error_handling(self):
        """Test that invalid imports still raise appropriate errors."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from atlasvibe import NonExistentClass  # This should fail
from atlasvibe import atlasvibe_node

@atlasvibe_node  
def ERROR_TEST():
    pass
''')
            f.flush()
            
            # Should raise AttributeError since NonExistentClass doesn't exist
            with pytest.raises((AttributeError, ImportError)):
                create_manifest(f.name)
            
            Path(f.name).unlink()
    
    def test_fromlist_handling(self):
        """Test that fromlist parameter is handled correctly in imports."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
# Test various import styles
import atlasvibe
from atlasvibe import atlasvibe_node
from atlasvibe import *  # Should work but not recommended

@atlasvibe_node
def FROMLIST_TEST() -> DataContainer:
    """Test fromlist handling."""
    return Scalar(123)
''')
            f.flush()
            
            manifest = create_manifest(f.name)
            
            assert manifest is not None
            assert manifest["name"] == "FROMLIST_TEST"
            # Note: Using module.Class notation in type hints may not parse correctly
            # This is a known limitation
            
            Path(f.name).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])