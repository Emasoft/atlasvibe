import pytest
import shutil
import sys
import os
from pathlib import Path
from unittest.mock import patch
from functools import wraps


def pytest_configure(config):
    """Configure pytest to add block directories to sys.path for imports."""
    # Get the blocks directory
    blocks_dir = Path(__file__).parent

    # Add the blocks directory itself to sys.path
    if str(blocks_dir) not in sys.path:
        sys.path.insert(0, str(blocks_dir))

    # Walk through all subdirectories and add block directories to sys.path
    for root, dirs, files in os.walk(blocks_dir):
        # Skip __pycache__ and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

        # Check if this directory contains a Python file with the same name
        root_path = Path(root)
        dir_name = root_path.name

        # Add directory to sys.path if it contains a block module
        if any(f == f"{dir_name}.py" for f in files):
            if str(root_path) not in sys.path:
                sys.path.insert(0, str(root_path))


@pytest.fixture(autouse=True)
def add_block_to_path(request):
    """Automatically add the test's block directory to sys.path."""
    test_file = Path(request.fspath)
    test_dir = test_file.parent

    # Ensure the test directory is in sys.path
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))

    yield

    # Optionally remove the path after the test
    # This is commented out to avoid issues with parallel test execution
    # if str(test_dir) in sys.path:
    #     sys.path.remove(str(test_dir))


@pytest.fixture
def mock_atlasvibe_decorator():
    """A fixture that mocks the atlasvibe decorator to a no-op decorator."""

    def no_op_decorator(func=None, **kwargs):
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                return func(*args, **kwargs)

            return decorated_function

        if func is not None:
            return decorator(func)
        return decorator

    # Patch the atlasvibe decorator in multiple locations
    with (
        patch(
            "pkgs.atlasvibe.atlasvibe.atlasvibe_python.atlasvibe",
            side_effect=no_op_decorator,
        ),
        patch("atlasvibe.atlasvibe", side_effect=no_op_decorator, create=True),
    ):
        yield no_op_decorator


@pytest.fixture
def mock_atlasvibe_node_decorator():
    """A fixture that mocks the atlasvibe_node decorator to a no-op decorator."""

    def no_op_decorator(func=None, **kwargs):
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                return func(*args, **kwargs)

            return decorated_function

        if func is not None:
            return decorator(func)
        return decorator

    # Patch the atlasvibe_node decorator in multiple locations
    with (
        patch(
            "pkgs.atlasvibe.atlasvibe.atlasvibe_python.atlasvibe_node",
            side_effect=no_op_decorator,
        ),
        patch("atlasvibe.atlasvibe_node", side_effect=no_op_decorator, create=True),
    ):
        yield no_op_decorator


@pytest.fixture
def mock_atlasvibe_venv_cache_directory(tmp_path):
    """Mock the AtlasVibe virtual environment cache directory."""
    cache_dir = tmp_path / "atlasvibe_cache"
    cache_dir.mkdir(exist_ok=True)

    # Patch the ATLASVIBE_CACHE_DIR constant
    with (
        patch("pkgs.atlasvibe.atlasvibe.CONSTANTS.ATLASVIBE_CACHE_DIR", str(cache_dir)),
        patch(
            "pkgs.atlasvibe.atlasvibe.atlasvibe_node_venv.ATLASVIBE_CACHE_DIR",
            str(cache_dir),
        ),
    ):
        yield cache_dir


@pytest.fixture
def cleanup_atlasvibe_cache_fixture(mock_atlasvibe_venv_cache_directory):
    """Cleanup the AtlasVibe cache after test execution."""
    cache_dir = mock_atlasvibe_venv_cache_directory

    yield cache_dir

    # Cleanup after test
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
