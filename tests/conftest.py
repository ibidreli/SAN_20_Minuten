import json
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def fixture_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_metadata(fixture_dir):
    return json.loads((fixture_dir / "fixtures.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def nlp():
    from data_extraction.candidates import load_model

    return load_model()
