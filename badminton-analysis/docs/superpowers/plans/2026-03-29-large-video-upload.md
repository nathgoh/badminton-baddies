# Large Video Upload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the in-memory upload endpoint with a tus-protocol resumable chunked upload server, backed by a `StorageBackend` abstraction for future cloud migration, supporting multi-GB videos with real upload progress.

**Architecture:** New `StorageBackend` protocol + `LocalStorageBackend` class in `services/storage.py` wraps all file I/O and is injected via FastAPI `Depends`. A new `routers/tus.py` implements tus 1.0.0 (OPTIONS/POST/HEAD/PATCH). `tus-js-client` on the frontend handles chunking, progress, and auto-resumption. Old `routers/upload.py` is removed.

**Tech Stack:** FastAPI, Python 3.12, pytest, httpx | tus-js-client v3, React 18, TypeScript, Vite

---

## File Map

| File | Change |
|------|--------|
| `backend/services/storage.py` | Rewrite: `StorageBackend` protocol + `LocalStorageBackend` + `get_storage()` DI factory |
| `backend/routers/tus.py` | New: OPTIONS, POST, HEAD, PATCH tus endpoints |
| `backend/routers/upload.py` | Deleted |
| `backend/main.py` | Remove upload router; add tus router |
| `backend/routers/detect.py` | Use `Depends(get_storage)` instead of direct function import |
| `backend/routers/video.py` | Use `Depends(get_storage)` instead of direct function import |
| `backend/routers/analyze.py` | Use `Depends(get_storage)`; move executor to module level |
| `backend/tests/test_storage.py` | New: unit tests for `LocalStorageBackend` |
| `backend/tests/test_tus.py` | New: integration tests for tus endpoints |
| `backend/tests/test_upload.py` | Deleted (endpoint removed) |
| `backend/tests/test_video.py` | Update: use `LocalStorageBackend` instead of old `get_video_dir` import |
| `frontend/src/components/VideoUploader.tsx` | Rewrite upload logic with `tus-js-client` |
| `frontend/src/api/client.ts` | Remove `uploadVideo()` method |

---

### Task 1: Rewrite `services/storage.py` with StorageBackend abstraction

**Files:**
- Modify: `backend/services/storage.py`
- Create: `backend/tests/test_storage.py`

- [ ] **Step 1: Write failing tests for `LocalStorageBackend`**

Create `backend/tests/test_storage.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd badminton-analysis/backend
python -m pytest tests/test_storage.py -v
```

Expected: `ImportError` or `AttributeError` — `LocalStorageBackend` doesn't have these methods yet.

- [ ] **Step 3: Rewrite `services/storage.py`**

Replace the entire file:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_storage.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/storage.py backend/tests/test_storage.py
git commit -m "feat: add StorageBackend protocol and LocalStorageBackend with tus upload support"
```

---

### Task 2: Create tus server router

**Files:**
- Create: `backend/routers/tus.py`
- Create: `backend/tests/test_tus.py`

- [ ] **Step 1: Write failing tus endpoint tests**

Create `backend/tests/test_tus.py`:

```python
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

    head = client.head(f"/api/tus/{upload_id}")
    assert head.status_code == 200
    assert head.headers["upload-offset"] == "0"
    assert head.headers["upload-length"] == "100"


def test_head_unknown_upload_returns_404(client):
    assert client.head("/api/tus/nonexistent").status_code == 404


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
    head = client.head(f"/api/tus/{upload_id}")
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_tus.py -v
```

Expected: `404 Not Found` for all tus routes — router not registered yet.

- [ ] **Step 3: Create `routers/tus.py`**

```python
import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from services.storage import LocalStorageBackend, get_storage

router = APIRouter(prefix="/api/tus")

TUS_VERSION = "1.0.0"
TUS_MAX_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB


@router.options("")
async def tus_options() -> Response:
    return Response(
        status_code=204,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Tus-Version": TUS_VERSION,
            "Tus-Max-Size": str(TUS_MAX_SIZE),
            "Tus-Extension": "creation",
        },
    )


