import pytest
import os
import shutil
import tempfile
from contextlib import contextmanager
from functools import wraps
# Assuming ATLASVIBE_CACHE_DIR is defined in atlasvibe_engine.utils.cache_utils
# If not, this import will fail. For now, we'll assume it exists or will be created.
from atlasvibe_engine.utils.cache_utils import ATLASVIBE_CACHE_DIR 
from unittest.mock import patch


@pytest.fixture
def mock_atlasvibe_decorator(deps=None): 
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

    # The actual path to atlasvibe_node decorator might be different.
    # This assumes it's in a module like `atlasvibe_engine.node` or similar.
    # If the decorator is globally available or imported differently in blocks, this path needs adjustment.
    with patch("atlasvibe_engine.flojoy_python.atlasvibe_node", new=no_op_decorator) as mock_atlasvibe:
        # The above path "atlasvibe_engine.flojoy_python.atlasvibe_node" is an assumption based on previous file structures.
        # It should point to where @atlasvibe_node is actually defined and imported by blocks.
        # If blocks import it as `from atlasvibe import atlasvibe_node`, then it might be `atlasvibe.atlasvibe_node`.
        # This needs to match how blocks will import the decorator.
        yield mock_atlasvibe


@pytest.fixture
def mock_atlasvibe_venv_cache_directory(): 
    """A fixture that mocks the atlasvibe venv cache directory to a temporary directory"""
    with tempfile.TemporaryDirectory() as tempdir:
        # This path also needs to be correct, where _get_venv_cache_dir is defined.
        with patch(
            "atlasvibe_engine.node_venv._get_venv_cache_dir", return_value=tempdir 
        ) as mock_venv_cache_dir:
            yield mock_venv_cache_dir


@pytest.fixture
def cleanup_atlasvibe_cache_fixture(): 
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

    with watch_directory(ATLASVIBE_CACHE_DIR): 
        yield
