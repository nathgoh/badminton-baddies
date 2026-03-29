import pytest

from services.storage import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(base_dir=str(tmp_path))


def test_create_upload_stores_meta(storage):
    storage.create_upload("abc", 100, "video.mp4")
    meta = storage.get_upload_meta("abc")
    assert meta["upload_id"] == "abc"
    assert meta["total_size"] == 100
    assert meta["filename"] == "video.mp4"
    assert meta["offset"] == 0


def test_get_upload_meta_raises_for_unknown(storage):
    with pytest.raises(FileNotFoundError):
        storage.get_upload_meta("nonexistent")


def test_write_chunk_updates_offset(storage):
    storage.create_upload("abc", 10, "video.mp4")
    new_offset = storage.write_chunk("abc", 0, b"hello")
    assert new_offset == 5
    assert storage.get_upload_meta("abc")["offset"] == 5


def test_write_chunk_writes_correct_bytes(storage):
    data = b"hello world"
    storage.create_upload("abc", len(data), "video.mp4")
    storage.write_chunk("abc", 0, data[:5])
    storage.write_chunk("abc", 5, data[5:])
    storage.finalize_upload("abc")
    result = storage.get_video_path("abc", "video.mp4").read_bytes()
    assert result == data


def test_finalize_moves_file_to_video_dir(storage):
    data = b"fake video"
    storage.create_upload("abc", len(data), "game.mp4")
    storage.write_chunk("abc", 0, data)
    storage.finalize_upload("abc")
    assert storage.get_video_path("abc", "game.mp4").exists()


def test_finalize_removes_uploads_dir(storage):
    storage.create_upload("abc", 5, "video.mp4")
    storage.write_chunk("abc", 0, b"hello")
    storage.finalize_upload("abc")
    uploads_dir = storage._uploads_dir() / "abc"
    assert not uploads_dir.exists()


def test_get_video_dir_creates_directory(storage):
    path = storage.get_video_dir("xyz")
    assert path.exists()
    assert path.is_dir()


def test_get_analysis_dir_creates_directory(storage):
    path = storage.get_analysis_dir("xyz")
    assert path.exists()
    assert path.is_dir()


def test_finalize_raises_when_upload_incomplete(storage):
    storage.create_upload("abc", 100, "video.mp4")
    storage.write_chunk("abc", 0, b"partial")
    with pytest.raises(ValueError, match="incomplete"):
        storage.finalize_upload("abc")


def test_create_upload_zero_size(storage):
    storage.create_upload("abc", 0, "empty.mp4")
    meta = storage.get_upload_meta("abc")
    assert meta["total_size"] == 0
    assert meta["offset"] == 0
