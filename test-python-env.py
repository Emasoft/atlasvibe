#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Script to verify Python environment setup for atlasvibe
# 

"""Test script to verify the Python environment is correctly set up."""

import sys
import os
import subprocess
from pathlib import Path

def test_python_version():
    """Verify Python version is 3.11."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    assert version.major == 3 and version.minor == 11, f"Expected Python 3.11, got {version.major}.{version.minor}"
    print("✓ Python version is correct (3.11)")

def test_virtual_env():
    """Verify we're in a virtual environment."""
    venv = os.environ.get('VIRTUAL_ENV') or sys.prefix
    print(f"Virtual environment: {venv}")
    assert '.venv' in venv, "Not in a virtual environment"
    print("✓ Running in virtual environment")

def test_poetry_available():
    """Verify Poetry is available."""
    try:
        result = subprocess.run(['poetry', '--version'], capture_output=True, text=True)
        print(f"Poetry version: {result.stdout.strip()}")
        assert result.returncode == 0, "Poetry not found"
        print("✓ Poetry is available")
    except FileNotFoundError:
        print("✗ Poetry not found in PATH")
        raise

def test_project_dependencies():
    """Verify key project dependencies are installed."""
    try:
        import fastapi
        import prefect
        import pandas
        import numpy
        print("✓ Key dependencies are installed")
        print(f"  - FastAPI: {fastapi.__version__}")
        print(f"  - Prefect: {prefect.__version__}")
        print(f"  - Pandas: {pandas.__version__}")
        print(f"  - NumPy: {numpy.__version__}")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        raise

def test_atlasvibe_config():
    """Verify atlasvibe configuration exists."""
    config_path = Path.home() / '.atlasvibe' / 'atlasvibe.yaml'
    print(f"Config path: {config_path}")
    assert config_path.exists(), f"Config file not found at {config_path}"
    print("✓ AtlasVibe configuration exists")

def test_python_cache():
    """Verify Python interpreter cache is set correctly."""
    cache_path = Path.home() / 'Library' / 'Application Support' / 'atlasvibe_py_interpreter'
    if cache_path.exists():
        interpreter = cache_path.read_text().strip()
        print(f"Cached interpreter: {interpreter}")
        assert Path(interpreter).exists(), f"Cached interpreter not found: {interpreter}"
        assert '3.11' in subprocess.check_output([interpreter, '--version']).decode(), "Cached interpreter is not Python 3.11"
        print("✓ Python interpreter cache is correct")
    else:
        print("⚠ Python interpreter cache not found (will be created on first run)")

def main():
    """Run all tests."""
    print("=" * 60)
    print("AtlasVibe Python Environment Test")
    print("=" * 60)
    
    tests = [
        test_python_version,
        test_virtual_env,
        test_poetry_available,
        test_project_dependencies,
        test_atlasvibe_config,
        test_python_cache,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    if failed == 0:
        print("✓ All tests passed! Environment is correctly set up.")
        return 0
    else:
        print(f"✗ {failed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())