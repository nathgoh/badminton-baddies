# Badminton Video Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-friendly web app where users upload badminton videos, select a player to track, and receive AI-powered analysis (annotated video + stats dashboard).

**Architecture:** Monorepo with `frontend/` (Vite + React + TS + Tailwind) and `backend/` (FastAPI). The backend runs YOLO for person detection, tracks the selected person frame-by-frame, runs MediaPipe Pose for skeleton extraction, computes stats, and renders an annotated video. Frontend proxies API requests to backend during development.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, React Router v6, Recharts | FastAPI, Python 3.10+, OpenCV, Ultralytics YOLOv8, MediaPipe, pytest, httpx

---

## File Map

### Backend

| File | Responsibility |
|------|---------------|
| `backend/main.py` | FastAPI app factory, CORS, router registration |
| `backend/routers/__init__.py` | Package init |
| `backend/routers/upload.py` | `POST /api/upload` — accept video, store, return ID |
| `backend/routers/detect.py` | `POST /api/detect` — run YOLO on frame, return bounding boxes |
| `backend/routers/analyze.py` | `POST /api/analyze`, `GET .../status`, `GET .../results` |
| `backend/routers/video.py` | `GET /api/video/{id}/{filename}` — serve video files |
| `backend/models/__init__.py` | Package init |
| `backend/models/schemas.py` | All Pydantic request/response models |
| `backend/services/__init__.py` | Package init |
| `backend/services/detection.py` | YOLO person detection wrapper |
| `backend/services/tracking.py` | Frame-to-frame person tracking via IoU |
| `backend/services/pose.py` | MediaPipe pose estimation wrapper |
| `backend/services/analysis.py` | Stats computation + annotated video rendering + orchestration |
| `backend/services/storage.py` | File storage helpers (paths, cleanup) |
| `backend/requirements.txt` | Python dependencies |
| `backend/.gitignore` | Ignore `storage/`, `__pycache__/`, `*.pyc` |
| `backend/tests/__init__.py` | Package init |
| `backend/tests/conftest.py` | Shared fixtures (test client, temp storage) |
| `backend/tests/test_upload.py` | Upload endpoint tests |
| `backend/tests/test_detect.py` | Detect endpoint tests |
| `backend/tests/test_analyze.py` | Analyze endpoint tests |
| `backend/tests/test_tracking.py` | IoU + tracking logic tests |
| `backend/tests/test_analysis_stats.py` | Stats computation tests |

### Frontend

| File | Responsibility |
|------|---------------|
| `frontend/src/main.tsx` | React entry point |
| `frontend/src/App.tsx` | Router setup (3 routes) |
| `frontend/src/types/index.ts` | Shared TypeScript types |
| `frontend/src/api/client.ts` | Typed fetch wrapper for all API endpoints |
| `frontend/src/pages/UploadPage.tsx` | Video upload screen |
| `frontend/src/pages/SelectPage.tsx` | Person selection screen |
| `frontend/src/pages/ResultsPage.tsx` | Stats + annotated video screen |
| `frontend/src/components/VideoUploader.tsx` | Drag-and-drop / tap file upload with progress |
| `frontend/src/components/PersonSelector.tsx` | Canvas overlay showing bounding boxes on frame |
| `frontend/src/components/ProcessingStatus.tsx` | Spinner + progress bar during analysis |
| `frontend/src/components/StatsPanel.tsx` | Metric cards (distance, speed, coverage, shots) |
| `frontend/src/components/StatChart.tsx` | Movement-over-time line chart |
| `frontend/src/components/VideoPlayer.tsx` | HTML5 video player for annotated video |
| `frontend/vite.config.ts` | Dev proxy to backend :8000 |
| `frontend/tailwind.config.js` | Tailwind configuration |
| `frontend/postcss.config.js` | PostCSS config for Tailwind |
| `frontend/index.html` | HTML shell |

---

