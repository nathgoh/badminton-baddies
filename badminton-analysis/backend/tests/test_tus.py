import base64

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


def _filename_meta(name: str) -> str:
    return f"filename {base64.b64encode(name.encode()).decode()}"


def test_options_returns_tus_headers(client):
    response = client.options("/api/tus")
    assert response.status_code == 204
    assert response.headers["tus-resumable"] == "1.0.0"
    assert "creation" in response.headers["tus-extension"]
    assert "tus-max-size" in response.headers


def test_post_creates_upload_and_returns_location(client):
    response = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": "100",
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    assert response.status_code == 201
    assert response.headers["location"].startswith("/api/tus/")
    assert response.headers["upload-offset"] == "0"


def test_post_missing_upload_length_returns_400(client):
    response = client.post(
        "/api/tus",
        headers={"Tus-Resumable": "1.0.0"},
    )
    assert response.status_code == 400


def test_head_returns_current_offset(client):
    post = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": "100",
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    upload_id = post.headers["location"].split("/")[-1]

    head = client.head(f"/api/tus/{upload_id}", headers={"Tus-Resumable": "1.0.0"})
    assert head.status_code == 200
    assert head.headers["upload-offset"] == "0"
    assert head.headers["upload-length"] == "100"


def test_head_unknown_upload_returns_404(client):
    assert client.head("/api/tus/nonexistent", headers={"Tus-Resumable": "1.0.0"}).status_code == 404


def test_patch_uploads_chunk_and_returns_new_offset(client):
    data = b"hello world"
    post = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(len(data) + 5),
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    upload_id = post.headers["location"].split("/")[-1]

    patch = client.patch(
        f"/api/tus/{upload_id}",
        content=data,
        headers={
            "Tus-Resumable": "1.0.0",
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": "0",
        },
    )
    assert patch.status_code == 204
    assert patch.headers["upload-offset"] == str(len(data))
    assert "x-video-id" not in patch.headers  # not complete yet


def test_patch_completes_upload_returns_video_id(client):
    data = b"hello world"
    post = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(len(data)),
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    upload_id = post.headers["location"].split("/")[-1]

    patch = client.patch(
        f"/api/tus/{upload_id}",
        content=data,
        headers={
            "Tus-Resumable": "1.0.0",
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": "0",
        },
    )
    assert patch.status_code == 204
    assert patch.headers["x-video-id"] == upload_id


def test_patch_wrong_content_type_returns_415(client):
    post = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": "10",
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    upload_id = post.headers["location"].split("/")[-1]

    patch = client.patch(
        f"/api/tus/{upload_id}",
        content=b"data",
        headers={
            "Tus-Resumable": "1.0.0",
            "Content-Type": "application/json",
            "Upload-Offset": "0",
        },
    )
    assert patch.status_code == 415


def test_patch_offset_mismatch_returns_409(client):
    post = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": "100",
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    upload_id = post.headers["location"].split("/")[-1]

    patch = client.patch(
        f"/api/tus/{upload_id}",
        content=b"data",
        headers={
            "Tus-Resumable": "1.0.0",
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": "50",  # wrong — should be 0
        },
    )
    assert patch.status_code == 409


def test_post_file_too_large_returns_413(client):
    response = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(10 * 1024 * 1024 * 1024 + 1),  # 10GB + 1 byte
            "Upload-Metadata": _filename_meta("huge.mp4"),
        },
    )
    assert response.status_code == 413


def test_patch_missing_tus_resumable_returns_412(client):
    post = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": "10",
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    upload_id = post.headers["location"].split("/")[-1]

    patch = client.patch(
        f"/api/tus/{upload_id}",
        content=b"data",
        headers={
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": "0",
            # No Tus-Resumable header
        },
    )
    assert patch.status_code == 412


def test_post_wrong_tus_resumable_returns_412(client):
    response = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "2.0.0",
            "Upload-Length": "100",
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    assert response.status_code == 412


def test_resumption_via_head_then_patch(client):
    data = b"hello world"
    post = client.post(
        "/api/tus",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(len(data)),
            "Upload-Metadata": _filename_meta("game.mp4"),
        },
    )
    upload_id = post.headers["location"].split("/")[-1]

    # Upload first half
    client.patch(
        f"/api/tus/{upload_id}",
        content=data[:5],
        headers={
            "Tus-Resumable": "1.0.0",
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": "0",
        },
    )

    # Check offset
    head = client.head(f"/api/tus/{upload_id}", headers={"Tus-Resumable": "1.0.0"})
    assert head.headers["upload-offset"] == "5"

    # Resume from offset 5
    patch2 = client.patch(
        f"/api/tus/{upload_id}",
        content=data[5:],
        headers={
            "Tus-Resumable": "1.0.0",
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": "5",
        },
    )
    assert patch2.status_code == 204
    assert patch2.headers["x-video-id"] == upload_id
