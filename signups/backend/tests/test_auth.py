from fastapi.testclient import TestClient

from ..storage.memory import InMemoryAdapter


def make_raw_client(monkeypatch, storage=None):
    from .. import main as main_module

    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.delenv("USE_SHEETS", raising=False)
    app = main_module.create_app()
    app.state.storage = storage or InMemoryAdapter()
    return TestClient(app)


def test_admin_routes_require_auth(monkeypatch):
    client = make_raw_client(monkeypatch)

    response = client.get("/api/admin/players")

    assert response.status_code == 403


def test_session_management_routes_require_auth(monkeypatch):
    client = make_raw_client(monkeypatch)

    response = client.get("/api/sessions")

    assert response.status_code == 403


def test_google_login_returns_jwt_for_admin(monkeypatch):
    storage = InMemoryAdapter()
    storage.add_admin("admin@example.com")
    client = make_raw_client(monkeypatch, storage=storage)

    from .. import main as main_module
    from ..auth import decode_jwt

    monkeypatch.setattr(
        main_module,
        "verify_google_id_token",
        lambda token: {"email": "admin@example.com"},
    )

    response = client.post("/auth/google", json={"id_token": "google-id-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert decode_jwt(data["access_token"]) == "admin@example.com"


def test_google_login_rejects_non_admin(monkeypatch):
    client = make_raw_client(monkeypatch)

    from .. import main as main_module

    monkeypatch.setattr(
        main_module,
        "verify_google_id_token",
        lambda token: {"email": "user@example.com"},
    )

    response = client.post("/auth/google", json={"id_token": "google-id-token"})

    assert response.status_code == 403


def test_create_app_uses_in_memory_by_default(monkeypatch):
    from .. import main as main_module
    from ..storage.memory import InMemoryAdapter

    monkeypatch.delenv("USE_SHEETS", raising=False)

    app = main_module.create_app()

    assert isinstance(app.state.storage, InMemoryAdapter)


def test_create_app_uses_sheets_when_enabled(monkeypatch):
    from .. import main as main_module
    from ..storage import sheets as sheets_module

    class FakeSheetsAdapter:
        def __init__(self, spreadsheet_id, credentials_file):
            self.spreadsheet_id = spreadsheet_id
            self.credentials_file = credentials_file

    monkeypatch.setenv("USE_SHEETS", "true")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet-123")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    monkeypatch.setattr(sheets_module, "SheetsAdapter", FakeSheetsAdapter)

    app = main_module.create_app()

    assert isinstance(app.state.storage, FakeSheetsAdapter)
    assert app.state.storage.spreadsheet_id == "sheet-123"
