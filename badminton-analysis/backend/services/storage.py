import json
import os
import shutil
from pathlib import Path
from typing import Protocol

DEFAULT_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")


class StorageBackend(Protocol):
    def create_upload(self, upload_id: str, total_size: int, filename: str) -> None: ...
    def get_upload_meta(self, upload_id: str) -> dict: ...
    def write_chunk(self, upload_id: str, offset: int, data: bytes) -> int: ...
    def finalize_upload(self, upload_id: str) -> None: ...
    def get_video_dir(self, video_id: str) -> Path: ...
    def get_video_path(self, video_id: str, filename: str) -> Path: ...
    def get_analysis_dir(self, analysis_id: str) -> Path: ...


class LocalStorageBackend:
    def __init__(self, base_dir: str | None = None):
        self._base = Path(base_dir or os.environ.get("STORAGE_DIR", DEFAULT_STORAGE_DIR))

    def _uploads_dir(self) -> Path:
        p = self._base / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def create_upload(self, upload_id: str, total_size: int, filename: str) -> None:
        upload_dir = self._uploads_dir() / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        # Pre-allocate sparse file
        with open(upload_dir / "data", "wb") as f:
            if total_size > 0:
                f.seek(total_size - 1)
                f.write(b"\0")
        meta = {
            "upload_id": upload_id,
            "filename": filename,
            "total_size": total_size,
            "offset": 0,
        }
        (upload_dir / "meta.json").write_text(json.dumps(meta))

    def get_upload_meta(self, upload_id: str) -> dict:
        meta_path = self._uploads_dir() / upload_id / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Upload {upload_id} not found")
        return json.loads(meta_path.read_text())

    def write_chunk(self, upload_id: str, offset: int, data: bytes) -> int:
        upload_dir = self._uploads_dir() / upload_id
        with open(upload_dir / "data", "r+b") as f:
            f.seek(offset)
            f.write(data)
        new_offset = offset + len(data)
        meta_path = upload_dir / "meta.json"
        meta = json.loads(meta_path.read_text())
        meta["offset"] = new_offset
        meta_path.write_text(json.dumps(meta))
        return new_offset

    def finalize_upload(self, upload_id: str) -> None:
        upload_dir = self._uploads_dir() / upload_id
        meta = json.loads((upload_dir / "meta.json").read_text())
        video_dir = self.get_video_dir(upload_id)
        shutil.move(str(upload_dir / "data"), str(video_dir / meta["filename"]))
        shutil.rmtree(upload_dir)

    def get_video_dir(self, video_id: str) -> Path:
        p = self._base / video_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_video_path(self, video_id: str, filename: str) -> Path:
        return self.get_video_dir(video_id) / filename

    def get_analysis_dir(self, analysis_id: str) -> Path:
        p = self._base / "analyses" / analysis_id
        p.mkdir(parents=True, exist_ok=True)
        return p


def get_storage() -> LocalStorageBackend:
    return LocalStorageBackend()


# ---------------------------------------------------------------------------
# Backwards-compat shims — routers still use these until Task 3 migrates them
# ---------------------------------------------------------------------------

def get_video_dir(video_id: str) -> Path:
    return get_storage().get_video_dir(video_id)


def get_video_path(video_id: str, filename: str) -> Path:
    return get_storage().get_video_path(video_id, filename)


def get_analysis_dir(analysis_id: str) -> Path:
    return get_storage().get_analysis_dir(analysis_id)