### Task 1: Backend Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.gitignore`
- Create: `backend/main.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/models/__init__.py`
- Create: `backend/services/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9
opencv-python-headless>=4.10.0
ultralytics>=8.2.0
mediapipe>=0.10.14
numpy>=1.26.0
httpx>=0.27.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 2: Create .gitignore**

```
storage/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
venv/
.env
```

- [ ] **Step 3: Create main.py with empty app**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Badminton Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Create empty package __init__.py files**

Create empty `backend/routers/__init__.py`, `backend/models/__init__.py`, `backend/services/__init__.py`, `backend/tests/__init__.py`.

- [ ] **Step 5: Create test conftest.py**

```python
import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_storage(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("STORAGE_DIR", tmpdir)
    yield tmpdir
    shutil.rmtree(tmpdir)
```

- [ ] **Step 6: Install dependencies and verify**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 7: Run health check test to verify setup**

```bash
cd backend
source venv/bin/activate
python -c "from main import app; from fastapi.testclient import TestClient; c = TestClient(app); r = c.get('/api/health'); assert r.json() == {'status': 'ok'}; print('OK')"
```

Expected: prints `OK`

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project with FastAPI"
```

---

### Task 2: Pydantic Models + Storage Utility

**Files:**
- Create: `backend/models/schemas.py`
- Create: `backend/services/storage.py`

- [ ] **Step 1: Create Pydantic schemas**

```python
from pydantic import BaseModel


class UploadResponse(BaseModel):
    video_id: str
    filename: str


class BoundingBox(BaseModel):
    id: int
    x: float
    y: float
    width: float
    height: float
    confidence: float


class DetectRequest(BaseModel):
    video_id: str
    frame_number: int = 0


class DetectResponse(BaseModel):
    frame_image: str
    persons: list[BoundingBox]


class AnalyzeRequest(BaseModel):
    video_id: str
    person_bbox: BoundingBox


class AnalyzeStartResponse(BaseModel):
    analysis_id: str
    status: str = "processing"


class AnalysisStatus(BaseModel):
    status: str
    progress: float | None = None


class MovementPoint(BaseModel):
    time_sec: float
    distance: float


class AnalysisStats(BaseModel):
    total_distance_meters: float
    avg_speed_mps: float
    court_coverage_pct: float
    estimated_shot_count: int
    movement_over_time: list[MovementPoint]


class AnalysisResult(BaseModel):
    stats: AnalysisStats
    annotated_video_url: str
```

- [ ] **Step 2: Create storage utility**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/schemas.py backend/services/storage.py
git commit -m "feat: add Pydantic schemas and storage utility"
```

---

### Task 3: Upload Endpoint (TDD)

**Files:**
- Create: `backend/tests/test_upload.py`
- Create: `backend/routers/upload.py`
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_upload.py -v
```

Expected: FAIL — 404 because route doesn't exist yet.

- [ ] **Step 3: Implement upload router**

```python
import uuid

from fastapi import APIRouter, UploadFile

from models.schemas import UploadResponse
from services.storage import get_video_dir

router = APIRouter(prefix="/api")


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile):
    video_id = str(uuid.uuid4())
    video_dir = get_video_dir(video_id)
    file_path = video_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    return UploadResponse(video_id=video_id, filename=file.filename)
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/main.py` after the CORS middleware:

```python
from routers import upload

app.include_router(upload.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_upload.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/upload.py backend/tests/test_upload.py backend/main.py
git commit -m "feat: add video upload endpoint"
```

---

### Task 4: Video Serving Endpoint (TDD)

**Files:**
- Create: `backend/tests/test_video.py`
- Create: `backend/routers/video.py`
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_video.py -v
```

Expected: FAIL — 404 because route doesn't exist.

- [ ] **Step 3: Implement video router**

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.storage import get_video_path

router = APIRouter(prefix="/api")


@router.get("/video/{video_id}/{filename}")
async def serve_video(video_id: str, filename: str):
    path = get_video_path(video_id, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/main.py`:

```python
from routers import upload, video

app.include_router(video.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_video.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/video.py backend/tests/test_video.py backend/main.py
git commit -m "feat: add video serving endpoint"
```

---

### Task 5: Detection Service + Endpoint (TDD)

**Files:**
- Create: `backend/services/detection.py`
- Create: `backend/routers/detect.py`
- Create: `backend/tests/test_detect.py`
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Write failing test for detect endpoint**

```python
import base64
import io
from unittest.mock import patch, MagicMock

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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_detect.py -v
```

Expected: FAIL — route not found.

- [ ] **Step 3: Implement detection service**

```python
import cv2
import numpy as np
from ultralytics import YOLO

from models.schemas import BoundingBox

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
    return _model


def extract_frame(video_path: str, frame_number: int = 0) -> np.ndarray | None:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    return frame


def detect_persons(video_path: str, frame_number: int = 0) -> tuple[np.ndarray, list[BoundingBox]]:
    frame = extract_frame(video_path, frame_number)
    if frame is None:
        raise ValueError("Could not read frame from video")

    model = _get_model()
    results = model(frame, verbose=False)

    persons = []
    for i, box in enumerate(results[0].boxes):
        cls = int(box.cls[0])
        if cls != 0:  # 0 = person class in COCO
            continue
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        persons.append(BoundingBox(
            id=i,
            x=x1,
            y=y1,
            width=x2 - x1,
            height=y2 - y1,
            confidence=conf,
        ))

    return frame, persons
```

- [ ] **Step 4: Implement detect router**

```python
import base64
import glob

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException

from models.schemas import DetectRequest, DetectResponse
from services.detection import detect_persons
from services.storage import get_video_dir

router = APIRouter(prefix="/api")


@router.post("/detect", response_model=DetectResponse)
async def detect(request: DetectRequest):
    video_dir = get_video_dir(request.video_id)
    video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.avi")) + list(video_dir.glob("*.mov"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(video_files[0])
    frame, persons = detect_persons(video_path, request.frame_number)

    _, buffer = cv2.imencode(".jpg", frame)
    frame_b64 = base64.b64encode(buffer).decode("utf-8")

    return DetectResponse(frame_image=frame_b64, persons=persons)
```

- [ ] **Step 5: Register router in main.py**

Add to `backend/main.py`:

```python
from routers import upload, video, detect

app.include_router(detect.router)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_detect.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/services/detection.py backend/routers/detect.py backend/tests/test_detect.py backend/main.py
git commit -m "feat: add person detection service and endpoint"
```

---

### Task 6: Tracking Service (TDD)

**Files:**
- Create: `backend/services/tracking.py`
- Create: `backend/tests/test_tracking.py`

- [ ] **Step 1: Write the failing tests**

```python
from services.tracking import compute_iou, track_person_in_frame
from models.schemas import BoundingBox


def test_iou_identical_boxes():
    box = BoundingBox(id=0, x=0, y=0, width=100, height=100, confidence=0.9)
    assert compute_iou(box, box) == 1.0


def test_iou_no_overlap():
    box_a = BoundingBox(id=0, x=0, y=0, width=50, height=50, confidence=0.9)
    box_b = BoundingBox(id=1, x=100, y=100, width=50, height=50, confidence=0.9)
    assert compute_iou(box_a, box_b) == 0.0


def test_iou_partial_overlap():
    box_a = BoundingBox(id=0, x=0, y=0, width=100, height=100, confidence=0.9)
    box_b = BoundingBox(id=1, x=50, y=50, width=100, height=100, confidence=0.9)
    iou = compute_iou(box_a, box_b)
    assert 0.1 < iou < 0.3  # ~14.3% overlap


def test_track_person_match():
    prev_box = BoundingBox(id=0, x=10, y=10, width=50, height=100, confidence=0.9)
    candidates = [
        BoundingBox(id=0, x=200, y=200, width=50, height=100, confidence=0.8),
        BoundingBox(id=1, x=12, y=11, width=50, height=100, confidence=0.85),
    ]
    matched = track_person_in_frame(prev_box, candidates)
    assert matched is not None
    assert matched.x == 12


def test_track_person_no_match():
    prev_box = BoundingBox(id=0, x=10, y=10, width=50, height=100, confidence=0.9)
    candidates = [
        BoundingBox(id=0, x=500, y=500, width=50, height=100, confidence=0.8),
    ]
    matched = track_person_in_frame(prev_box, candidates, iou_threshold=0.3)
    assert matched is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_tracking.py -v
```

Expected: FAIL — import error.

- [ ] **Step 3: Implement tracking service**

```python
from models.schemas import BoundingBox


def compute_iou(box_a: BoundingBox, box_b: BoundingBox) -> float:
    x_left = max(box_a.x, box_b.x)
    y_top = max(box_a.y, box_b.y)
    x_right = min(box_a.x + box_a.width, box_b.x + box_b.width)
    y_bottom = min(box_a.y + box_a.height, box_b.y + box_b.height)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area_a = box_a.width * box_a.height
    area_b = box_b.width * box_b.height
    union = area_a + area_b - intersection

    if union == 0:
        return 0.0

    return intersection / union


def track_person_in_frame(
    prev_box: BoundingBox,
    candidates: list[BoundingBox],
    iou_threshold: float = 0.2,
) -> BoundingBox | None:
    best_match = None
    best_iou = 0.0

    for candidate in candidates:
        iou = compute_iou(prev_box, candidate)
        if iou > best_iou:
            best_iou = iou
            best_match = candidate

    if best_iou < iou_threshold:
        return None

    return best_match
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_tracking.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/tracking.py backend/tests/test_tracking.py
git commit -m "feat: add person tracking service with IoU matching"
```

---

### Task 7: Pose Estimation Service

**Files:**
- Create: `backend/services/pose.py`

- [ ] **Step 1: Implement pose service**

```python
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose


def estimate_pose(frame: np.ndarray, bbox: tuple[float, float, float, float]) -> list[dict] | None:
    """Run MediaPipe Pose on a cropped region of the frame.

    Args:
        frame: Full video frame (BGR).
        bbox: (x, y, width, height) of the person region.

    Returns:
        List of landmark dicts with keys: name, x, y, z, visibility.
        Coordinates are in full-frame pixel space. None if no pose detected.
    """
    x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

    # Add padding around the bounding box
    pad = int(max(w, h) * 0.1)
    fh, fw = frame.shape[:2]
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(fw, x + w + pad)
    y2 = min(fh, y + h + pad)

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    rgb_crop = crop[:, :, ::-1]  # BGR to RGB

    with mp_pose.Pose(static_image_mode=True, model_complexity=1) as pose:
        result = pose.process(rgb_crop)

    if not result.pose_landmarks:
        return None

    crop_h, crop_w = crop.shape[:2]
    landmarks = []
    for i, lm in enumerate(result.pose_landmarks.landmark):
        landmarks.append({
            "name": mp_pose.PoseLandmark(i).name,
            "x": x1 + lm.x * crop_w,
            "y": y1 + lm.y * crop_h,
            "z": lm.z,
            "visibility": lm.visibility,
        })

    return landmarks
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/pose.py
git commit -m "feat: add MediaPipe pose estimation service"
```

---

### Task 8: Analysis Stats Computation (TDD)

**Files:**
- Create: `backend/tests/test_analysis_stats.py`
- Create: `backend/services/analysis.py`

- [ ] **Step 1: Write failing tests for stats computation**

```python
from services.analysis import compute_stats


def test_compute_stats_basic():
    # Simulate 3 frames at 30fps with known positions
    frame_data = [
        {"time_sec": 0.0, "center_x": 100, "center_y": 200, "landmarks": None},
        {"time_sec": 0.033, "center_x": 110, "center_y": 200, "landmarks": None},
        {"time_sec": 0.066, "center_x": 120, "center_y": 200, "landmarks": None},
    ]
    frame_width = 640
    frame_height = 480

    stats = compute_stats(frame_data, frame_width, frame_height)

    assert stats.total_distance_meters > 0
    assert stats.avg_speed_mps > 0
    assert 0 <= stats.court_coverage_pct <= 100
    assert stats.estimated_shot_count >= 0
    assert len(stats.movement_over_time) > 0


def test_compute_stats_stationary():
    frame_data = [
        {"time_sec": 0.0, "center_x": 100, "center_y": 200, "landmarks": None},
        {"time_sec": 0.033, "center_x": 100, "center_y": 200, "landmarks": None},
    ]
    stats = compute_stats(frame_data, 640, 480)
    assert stats.total_distance_meters == 0.0
    assert stats.avg_speed_mps == 0.0


def test_shot_detection():
    # Simulate wrist acceleration spike
    base_landmarks = [{"name": "RIGHT_WRIST", "x": 100, "y": 100, "z": 0, "visibility": 0.9}]
    spike_landmarks = [{"name": "RIGHT_WRIST", "x": 200, "y": 100, "z": 0, "visibility": 0.9}]

    frame_data = [
        {"time_sec": 0.0, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
        {"time_sec": 0.033, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
        {"time_sec": 0.066, "center_x": 100, "center_y": 200, "landmarks": spike_landmarks},
        {"time_sec": 0.1, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
        {"time_sec": 0.133, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
    ]
    stats = compute_stats(frame_data, 640, 480)
    assert stats.estimated_shot_count >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_analysis_stats.py -v
```

Expected: FAIL — import error.

- [ ] **Step 3: Implement analysis service**

```python
import json
import math
from pathlib import Path

import cv2
import numpy as np

from models.schemas import AnalysisStats, MovementPoint, BoundingBox
from services.detection import detect_persons, extract_frame
from services.tracking import track_person_in_frame
from services.pose import estimate_pose

# Approximate court length in meters for distance normalization
COURT_LENGTH_M = 13.4
COURT_GRID_CELLS = 20


def compute_stats(
    frame_data: list[dict],
    frame_width: int,
    frame_height: int,
) -> AnalysisStats:
    if len(frame_data) < 2:
        return AnalysisStats(
            total_distance_meters=0,
            avg_speed_mps=0,
            court_coverage_pct=0,
            estimated_shot_count=0,
            movement_over_time=[],
        )

    # Pixel-to-meter scale: assume frame height ~ court length
    px_to_m = COURT_LENGTH_M / frame_height

    # Distance and movement over time
    total_distance_px = 0.0
    movement_over_time = []
    cumulative_distance = 0.0

    for i in range(1, len(frame_data)):
        dx = frame_data[i]["center_x"] - frame_data[i - 1]["center_x"]
        dy = frame_data[i]["center_y"] - frame_data[i - 1]["center_y"]
        dist = math.sqrt(dx * dx + dy * dy)
        total_distance_px += dist
        cumulative_distance += dist * px_to_m
        movement_over_time.append(MovementPoint(
            time_sec=round(frame_data[i]["time_sec"], 2),
            distance=round(cumulative_distance, 2),
        ))

    total_distance_m = total_distance_px * px_to_m
    total_time = frame_data[-1]["time_sec"] - frame_data[0]["time_sec"]
    avg_speed = total_distance_m / total_time if total_time > 0 else 0.0

    # Court coverage: divide frame into grid, count visited cells
    cell_w = frame_width / COURT_GRID_CELLS
    cell_h = frame_height / COURT_GRID_CELLS
    visited = set()
    for fd in frame_data:
        col = int(fd["center_x"] / cell_w) if cell_w > 0 else 0
        row = int(fd["center_y"] / cell_h) if cell_h > 0 else 0
        visited.add((row, col))
    total_cells = COURT_GRID_CELLS * COURT_GRID_CELLS
    coverage_pct = (len(visited) / total_cells) * 100

    # Shot detection: wrist acceleration spikes
    shot_count = _detect_shots(frame_data)

    return AnalysisStats(
        total_distance_meters=round(total_distance_m, 2),
        avg_speed_mps=round(avg_speed, 2),
        court_coverage_pct=round(coverage_pct, 1),
        estimated_shot_count=shot_count,
        movement_over_time=movement_over_time,
    )


def _detect_shots(frame_data: list[dict]) -> int:
    wrist_positions = []
    for fd in frame_data:
        lms = fd.get("landmarks")
        if lms is None:
            wrist_positions.append(None)
            continue
        wrist = None
        for lm in lms:
            if lm["name"] in ("RIGHT_WRIST", "LEFT_WRIST"):
                if wrist is None or lm["visibility"] > wrist["visibility"]:
                    wrist = lm
        wrist_positions.append(wrist)

    # Compute wrist speed between frames
    speeds = []
    for i in range(1, len(wrist_positions)):
        if wrist_positions[i] is None or wrist_positions[i - 1] is None:
            speeds.append(0.0)
            continue
        dx = wrist_positions[i]["x"] - wrist_positions[i - 1]["x"]
        dy = wrist_positions[i]["y"] - wrist_positions[i - 1]["y"]
        speeds.append(math.sqrt(dx * dx + dy * dy))

    if not speeds:
        return 0

    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    threshold = max(avg_speed * 3, 30)  # 3x average or at least 30px

    shot_count = 0
    cooldown = 0
    for s in speeds:
        if cooldown > 0:
            cooldown -= 1
            continue
        if s > threshold:
            shot_count += 1
            cooldown = 5  # Skip 5 frames after a shot to avoid double-counting

    return shot_count


def render_annotated_video(
    video_path: str,
    output_path: str,
    tracked_boxes: list[BoundingBox | None],
    all_landmarks: list[list[dict] | None],
    positions: list[tuple[float, float]],
) -> None:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    trail = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx < len(tracked_boxes) and tracked_boxes[frame_idx] is not None:
            box = tracked_boxes[frame_idx]
            # Draw bounding box
            x, y, w, h = int(box.x), int(box.y), int(box.width), int(box.height)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if frame_idx < len(positions):
            trail.append(positions[frame_idx])

        # Draw movement trail
        for i in range(1, len(trail)):
            pt1 = (int(trail[i - 1][0]), int(trail[i - 1][1]))
            pt2 = (int(trail[i][0]), int(trail[i][1]))
            cv2.line(frame, pt1, pt2, (255, 165, 0), 2)

        # Draw pose skeleton
        if frame_idx < len(all_landmarks) and all_landmarks[frame_idx] is not None:
            lms = all_landmarks[frame_idx]
            _draw_skeleton(frame, lms)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()


SKELETON_CONNECTIONS = [
    ("LEFT_SHOULDER", "RIGHT_SHOULDER"),
    ("LEFT_SHOULDER", "LEFT_ELBOW"),
    ("LEFT_ELBOW", "LEFT_WRIST"),
    ("RIGHT_SHOULDER", "RIGHT_ELBOW"),
    ("RIGHT_ELBOW", "RIGHT_WRIST"),
    ("LEFT_SHOULDER", "LEFT_HIP"),
    ("RIGHT_SHOULDER", "RIGHT_HIP"),
    ("LEFT_HIP", "RIGHT_HIP"),
    ("LEFT_HIP", "LEFT_KNEE"),
    ("LEFT_KNEE", "LEFT_ANKLE"),
    ("RIGHT_HIP", "RIGHT_KNEE"),
    ("RIGHT_KNEE", "RIGHT_ANKLE"),
]


def _draw_skeleton(frame: np.ndarray, landmarks: list[dict]) -> None:
    lm_map = {lm["name"]: lm for lm in landmarks}

    # Draw joints
    for lm in landmarks:
        if lm["visibility"] > 0.5:
            cv2.circle(frame, (int(lm["x"]), int(lm["y"])), 4, (0, 0, 255), -1)

    # Draw connections
    for name_a, name_b in SKELETON_CONNECTIONS:
        if name_a in lm_map and name_b in lm_map:
            a = lm_map[name_a]
            b = lm_map[name_b]
            if a["visibility"] > 0.5 and b["visibility"] > 0.5:
                pt1 = (int(a["x"]), int(a["y"]))
                pt2 = (int(b["x"]), int(b["y"]))
                cv2.line(frame, pt1, pt2, (0, 255, 255), 2)


def run_full_analysis(
    video_path: str,
    person_bbox: BoundingBox,
    analysis_dir: Path,
    progress_callback=None,
) -> dict:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    current_box = person_bbox
    frame_data = []
    tracked_boxes = []
    all_landmarks = []
    positions = []

    for frame_idx in range(total_frames):
        frame = extract_frame(video_path, frame_idx)
        if frame is None:
            tracked_boxes.append(None)
            all_landmarks.append(None)
            continue

        # Detect persons in this frame
        from services.detection import _get_model
        model = _get_model()
        results = model(frame, verbose=False)

        candidates = []
        for i, box in enumerate(results[0].boxes):
            cls = int(box.cls[0])
            if cls != 0:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            candidates.append(BoundingBox(
                id=i, x=x1, y=y1, width=x2 - x1, height=y2 - y1, confidence=conf,
            ))

        # Track the selected person
        matched = track_person_in_frame(current_box, candidates)
        if matched is not None:
            current_box = matched

        tracked_boxes.append(matched)

        # Center position
        if matched is not None:
            cx = matched.x + matched.width / 2
            cy = matched.y + matched.height / 2
        else:
            cx = current_box.x + current_box.width / 2
            cy = current_box.y + current_box.height / 2

        positions.append((cx, cy))

        # Pose estimation
        bbox_tuple = (current_box.x, current_box.y, current_box.width, current_box.height)
        landmarks = estimate_pose(frame, bbox_tuple)
        all_landmarks.append(landmarks)

        time_sec = frame_idx / fps if fps > 0 else 0
        frame_data.append({
            "time_sec": time_sec,
            "center_x": cx,
            "center_y": cy,
            "landmarks": landmarks,
        })

        if progress_callback and total_frames > 0:
            progress_callback(frame_idx / total_frames)

    # Compute stats
    stats = compute_stats(frame_data, frame_width, frame_height)

    # Render annotated video
    annotated_path = str(analysis_dir / "annotated.mp4")
    render_annotated_video(video_path, annotated_path, tracked_boxes, all_landmarks, positions)

    # Save stats
    stats_path = analysis_dir / "stats.json"
    stats_path.write_text(stats.model_dump_json())

    return {"stats": stats, "annotated_path": annotated_path}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_analysis_stats.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/analysis.py backend/tests/test_analysis_stats.py
git commit -m "feat: add analysis stats computation and video annotation"
```

---

### Task 9: Analysis Orchestration Endpoint (TDD)

**Files:**
- Create: `backend/routers/analyze.py`
- Create: `backend/tests/test_analyze.py`
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Write the failing tests**

```python
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from main import app
from services.storage import get_video_dir, get_analysis_dir

client = TestClient(app)


def test_start_analysis(temp_storage):
    video_id = "analyze-test"
    video_dir = get_video_dir(video_id)

    import cv2
    import numpy as np
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    video_path = str(video_dir / "test.mp4")
    writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (100, 100))
    writer.write(frame)
    writer.release()

    response = client.post(
        "/api/analyze",
        json={
            "video_id": video_id,
            "person_bbox": {
                "id": 0, "x": 10, "y": 10, "width": 50, "height": 80, "confidence": 0.9,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "processing"


def test_analysis_status_not_found():
    response = client.get("/api/analyze/nonexistent/status")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_analyze.py -v
```

Expected: FAIL — route not found.

- [ ] **Step 3: Implement analyze router**

```python
import uuid
from threading import Thread

from fastapi import APIRouter, HTTPException

from models.schemas import (
    AnalyzeRequest,
    AnalyzeStartResponse,
    AnalysisStatus,
    AnalysisResult,
    AnalysisStats,
)
from services.storage import get_video_dir, get_analysis_dir
from services.analysis import run_full_analysis

router = APIRouter(prefix="/api")

# In-memory analysis state (sufficient for baseline single-server app)
_analyses: dict[str, dict] = {}


@router.post("/analyze", response_model=AnalyzeStartResponse)
async def start_analysis(request: AnalyzeRequest):
    video_dir = get_video_dir(request.video_id)
    video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.avi")) + list(video_dir.glob("*.mov"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Video not found")

    analysis_id = str(uuid.uuid4())
    analysis_dir = get_analysis_dir(analysis_id)
    video_path = str(video_files[0])

    _analyses[analysis_id] = {
        "status": "processing",
        "progress": 0.0,
        "video_id": request.video_id,
    }

    def _run():
        try:
            def on_progress(p):
                _analyses[analysis_id]["progress"] = round(p * 100, 1)

            result = run_full_analysis(
                video_path, request.person_bbox, analysis_dir, progress_callback=on_progress,
            )
            _analyses[analysis_id]["status"] = "completed"
            _analyses[analysis_id]["progress"] = 100.0
            _analyses[analysis_id]["result"] = result
        except Exception as e:
            _analyses[analysis_id]["status"] = "failed"
            _analyses[analysis_id]["error"] = str(e)

    thread = Thread(target=_run, daemon=True)
    thread.start()

    return AnalyzeStartResponse(analysis_id=analysis_id, status="processing")


@router.get("/analyze/{analysis_id}/status", response_model=AnalysisStatus)
async def analysis_status(analysis_id: str):
    if analysis_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    entry = _analyses[analysis_id]
    return AnalysisStatus(status=entry["status"], progress=entry.get("progress"))


@router.get("/analyze/{analysis_id}/results", response_model=AnalysisResult)
async def analysis_results(analysis_id: str):
    if analysis_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    entry = _analyses[analysis_id]
    if entry["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not yet completed")

    result = entry["result"]
    video_id = entry["video_id"]
    annotated_url = f"/api/video/analyses/{analysis_id}/annotated.mp4"

    return AnalysisResult(
        stats=result["stats"],
        annotated_video_url=annotated_url,
    )
```

- [ ] **Step 4: Register router in main.py and add analyses video serving**

Update `backend/main.py` to its final form:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import upload, video, detect, analyze

app = FastAPI(title="Badminton Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(video.router)
app.include_router(detect.router)
app.include_router(analyze.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

Update `backend/routers/video.py` to also serve analysis files:

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.storage import get_video_path, get_analysis_dir

router = APIRouter(prefix="/api")


@router.get("/video/{video_id}/{filename}")
async def serve_video(video_id: str, filename: str):
    path = get_video_path(video_id, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/video/analyses/{analysis_id}/{filename}")
async def serve_analysis_video(analysis_id: str, filename: str):
    path = get_analysis_dir(analysis_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Annotated video not found")
    return FileResponse(path, media_type="video/mp4")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_analyze.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Run all backend tests**

```bash
cd backend && source venv/bin/activate && python -m pytest -v
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/analyze.py backend/routers/video.py backend/tests/test_analyze.py backend/main.py
git commit -m "feat: add analysis orchestration endpoint with background processing"
```

---

### Task 10: Frontend Project Scaffolding

**Files:**
- Create: `frontend/` (via Vite scaffold)
- Modify: `frontend/vite.config.ts` (add proxy)
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`

- [ ] **Step 1: Scaffold Vite + React + TypeScript project**

```bash
cd /path/to/badminton-analysis
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install
npm install react-router-dom recharts
npm install -D tailwindcss @tailwindcss/postcss postcss
```

- [ ] **Step 3: Configure Tailwind — create postcss.config.js**

```javascript
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

- [ ] **Step 4: Replace frontend/src/index.css with Tailwind imports**

```css
@import "tailwindcss";
```

- [ ] **Step 5: Configure Vite proxy — update vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 6: Clean up default Vite scaffolding**

Delete `frontend/src/App.css` and `frontend/src/assets/react.svg`. Replace `frontend/src/App.tsx` with:

```tsx
function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <h1 className="text-2xl font-bold p-4">Badminton Analysis</h1>
    </div>
  );
}

export default App;
```

- [ ] **Step 7: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173` — should show "Badminton Analysis" heading with dark background and Tailwind styling.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vite, React, TypeScript, Tailwind"
```

---

### Task 11: TypeScript Types + API Client

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Create shared types**

```typescript
export interface BoundingBox {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export interface UploadResponse {
  video_id: string;
  filename: string;
}

export interface DetectResponse {
  frame_image: string;
  persons: BoundingBox[];
}

export interface AnalyzeStartResponse {
  analysis_id: string;
  status: string;
}

export interface AnalysisStatus {
  status: "processing" | "completed" | "failed";
  progress?: number;
}

export interface MovementPoint {
  time_sec: number;
  distance: number;
}

export interface AnalysisStats {
  total_distance_meters: number;
  avg_speed_mps: number;
  court_coverage_pct: number;
  estimated_shot_count: number;
  movement_over_time: MovementPoint[];
}

export interface AnalysisResult {
  stats: AnalysisStats;
  annotated_video_url: string;
}
```

- [ ] **Step 2: Create API client**

```typescript
import type {
  UploadResponse,
  DetectResponse,
  AnalyzeStartResponse,
  AnalysisStatus,
  AnalysisResult,
  BoundingBox,
} from "../types";

const BASE = "/api";

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function detectPersons(
  videoId: string,
  frameNumber = 0
): Promise<DetectResponse> {
  const res = await fetch(`${BASE}/detect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_id: videoId, frame_number: frameNumber }),
  });
  if (!res.ok) throw new Error(`Detection failed: ${res.statusText}`);
  return res.json();
}

