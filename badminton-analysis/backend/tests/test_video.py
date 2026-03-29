from fastapi.testclient import TestClient

from main import app
from services.storage import get_video_dir

client = TestClient(app)


def test_serve_video(temp_storage):
    video_id = "test-video-id"
    video_dir = get_video_dir(video_id)
    (video_dir / "test.mp4").write_bytes(b"fake video bytes")

    response = client.get(f"/api/video/{video_id}/test.mp4")
    assert response.status_code == 200
    assert response.content == b"fake video bytes"


def test_serve_video_not_found():
    response = client.get("/api/video/nonexistent/nope.mp4")
    assert response.status_code == 404
