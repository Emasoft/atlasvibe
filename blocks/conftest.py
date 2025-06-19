import pytest
import shutil
from unittest.mock import patch
from functools import wraps


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
