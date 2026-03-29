import os

from fastapi.testclient import TestClient
import pytest

os.environ.setdefault("USE_SHEETS", "false")

from ..main import create_app
from ..middleware import require_admin
from ..storage.memory import InMemoryAdapter


@pytest.fixture
def storage() -> InMemoryAdapter:
    return InMemoryAdapter()


@pytest.fixture
def client(storage: InMemoryAdapter) -> TestClient:
    app = create_app()
    app.state.storage = storage
    app.dependency_overrides[require_admin] = lambda: "test@admin.com"
    return TestClient(app)
