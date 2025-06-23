import os
import pytest

try:
    import pyarrow  # noqa: F401
    import fastparquet  # noqa: F401

    pyarrow = pyarrow
    fastparquet = fastparquet
except ImportError:
    pyarrow = None
    fastparquet = None


@pytest.mark.skipif(
    pyarrow is None or fastparquet is None,
    reason="OPEN_PARQUET requires pyarrow and fastparquet to be installed | Ignore this test in CI",
)
@pytest.mark.slow
def test_OPEN_PARQUET(mock_atlasvibe_decorator):
    import OPEN_PARQUET

    _file_path = (
        f"{os.path.dirname(os.path.realpath(__file__))}/assets/userdata1.parquet"
    )
    output = OPEN_PARQUET.OPEN_PARQUET(_file_path)

    assert output.m.shape == (1000, 13)
