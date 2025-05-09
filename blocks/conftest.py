import pytest
import os
import shutil
import tempfile
from contextlib import contextmanager
from functools import wraps
from atlasvibe_engine.utils.cache_utils import ATLASVIBE_CACHE_DIR # Assuming cache dir constant is rebranded
from unittest.mock import patch


@pytest.fixture
def mock_atlasvibe_decorator(deps=None): # Renamed from mock_flojoy_decorator
    """A fixture that mocks the atlasvibe_node decorator to a no-op decorator."""
    # TODO: Add support for mocking dependencies

    def no_op_decorator(func=None, **kwargs):
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                return func(*args, **kwargs)

            return decorated_function

        if func is not None:
            return decorator(func)

        return decorator

    with patch("atlasvibe_engine.node.atlasvibe_node") as mock_atlasvibe: # Assuming decorator is in atlasvibe_engine.node
        mock_atlasvibe.side_effect = no_op_decorator
        yield mock_atlasvibe


@pytest.fixture
def mock_atlasvibe_venv_cache_directory(): # Renamed
    """A fixture that mocks the atlasvibe venv cache directory to a temporary directory"""
    with tempfile.TemporaryDirectory() as tempdir:
        with patch(
            "atlasvibe_engine.node_venv._get_venv_cache_dir", return_value=tempdir # Assuming path
        ) as mock_venv_cache_dir:
            yield mock_venv_cache_dir


@pytest.fixture
def cleanup_atlasvibe_cache_fixture(): # Renamed
    """A fixture that watches for additions to the atlasvibe cache directory and deletes them.
    NOTE: This fixture is not thread-safe. DO NOT run tests in parallel if using this.
    """

    # Helper functions for watching a directory for changes

    def get_all_paths(directory):
        """Recursively get all file and directory paths within the directory."""
        paths = set()
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                paths.add(os.path.join(dirpath, filename))
            for dirname in dirnames:
                paths.add(os.path.join(dirpath, dirname))
        return paths

    @contextmanager
    def watch_directory(path):
        """Watch a directory for changes and yield. After the yield, remove all new files or directories."""
        # Validate that path is a directory
        if os.path.exists(path) and not os.path.isdir(path):
            raise ValueError(f"{path} already exists and is a file")

        try:
            # Store initial files and directories
            initial_contents = get_all_paths(path)
            yield
        finally:
            # Store final files and directories
            final_contents = get_all_paths(path)

            # Find the difference between the two sets, this will be the new files or directories
            new_contents = final_contents - initial_contents

            # Remove all new files or directories
            for content in new_contents:
                if os.path.isfile(content):
                    os.remove(content)
                elif os.path.isdir(content) and not os.path.islink(content):
                    shutil.rmtree(content)
                else:
                    # Does not exist
                    pass

    with watch_directory(ATLASVIBE_CACHE_DIR): # Use rebranded cache dir constant
        yield
