import pytest
import requests.exceptions

# Fix imports - use direct imports from data_container
from pkgs.atlasvibe.atlasvibe.data_container import Image, DataFrame, Grayscale

# Using public test images for testing
PUBLIC_TEST_IMAGES_BASE_URL = "https://raw.githubusercontent.com/python-pillow/Pillow/main/Tests/images"

@pytest.mark.parametrize(
    "file_type, output_type, file_url",
    [
        ("Image", Image, f"{PUBLIC_TEST_IMAGES_BASE_URL}/hopper.png"),
        ("Grayscale", Grayscale, f"{PUBLIC_TEST_IMAGES_BASE_URL}/hopper.png"),
        ("CSV", DataFrame, "https://raw.githubusercontent.com/pandas-dev/pandas/main/pandas/tests/io/data/csv/iris.csv"),
        ("JSON", DataFrame, "https://jsonplaceholder.typicode.com/users"),
    ],
)
def test_REMOTE_FILE_valid_usage(
    mock_atlasvibe_decorator, file_type, output_type, file_url
):
    import REMOTE_FILE

    output = REMOTE_FILE.REMOTE_FILE(file_url=file_url, file_type=file_type)
    assert isinstance(output, output_type)

@pytest.mark.parametrize(
    "file_url",
    [
        "not_valid",
        "/not/a/valid/url",
        "ftp://not_existing.url",
        "htp://misstyped.url",
    ],
)
def test_REMOTE_FILE_not_valid(file_url, mock_atlasvibe_decorator):
    import REMOTE_FILE

    with pytest.raises(ValueError):
        REMOTE_FILE.REMOTE_FILE(file_url=file_url, file_type="Image")

@pytest.mark.parametrize(
    "file_url", ["gcp://not_yet_supported", "s3://not_yet_supported"]
)
def test_REMOTE_FILE_not_yet_supported(file_url, mock_atlasvibe_decorator):
    import REMOTE_FILE

    error_msg = f"No connection adapters were found for '{file_url}'"
    with pytest.raises(requests.exceptions.InvalidSchema, match=error_msg):
        REMOTE_FILE.REMOTE_FILE(file_url=file_url, file_type="Image")
