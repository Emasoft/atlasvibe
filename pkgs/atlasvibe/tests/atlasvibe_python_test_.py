import os
from atlasvibe.atlasvibe_python import cache_huggingface_to_atlasvibe
from atlasvibe.utils import get_hf_hub_cache_path


def test_cache_huggingface_to_atlasvibe_decorator():
    os.environ["HF_HOME"] = "test"

    def test_func():
        return os.environ.get("HF_HOME")

    test_func = cache_huggingface_to_atlasvibe()(test_func)
    assert os.environ.get("HF_HOME") == "test"
    assert test_func() == get_hf_hub_cache_path()
    assert os.environ.get("HF_HOME") == "test"
