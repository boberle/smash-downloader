from pathlib import Path

import pytest


@pytest.fixture
def testdata_directory() -> Path:
    return Path(__file__).parent / "testdata"