export async function startAnalysis(
  videoId: string,
  personBbox: BoundingBox
): Promise<AnalyzeStartResponse> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_id: videoId, person_bbox: personBbox }),
  });
  if (!res.ok) throw new Error(`Analysis start failed: ${res.statusText}`);
  return res.json();
}

export async function getAnalysisStatus(
  analysisId: string
): Promise<AnalysisStatus> {
  const res = await fetch(`${BASE}/analyze/${analysisId}/status`);
  if (!res.ok) throw new Error(`Status check failed: ${res.statusText}`);
  return res.json();
}

export async function getAnalysisResults(
  analysisId: string
): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analyze/${analysisId}/results`);
  if (!res.ok) throw new Error(`Results fetch failed: ${res.statusText}`);
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add TypeScript types and API client"
```

---

### Task 12: VideoUploader Component + UploadPage

**Files:**
- Create: `frontend/src/components/VideoUploader.tsx`
- Create: `frontend/src/pages/UploadPage.tsx`

- [ ] **Step 1: Create VideoUploader component**

```tsx
import { useCallback, useState, useRef } from "react";

interface VideoUploaderProps {
  onUploadComplete: (videoId: string) => void;
}

export default function VideoUploader({ onUploadComplete }: VideoUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.type.startsWith("video/")) {
        setError("Please select a video file");
        return;
      }
      setError(null);
      setProgress(0);

      const form = new FormData();
      form.append("file", file);

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/upload");

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          setProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          const data = JSON.parse(xhr.responseText);
          setProgress(100);
          onUploadComplete(data.video_id);
        } else {
          setError("Upload failed. Please try again.");
          setProgress(null);
        }
      };

      xhr.onerror = () => {
        setError("Upload failed. Please try again.");
        setProgress(null);
      };

      xhr.send(form);
    },
    [onUploadComplete]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="w-full max-w-lg mx-auto">
      <div
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors ${
          isDragging
            ? "border-blue-400 bg-blue-400/10"
            : "border-gray-600 hover:border-gray-400"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={onFileChange}
        />
        <div className="text-5xl mb-4">🏸</div>
        <p className="text-lg font-medium text-gray-300">
          Tap to select or drag a video
        </p>
        <p className="text-sm text-gray-500 mt-2">MP4, AVI, or MOV</p>
      </div>

      {progress !== null && (
        <div className="mt-6">
          <div className="w-full bg-gray-700 rounded-full h-3">
            <div
              className="bg-blue-500 h-3 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-400 mt-2 text-center">
            Uploading... {progress}%
          </p>
        </div>
      )}

      {error && (
        <p className="mt-4 text-red-400 text-center text-sm">{error}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create UploadPage**

```tsx
import { useNavigate } from "react-router-dom";
import VideoUploader from "../components/VideoUploader";

