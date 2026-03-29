from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from main import app
from models.schemas import BoundingBox

client = TestClient(app)


def test_detect_persons(temp_storage):
    from services.storage import get_video_dir

    # Create a fake video file (1 frame, 100x100, 3 channels)
    video_id = "detect-test"
    video_dir = get_video_dir(video_id)

    # We need a real video file for OpenCV to read, so create a minimal one
    import cv2
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    video_path = str(video_dir / "test.mp4")
    writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (100, 100))
    writer.write(frame)
    writer.release()

    fake_boxes = [
        BoundingBox(id=0, x=10, y=20, width=30, height=60, confidence=0.9),
    ]
    fake_frame = np.zeros((100, 100, 3), dtype=np.uint8)

    with patch("routers.detect.detect_persons") as mock_detect:
        mock_detect.return_value = (fake_frame, fake_boxes)
        response = client.post(
            "/api/detect",
            json={"video_id": video_id, "frame_number": 0},
        )

    assert response.status_code == 200
    data = response.json()
    assert "frame_image" in data
    assert len(data["persons"]) == 1
    assert data["persons"][0]["x"] == 10


def test_detect_invalid_video():
    response = client.post(
        "/api/detect",
        json={"video_id": "nonexistent", "frame_number": 0},
    )
    assert response.status_code == 404
