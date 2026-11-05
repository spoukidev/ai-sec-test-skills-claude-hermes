import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _project_home(monkeypatch):
    """Run every test against this checkout and with no real API keys in the environment."""
    monkeypatch.setenv("AISEC_HOME", str(ROOT))
    for k in list(os.environ):
        if k.endswith("_API_KEY") or k.startswith(("AISSEC_", "AISEC_JUDGE", "OPENAI_BASE_URL")):
            monkeypatch.delenv(k, raising=False)
    yield