export default function UploadPage() {
  const navigate = useNavigate();

  const handleUploadComplete = (videoId: string) => {
    navigate(`/select/${videoId}`);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <header className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-center">Badminton Analysis</h1>
      </header>
      <main className="flex-1 flex flex-col items-center justify-center p-6">
        <h2 className="text-2xl font-semibold mb-8">Upload Your Video</h2>
        <VideoUploader onUploadComplete={handleUploadComplete} />
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/VideoUploader.tsx frontend/src/pages/UploadPage.tsx
git commit -m "feat: add video upload page with drag-and-drop"
```

---

### Task 13: PersonSelector Component + SelectPage

**Files:**
- Create: `frontend/src/components/PersonSelector.tsx`
- Create: `frontend/src/pages/SelectPage.tsx`

- [ ] **Step 1: Create PersonSelector component**

```tsx
import { useRef, useEffect, useCallback } from "react";
import type { BoundingBox } from "../types";

interface PersonSelectorProps {
  frameImage: string;
  persons: BoundingBox[];
  onSelect: (person: BoundingBox) => void;
}

export default function PersonSelector({
  frameImage,
  persons,
  onSelect,
}: PersonSelectorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scaleRef = useRef(1);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      // Scale to fit container width
      const containerWidth = container.clientWidth;
      const scale = containerWidth / img.width;
      scaleRef.current = scale;

      canvas.width = containerWidth;
      canvas.height = img.height * scale;

      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Draw bounding boxes
      persons.forEach((person, i) => {
        const x = person.x * scale;
        const y = person.y * scale;
        const w = person.width * scale;
        const h = person.height * scale;

        ctx.strokeStyle = "#22c55e";
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, w, h);

        // Label
        ctx.fillStyle = "#22c55e";
        ctx.font = "bold 14px sans-serif";
        ctx.fillText(`Person ${i + 1}`, x + 4, y - 6);
      });
    };
    img.src = `data:image/jpeg;base64,${frameImage}`;
  }, [frameImage, persons]);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const clickX = (e.clientX - rect.left);
      const clickY = (e.clientY - rect.top);
      const scale = scaleRef.current;

      // Find which person was clicked
      for (const person of persons) {
        const x = person.x * scale;
        const y = person.y * scale;
        const w = person.width * scale;
        const h = person.height * scale;

        if (
          clickX >= x &&
          clickX <= x + w &&
          clickY >= y &&
          clickY <= y + h
        ) {
          onSelect(person);
          return;
        }
      }
    },
    [persons, onSelect]
  );

  return (
    <div ref={containerRef} className="w-full max-w-2xl mx-auto">
      <canvas
        ref={canvasRef}
        className="w-full rounded-lg cursor-pointer"
        onClick={handleClick}
      />
      <p className="text-sm text-gray-400 mt-3 text-center">
        Tap on the person you want to analyze
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Create SelectPage**

```tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { BoundingBox } from "../types";
import { detectPersons, startAnalysis } from "../api/client";
import PersonSelector from "../components/PersonSelector";

export default function SelectPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();
  const [frameImage, setFrameImage] = useState<string | null>(null);
  const [persons, setPersons] = useState<BoundingBox[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!videoId) return;

    detectPersons(videoId)
      .then((data) => {
        setFrameImage(data.frame_image);
        setPersons(data.persons);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [videoId]);

  const handleSelect = async (person: BoundingBox) => {
    if (!videoId) return;
    try {
      const result = await startAnalysis(videoId, person);
      navigate(`/results/${result.analysis_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <header className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-center">Select Player</h1>
      </header>
      <main className="flex-1 flex flex-col items-center justify-center p-6">
        {loading && (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto" />
            <p className="mt-4 text-gray-400">Detecting players...</p>
          </div>
        )}

        {error && <p className="text-red-400">{error}</p>}

        {!loading && !error && frameImage && (
          <>
            {persons.length === 0 ? (
              <p className="text-gray-400">No persons detected in the video.</p>
            ) : (
              <PersonSelector
                frameImage={frameImage}
                persons={persons}
                onSelect={handleSelect}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PersonSelector.tsx frontend/src/pages/SelectPage.tsx
git commit -m "feat: add person selection page with bounding box overlay"
```

---

### Task 14: Results Page Components

**Files:**
- Create: `frontend/src/components/ProcessingStatus.tsx`
- Create: `frontend/src/components/StatsPanel.tsx`
- Create: `frontend/src/components/StatChart.tsx`
- Create: `frontend/src/components/VideoPlayer.tsx`

- [ ] **Step 1: Create ProcessingStatus component**

```tsx
interface ProcessingStatusProps {
  progress?: number;
}

export default function ProcessingStatus({ progress }: ProcessingStatusProps) {
  return (
    <div className="text-center py-12">
      <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-400 mx-auto" />
      <p className="mt-6 text-lg text-gray-300">Analyzing performance...</p>
      {progress !== undefined && progress !== null && (
        <div className="mt-4 w-64 mx-auto">
          <div className="w-full bg-gray-700 rounded-full h-3">
            <div
              className="bg-blue-500 h-3 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-400 mt-2">{Math.round(progress)}%</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create StatsPanel component**

```tsx
import type { AnalysisStats } from "../types";

interface StatsPanelProps {
  stats: AnalysisStats;
}

export default function StatsPanel({ stats }: StatsPanelProps) {
  const cards = [
    {
      label: "Distance",
      value: `${stats.total_distance_meters.toFixed(1)}m`,
      icon: "📏",
    },
    {
      label: "Avg Speed",
      value: `${stats.avg_speed_mps.toFixed(1)} m/s`,
      icon: "⚡",
    },
    {
      label: "Court Coverage",
      value: `${stats.court_coverage_pct.toFixed(0)}%`,
      icon: "🗺️",
    },
    {
      label: "Shots",
      value: `${stats.estimated_shot_count}`,
      icon: "🏸",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 w-full max-w-lg mx-auto">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-gray-800 rounded-xl p-4 text-center"
        >
          <div className="text-2xl mb-1">{card.icon}</div>
          <div className="text-2xl font-bold">{card.value}</div>
          <div className="text-sm text-gray-400 mt-1">{card.label}</div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create StatChart component**

```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { MovementPoint } from "../types";

interface StatChartProps {
  data: MovementPoint[];
}

export default function StatChart({ data }: StatChartProps) {
  return (
    <div className="w-full max-w-lg mx-auto bg-gray-800 rounded-xl p-4">
      <h3 className="text-sm font-medium text-gray-400 mb-3">
        Movement Over Time
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="time_sec"
            stroke="#9ca3af"
            fontSize={12}
            tickFormatter={(v) => `${v}s`}
          />
          <YAxis
            stroke="#9ca3af"
            fontSize={12}
            tickFormatter={(v) => `${v}m`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "8px",
            }}
            labelFormatter={(v) => `${v}s`}
            formatter={(v: number) => [`${v.toFixed(1)}m`, "Distance"]}
          />
          <Line
            type="monotone"
            dataKey="distance"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Create VideoPlayer component**

```tsx
interface VideoPlayerProps {
  src: string;
}

export default function VideoPlayer({ src }: VideoPlayerProps) {
  return (
    <div className="w-full max-w-lg mx-auto">
      <video
        className="w-full rounded-xl"
        controls
        playsInline
        src={src}
      >
        Your browser does not support video playback.
      </video>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ProcessingStatus.tsx frontend/src/components/StatsPanel.tsx frontend/src/components/StatChart.tsx frontend/src/components/VideoPlayer.tsx
git commit -m "feat: add results page components (stats, chart, video player)"
```

---

### Task 15: ResultsPage

**Files:**
- Create: `frontend/src/pages/ResultsPage.tsx`

- [ ] **Step 1: Create ResultsPage**

```tsx
import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { AnalysisResult } from "../types";
import { getAnalysisStatus, getAnalysisResults } from "../api/client";
import ProcessingStatus from "../components/ProcessingStatus";
import StatsPanel from "../components/StatsPanel";
import StatChart from "../components/StatChart";
import VideoPlayer from "../components/VideoPlayer";

export default function ResultsPage() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<string>("processing");
  const [progress, setProgress] = useState<number>(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (!analysisId) return;

    const poll = async () => {
      try {
        const s = await getAnalysisStatus(analysisId);
        setStatus(s.status);
        setProgress(s.progress ?? 0);

        if (s.status === "completed") {
          clearInterval(pollRef.current);
          const r = await getAnalysisResults(analysisId);
          setResult(r);
        } else if (s.status === "failed") {
          clearInterval(pollRef.current);
          setError("Analysis failed. Please try again.");
        }
      } catch (err) {
        clearInterval(pollRef.current);
        setError(err instanceof Error ? err.message : "Something went wrong");
      }
    };

    poll();
    pollRef.current = setInterval(poll, 2000);

    return () => clearInterval(pollRef.current);
  }, [analysisId]);

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <header className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-center">Analysis Results</h1>
      </header>
      <main className="flex-1 p-6 space-y-6 pb-24">
        {status === "processing" && <ProcessingStatus progress={progress} />}

        {error && (
          <div className="text-center">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {result && (
          <>
            <StatsPanel stats={result.stats} />
            <StatChart data={result.stats.movement_over_time} />
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3 text-center">
                Annotated Video
              </h3>
              <VideoPlayer src={result.annotated_video_url} />
            </div>
          </>
        )}
      </main>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-gray-900 border-t border-gray-800">
        <button
          onClick={() => navigate("/")}
          className="w-full max-w-lg mx-auto block bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-xl transition-colors"
        >
          Analyze Another Video
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ResultsPage.tsx
git commit -m "feat: add results page with polling, stats, chart, and video"
```

---

### Task 16: App Routing + Final Wiring

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Update App.tsx with routing**

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import SelectPage from "./pages/SelectPage";
import ResultsPage from "./pages/ResultsPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/select/:videoId" element={<SelectPage />} />
        <Route path="/results/:analysisId" element={<ResultsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 2: Clean up main.tsx**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 3: Verify frontend compiles**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx
git commit -m "feat: wire up routing for upload, select, and results pages"
```

---

### Task 17: End-to-End Smoke Test

- [ ] **Step 1: Start backend**

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend in another terminal**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: Manual smoke test**

1. Open `http://localhost:5173` on a phone or using browser device emulation
2. Upload a short badminton video
3. Verify person detection shows bounding boxes on the first frame
4. Tap a person to start analysis
5. Verify progress polling works and results display (stats + annotated video)

- [ ] **Step 4: Run all backend tests**

```bash
cd backend && source venv/bin/activate && python -m pytest -v
```

Expected: All tests pass.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete baseline badminton analysis web app"
```
