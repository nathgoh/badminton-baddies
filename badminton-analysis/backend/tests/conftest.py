import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_storage(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("STORAGE_DIR", tmpdir)
    yield tmpdir
    shutil.rmtree(tmpdir)
