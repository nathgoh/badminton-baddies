import io

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_upload_video(temp_storage):
    fake_video = io.BytesIO(b"fake video content")
    response = client.post(
        "/api/upload",
        files={"file": ("test_match.mp4", fake_video, "video/mp4")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "video_id" in data
    assert data["filename"] == "test_match.mp4"


def test_upload_no_file():
    response = client.post("/api/upload")
    assert response.status_code == 422
