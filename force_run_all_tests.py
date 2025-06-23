#!/usr/bin/env python3
"""
Force run all tests by temporarily modifying pytest skip decorators.
This is useful for local development when you have all dependencies installed.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path


def create_pytest_plugin():
    """Create a pytest plugin that overrides skip and skipif markers."""
    plugin_content = '''
import pytest

# Override the skipif marker to never skip
original_skipif = pytest.mark.skipif

def mock_skipif(condition, *, reason=None):
    """Mock skipif that never skips."""
    return pytest.mark.skipif(False, reason=reason or "Force run enabled")

# Replace pytest.mark.skipif
pytest.mark.skipif = mock_skipif

# Override the skip marker
original_skip = pytest.mark.skip

def mock_skip(*, reason=None):
    """Mock skip that never skips."""
    return pytest.mark.skipif(False, reason=reason or "Force run enabled")

pytest.mark.skip = mock_skip

# Ensure xfail tests are run
def pytest_configure(config):
    """Configure pytest to run xfail tests."""
    config.option.runxfail = True
'''

    # Create a temporary directory for our plugin
    plugin_dir = Path(tempfile.mkdtemp())
    plugin_file = plugin_dir / "conftest.py"
    plugin_file.write_text(plugin_content)

    return plugin_dir


def run_all_tests():
    """Run all tests with skip decorators disabled."""
    print("🚀 Force running all tests (ignoring skip decorators)...")
    print("⚠️  Make sure you have all dependencies installed!")
    print()

    # Create the override plugin
    plugin_dir = create_pytest_plugin()

    try:
        # Prepare pytest command with the plugin directory
        cmd = [
            "uv",
            "run",
            "pytest",
            "-v",
            "--runxfail",  # Run xfail tests
            "--tb=short",
            f"--confcutdir={plugin_dir}",  # Use our plugin directory
            "-p",
            "no:cacheprovider",  # Disable cache to ensure fresh run
        ]

        # Add any additional arguments passed to this script
        cmd.extend(sys.argv[1:])

        # Set PYTHONPATH to include our plugin directory
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{plugin_dir}:{pythonpath}" if pythonpath else str(plugin_dir)

        # Run pytest
        result = subprocess.run(cmd, env=env)

        return result.returncode

    finally:
        # Clean up
        shutil.rmtree(plugin_dir, ignore_errors=True)


def check_dependencies():
    """Check if common test dependencies are installed."""
    missing_deps = []

    deps_to_check = [
        ("torch", "PyTorch"),
        ("transformers", "Transformers"),
        ("onnx", "ONNX"),
        ("sympy", "SymPy"),
        ("sklearn", "scikit-learn"),
        ("pyarrow", "PyArrow"),
        ("prophet", "Prophet"),
    ]

    for module, name in deps_to_check:
        try:
            __import__(module)
        except ImportError:
            missing_deps.append(name)

    if missing_deps:
        print("⚠️  Warning: The following dependencies are not installed:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print()
        print("To install all test dependencies, run:")
        print("   bash install_all_test_deps.sh")
        print()
        response = input("Continue anyway? [y/N]: ")
        if response.lower() != "y":
            return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("AtlasVibe Force Run All Tests")
    print("=" * 60)
    print()

    if not check_dependencies():
        sys.exit(1)

    exit_code = run_all_tests()

    print()
    if exit_code == 0:
        print("✅ All tests completed!")
    else:
        print("❌ Some tests failed.")

    sys.exit(exit_code)
