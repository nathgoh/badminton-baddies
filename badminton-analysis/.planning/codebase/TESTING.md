# Testing Patterns

**Analysis Date:** 2026-03-29

## Test Framework

**Runner:**
- pytest >= 8.3.0
- Config: `backend/setup.cfg` (also mirrored in `backend/pyproject.toml`)

**Async Support:**
- pytest-asyncio >= 0.24.0
- `asyncio_mode = auto` (set in both `backend/setup.cfg` and `backend/pyproject.toml`) — all async tests run automatically without `@pytest.mark.asyncio`

**HTTP Client:**
- httpx >= 0.27.0 (required by FastAPI TestClient)
- `fastapi.testclient.TestClient` used for all API-level tests

**Assertion Library:**
- Standard Python `assert` statements only — no third-party assertion library

**Run Commands:**
```bash
cd backend && uv run pytest tests/          # Run all tests (from project root via Makefile)
make test                                   # Alias via Makefile
uv run pytest tests/ -v                    # Verbose output
uv run pytest tests/test_tus.py            # Run single test file
```

## Test File Organization

**Location:** All tests live in `backend/tests/` — separate from source, not co-located.

**Naming:** Files follow `test_<feature>.py` pattern.

**Structure:**
```
backend/tests/
├── conftest.py              # Shared fixtures (client, temp_storage)
├── __init__.py
├── test_analysis_stats.py   # Unit tests: services/analysis.py compute_stats()
├── test_detect.py           # Integration tests: POST /api/detect with mocking
├── test_storage.py          # Unit tests: services/storage.LocalStorageBackend
├── test_tracking.py         # Unit tests: services/tracking.py pure functions
├── test_tus.py              # Integration tests: tus resumable upload protocol endpoints
├── test_upload.py           # Integration tests: POST /api/upload endpoint
└── test_video.py            # Integration tests: GET /api/video/* endpoints
```

## Test Structure

**Function-based tests only** — no test classes are used anywhere.

**Suite Organization:**
```python
# Fixtures defined at module scope or in conftest.py
@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(base_dir=str(tmp_path))

@pytest.fixture
def client(storage):
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# Tests receive fixtures as parameters
def test_create_upload_stores_meta(storage):
    storage.create_upload("abc", 100, "video.mp4")
    meta = storage.get_upload_meta("abc")
    assert meta["upload_id"] == "abc"
```

**Naming Pattern:** `test_<what>_<condition>` — e.g., `test_patch_offset_mismatch_returns_409`, `test_finalize_raises_when_upload_incomplete`, `test_iou_no_overlap`.

## Mocking

**Framework:** `unittest.mock.patch` (standard library) — used in `backend/tests/test_detect.py`.

**Pattern:**
```python
from unittest.mock import patch

with patch("routers.detect.detect_persons") as mock_detect:
    mock_detect.return_value = (fake_frame, fake_boxes)
    response = client.post("/api/detect", json={...})
```

Mocking targets use the **import path in the consuming module** (`routers.detect.detect_persons`), not the defining module.

**What to Mock:**
- Heavy ML/CV inference functions (`detect_persons` from YOLO/MediaPipe) to avoid loading models in tests
- Any external I/O not controlled by the `LocalStorageBackend` fixture

**What NOT to Mock:**
- `LocalStorageBackend` itself — use `tmp_path` fixture to instantiate real storage against a temp directory
- FastAPI routing and middleware — use `TestClient` for real request/response cycles

## Dependency Injection Override Pattern

FastAPI's `app.dependency_overrides` is the primary pattern for injecting test doubles into API tests:

```python
@pytest.fixture
def client(storage):
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()   # Always clean up after each test
```

This pattern appears in `test_tus.py`, `test_video.py`, and `test_detect.py`. The `client` fixture in `conftest.py` does NOT use this pattern (it creates a plain `TestClient(app)` without storage override) — per-module fixtures with DI override are preferred for tests that need controlled storage.

## Fixtures and Factories

**Shared fixtures (`backend/tests/conftest.py`):**
```python
@pytest.fixture
def client():
    return TestClient(app)       # Plain client, no storage override

@pytest.fixture
def temp_storage(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("STORAGE_DIR", tmpdir)
    yield tmpdir
    shutil.rmtree(tmpdir)        # Manual cleanup via shutil
```

**Per-module fixtures:** Most API test files redefine `storage` and `client` locally (using `tmp_path` from pytest, not `temp_storage` from conftest) to wire storage into the dependency override.

**Test data:** Inline — no fixture factories or data files. Fake binary content is created inline:
```python
fake_video = io.BytesIO(b"fake video content")
data = b"hello world"
frame = np.zeros((100, 100, 3), dtype=np.uint8)   # minimal OpenCV frame
```

For real video file creation (OpenCV requires a valid container), `cv2.VideoWriter` is used inline in `test_detect.py`.

## Coverage

**Requirements:** No coverage threshold enforced — no `pytest-cov` dependency, no `--cov` flags configured.

**Coverage command:** Not configured. Add manually if needed:
```bash
uv add --dev pytest-cov
uv run pytest tests/ --cov=. --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- `test_storage.py` — tests `LocalStorageBackend` methods directly against `tmp_path`
- `test_tracking.py` — tests pure functions `compute_iou` and `track_person_in_frame` with `BoundingBox` model instances
- `test_analysis_stats.py` — tests `compute_stats` with inline frame data dicts

**Integration Tests:**
- `test_tus.py` — full tus protocol flow: OPTIONS/POST/HEAD/PATCH via `TestClient` with real `LocalStorageBackend`
- `test_video.py` — GET video file serving endpoints
- `test_detect.py` — POST /api/detect with ML function mocked, real video file, real storage
- `test_upload.py` — POST /api/upload multipart form upload

**E2E Tests:** Not used.

## Common Patterns

**Error/exception testing:**
```python
with pytest.raises(FileNotFoundError):
    storage.get_upload_meta("nonexistent")

with pytest.raises(ValueError, match="incomplete"):
    storage.finalize_upload("abc")
```

**HTTP error status assertion (inline, no helper):**
```python
assert response.status_code == 404
assert client.head("/api/tus/nonexistent", headers={"Tus-Resumable": "1.0.0"}).status_code == 404
```

**Multi-step flow tests (stateful protocol testing):**
```python
# Create → inspect state → mutate → assert final state
post = client.post("/api/tus", headers={...})
upload_id = post.headers["location"].split("/")[-1]
head = client.head(f"/api/tus/{upload_id}", headers={"Tus-Resumable": "1.0.0"})
assert head.headers["upload-offset"] == "5"
```

**Range assertions for computed values:**
```python
assert 0.1 < iou < 0.3          # floating point IoU range
assert 0 <= stats.court_coverage_pct <= 100
```

---

*Testing analysis: 2026-03-29*
