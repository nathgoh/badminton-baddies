import pytest
from fastapi.testclient import TestClient

from main import app
from services.storage import LocalStorageBackend, get_storage


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(base_dir=str(tmp_path))


@pytest.fixture
def client(storage):
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_serve_video(client, storage):
    video_id = "test-video-id"
    video_dir = storage.get_video_dir(video_id)
    (video_dir / "test.mp4").write_bytes(b"fake video bytes")

    response = client.get(f"/api/video/{video_id}/test.mp4")
    assert response.status_code == 200
    assert response.content == b"fake video bytes"


def test_serve_video_not_found(client):
    response = client.get("/api/video/nonexistent/nope.mp4")
    assert response.status_code == 404
