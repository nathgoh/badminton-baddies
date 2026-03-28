import os
from pathlib import Path

STORAGE_DIR = os.environ.get("STORAGE_DIR", os.path.join(os.path.dirname(__file__), "..", "storage"))


def get_storage_dir() -> Path:
    path = Path(STORAGE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_video_dir(video_id: str) -> Path:
    path = get_storage_dir() / video_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_video_path(video_id: str, filename: str) -> Path:
    return get_video_dir(video_id) / filename


def get_analysis_dir(analysis_id: str) -> Path:
    path = get_storage_dir() / "analyses" / analysis_id
    path.mkdir(parents=True, exist_ok=True)
    return path