@router.post("")
async def tus_create(
    request: Request,
    storage: LocalStorageBackend = Depends(get_storage),
) -> Response:
    upload_length = request.headers.get("Upload-Length")
    if not upload_length:
        raise HTTPException(status_code=400, detail="Upload-Length header required")

    total_size = int(upload_length)
    if total_size > TUS_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    filename = "upload"
    for part in request.headers.get("Upload-Metadata", "").split(","):
        part = part.strip()
        if part.startswith("filename "):
            filename = base64.b64decode(part[len("filename "):]).decode("utf-8")
            break

    upload_id = str(uuid.uuid4())
    storage.create_upload(upload_id, total_size, filename)

    return Response(
        status_code=201,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Location": f"/api/tus/{upload_id}",
            "Upload-Offset": "0",
        },
    )


@router.head("/{upload_id}")
async def tus_head(
    upload_id: str,
    storage: LocalStorageBackend = Depends(get_storage),
) -> Response:
    try:
        meta = storage.get_upload_meta(upload_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Upload not found")

    return Response(
        status_code=200,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Upload-Offset": str(meta["offset"]),
            "Upload-Length": str(meta["total_size"]),
            "Cache-Control": "no-store",
        },
    )


@router.patch("/{upload_id}")
async def tus_patch(
    upload_id: str,
    request: Request,
    storage: LocalStorageBackend = Depends(get_storage),
) -> Response:
    if request.headers.get("Content-Type") != "application/offset+octet-stream":
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/offset+octet-stream",
        )

    upload_offset = request.headers.get("Upload-Offset")
    if upload_offset is None:
        raise HTTPException(status_code=400, detail="Upload-Offset header required")

    offset = int(upload_offset)

    try:
        meta = storage.get_upload_meta(upload_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Upload not found")

    if meta["offset"] != offset:
        raise HTTPException(
            status_code=409,
            detail=f"Offset mismatch: expected {meta['offset']}, got {offset}",
        )

    data = await request.body()
    new_offset = storage.write_chunk(upload_id, offset, data)

    headers = {
        "Tus-Resumable": TUS_VERSION,
        "Upload-Offset": str(new_offset),
    }

    if new_offset == meta["total_size"]:
        storage.finalize_upload(upload_id)
        headers["X-Video-Id"] = upload_id

    return Response(status_code=204, headers=headers)
```

- [ ] **Step 4: Register the tus router in `main.py`**

In `main.py`, add the tus import and `app.include_router` call (keep upload router for now — it will be removed in Task 4):

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import upload, video, detect, analyze, tus

app = FastAPI(title="Badminton Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(tus.router)
app.include_router(video.router)
app.include_router(detect.router)
app.include_router(analyze.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run tus tests to verify they pass**

```bash
python -m pytest tests/test_tus.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/tus.py backend/tests/test_tus.py backend/main.py
git commit -m "feat: add tus resumable upload server"
```

---

### Task 3: Migrate existing routers to use StorageBackend DI

**Files:**
- Modify: `backend/routers/detect.py`
- Modify: `backend/routers/video.py`
- Modify: `backend/routers/analyze.py`
- Modify: `backend/tests/test_video.py`

- [ ] **Step 1: Update `routers/detect.py`**

```python
import base64

import cv2
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import DetectRequest, DetectResponse
from services.detection import detect_persons
from services.storage import LocalStorageBackend, get_storage

router = APIRouter(prefix="/api")


@router.post("/detect", response_model=DetectResponse)
async def detect(
    request: DetectRequest,
    storage: LocalStorageBackend = Depends(get_storage),
):
    video_dir = storage.get_video_dir(request.video_id)
    video_files = (
        list(video_dir.glob("*.mp4"))
        + list(video_dir.glob("*.avi"))
        + list(video_dir.glob("*.mov"))
    )
    if not video_files:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(video_files[0])
    frame, persons = detect_persons(video_path, request.frame_number)

    _, buffer = cv2.imencode(".jpg", frame)
    frame_b64 = base64.b64encode(buffer).decode("utf-8")

    return DetectResponse(frame_image=frame_b64, persons=persons)
```

- [ ] **Step 2: Update `routers/video.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from services.storage import LocalStorageBackend, get_storage

router = APIRouter(prefix="/api")


@router.get("/video/{video_id}/{filename}")
async def serve_video(
    video_id: str,
    filename: str,
    storage: LocalStorageBackend = Depends(get_storage),
):
    path = storage.get_video_path(video_id, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/video/analyses/{analysis_id}/{filename}")
async def serve_analysis_video(
    analysis_id: str,
    filename: str,
    storage: LocalStorageBackend = Depends(get_storage),
):
    path = storage.get_analysis_dir(analysis_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Analysis video not found")
    return FileResponse(path, media_type="video/mp4")
```

- [ ] **Step 3: Update `routers/analyze.py`**

Replace the top of the file (imports + executor):

```python
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.schemas import (
    AnalyzeRequest, AnalyzeStartResponse, AnalysisStatus,
    AnalysisResult, BoundingBox
)
from services.analysis import compute_stats, render_annotated_video
from services.detection import detect_persons
from services.pose import estimate_pose
from services.storage import LocalStorageBackend, get_storage
from services.tracking import track_person_in_frame

router = APIRouter(prefix="/api")

_analysis_status = {}
_status_lock = Lock()
_executor = ThreadPoolExecutor(max_workers=2)
```

Update `start_analysis` to accept and forward storage:

```python
@router.post("/analyze", response_model=AnalyzeStartResponse)
async def start_analysis(
    request: AnalyzeRequest,
    storage: LocalStorageBackend = Depends(get_storage),
):
    analysis_id = str(uuid.uuid4())

    with _status_lock:
        _analysis_status[analysis_id] = AnalysisJob(
            id=analysis_id,
            status="processing",
            progress=0.0
        )

    _executor.submit(_run_analysis, analysis_id, request, storage)

    return AnalyzeStartResponse(analysis_id=analysis_id, status="processing")
```

Update `_run_analysis` signature and storage calls:

```python
def _run_analysis(analysis_id: str, request: AnalyzeRequest, storage: LocalStorageBackend):
    """Background analysis job."""
    try:
        _update_progress(analysis_id, 0.1)

        video_dir = storage.get_video_dir(request.video_id)
        video_files = (
            list(video_dir.glob("*.mp4"))
            + list(video_dir.glob("*.avi"))
            + list(video_dir.glob("*.mov"))
        )
        if not video_files:
            raise Exception("Video not found")

        video_path = str(video_files[0])
```

And later in the same function:

```python
        analysis_dir = storage.get_analysis_dir(analysis_id)
```

(All other lines in `_run_analysis` stay the same.)

- [ ] **Step 4: Update `tests/test_video.py`** to use `LocalStorageBackend` instead of the removed `get_video_dir`

```python
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
```

- [ ] **Step 5: Run the full test suite to verify**

```bash
python -m pytest tests/ -v --ignore=tests/test_upload.py
```

Expected: all tests PASS (ignoring test_upload.py which tests a route we're about to delete).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/detect.py backend/routers/video.py backend/routers/analyze.py backend/tests/test_video.py
git commit -m "refactor: migrate routers to StorageBackend DI and fix ThreadPoolExecutor leak"
```

---

### Task 4: Remove old upload endpoint

**Files:**
- Delete: `backend/routers/upload.py`
- Delete: `backend/tests/test_upload.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Remove upload router from `main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import video, detect, analyze, tus

app = FastAPI(title="Badminton Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tus.router)
app.include_router(video.router)
app.include_router(detect.router)
app.include_router(analyze.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Delete the old files**

```bash
rm backend/routers/upload.py
rm backend/tests/test_upload.py
```

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests PASS. No references to `/api/upload`.

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "feat: remove legacy in-memory upload endpoint"
```

---

### Task 5: Frontend — tus-js-client integration

**Files:**
- Modify: `frontend/src/components/VideoUploader.tsx`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Install `tus-js-client`**

```bash
cd badminton-analysis/frontend
npm install tus-js-client
```

Expected: package added to `package.json` and `package-lock.json`.

- [ ] **Step 2: Rewrite `VideoUploader.tsx`**

```tsx
import React, { useRef, useState } from 'react';
import * as tus from 'tus-js-client';
import { Upload, FileVideo, AlertCircle } from 'lucide-react';

interface VideoUploaderProps {
  onUploadSuccess: (videoId: string) => void;
}

export default function VideoUploader({ onUploadSuccess }: VideoUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    const videoFile = files.find((f) => f.type.startsWith('video/'));
    if (videoFile) {
      handleFileUpload(videoFile);
    } else {
      setError('Please upload a video file');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
  };

  const handleFileUpload = async (file: File) => {
    setError(null);
    setIsUploading(true);
    setUploadProgress(0);

    const upload = new tus.Upload(file, {
      endpoint: '/api/tus',
      chunkSize: 10 * 1024 * 1024,
      retryDelays: [0, 1000, 3000, 5000],
      metadata: {
        filename: file.name,
        filetype: file.type,
      },
      onProgress(bytesUploaded: number, bytesTotal: number) {
        setUploadProgress(Math.round((bytesUploaded / bytesTotal) * 100));
      },
      onSuccess() {
        const videoId = upload.url!.split('/').pop()!;
        setUploadProgress(100);
        setTimeout(() => onUploadSuccess(videoId), 500);
      },
      onError(err: tus.DetailedError | Error) {
        setError(err.message || 'Upload failed');
        setIsUploading(false);
        setUploadProgress(0);
      },
    });

    const previousUploads = await upload.findPreviousUploads();
    if (previousUploads.length > 0) {
      upload.resumeFromPreviousUpload(previousUploads[0]);
    }

    upload.start();
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${isUploading ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={!isUploading ? handleClick : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isUploading}
        />

        <div className="flex flex-col items-center space-y-4">
          {isUploading ? (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
              <div className="w-full max-w-xs">
                <div className="text-sm text-gray-600 mb-2">
                  Uploading... {uploadProgress}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            </>
          ) : (
            <>
              <Upload className="h-12 w-12 text-gray-400" />
              <div>
                <p className="text-lg font-medium text-gray-900">
                  Drop your video here or click to browse
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Supports MP4, AVI, MOV files
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 flex items-center space-x-2 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      <div className="mt-6 text-center">
        <p className="text-xs text-gray-500">
          <FileVideo className="inline h-4 w-4 mr-1" />
          No file size limit — large videos supported
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Remove `uploadVideo` from `api/client.ts`**

```typescript
import {
  DetectRequest,
  DetectResponse,
  AnalyzeRequest,
  AnalyzeStartResponse,
  AnalysisStatus,
  AnalysisResult,
} from '../types';

const API_BASE = '/api';

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async detectPersons(request: DetectRequest): Promise<DetectResponse> {
    return this.request<DetectResponse>('/detect', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async startAnalysis(request: AnalyzeRequest): Promise<AnalyzeStartResponse> {
    return this.request<AnalyzeStartResponse>('/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
    return this.request<AnalysisStatus>(`/analyze/${analysisId}/status`);
  }

  async getAnalysisResults(analysisId: string): Promise<AnalysisResult> {
    return this.request<AnalysisResult>(`/analyze/${analysisId}/results`);
  }

  getVideoUrl(videoId: string, filename: string): string {
    return `${API_BASE}/video/${videoId}/${filename}`;
  }

  getAnnotatedVideoUrl(analysisId: string): string {
    return `${API_BASE}/video/analyses/${analysisId}/annotated_video.mp4`;
  }
}

export const apiClient = new ApiClient();
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd badminton-analysis/frontend
npm run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
cd badminton-analysis
git add frontend/src/components/VideoUploader.tsx frontend/src/api/client.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: replace upload with tus-js-client for resumable multi-GB video uploads"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| tus OPTIONS/POST/HEAD/PATCH | Task 2 |
| Upload state in `storage/uploads/{id}/meta.json` | Task 1 (`create_upload`) |
| Chunk written via seek+write | Task 1 (`write_chunk`) |
| Finalize moves data → `{video_id}/{filename}` | Task 1 (`finalize_upload`) |
| `X-Video-Id` on completion | Task 2 (`tus_patch`) |
| `StorageBackend` Protocol | Task 1 |
| `get_storage()` DI factory | Task 1 |
| All routers use `Depends(get_storage)` | Task 3 |
| Fix `ThreadPoolExecutor` leak | Task 3 |
| Remove old upload endpoint | Task 4 |
| `tus-js-client` frontend integration | Task 5 |
| Real progress tracking | Task 5 (`onProgress`) |
| Resumption via `findPreviousUploads` | Task 5 |
| Remove `uploadVideo` from `client.ts` | Task 5 |
| "No file size limit" label | Task 5 |

All requirements covered. No gaps.
