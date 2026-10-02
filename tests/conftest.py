import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOKEN = "test-token"

# The server reads its settings at import time, so set them first.
_data = tempfile.mkdtemp(prefix="carcode-test-")
os.environ.update({
    "CARCODE_TOKEN": TOKEN,
    "CARCODE_DATA_DIR": _data,
    "CARCODE_WORKDIR": _data,
    "CARCODE_NAME": "Jarvis",
    "CARCODE_WAIT_SECONDS": "1.5",
    "CLAUDE_BIN": str(HERE / "fake_claude.py"),
})
sys.path.insert(0, str(HERE.parent))

import server  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    server.devices.clear()
    server.HISTORY.clear()
    server.STATE_FILE.unlink(missing_ok=True)
    with TestClient(server.app) as c:
        yield c
    server.devices.clear()


@pytest.fixture
def say(client):
    def _say(text: str, device: str = "phone") -> dict:
        r = client.post("/voice", json={"text": text, "device": device},
                        headers={"X-Carcode-Token": TOKEN})
        assert r.status_code == 200
        return r.json()
    return _say
