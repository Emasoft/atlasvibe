import pytest
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
    with patch("pkgs.atlasvibe.atlasvibe.atlasvibe_python.atlasvibe", side_effect=no_op_decorator), \
         patch("atlasvibe.atlasvibe", side_effect=no_op_decorator, create=True):
        yield no_op_decorator