# Coding Conventions

**Analysis Date:** 2026-03-29

## Naming Patterns

**Files:**
- Modules use `snake_case`: `storage.py`, `detect.py`, `analyze.py`, `test_tus.py`
- Test files are prefixed `test_`: `test_storage.py`, `test_tus.py`, `test_tracking.py`
- Private helpers are prefixed with underscore: `_run_analysis`, `_check_tus_version`, `_detect_shots`, `_draw_skeleton`

**Functions:**
- Public functions use `snake_case`: `compute_stats`, `detect_persons`, `estimate_pose`, `track_person_in_frame`
- Private/internal functions prefixed with `_`: `_get_model`, `_uploads_dir`, `_update_progress`
- FastAPI route handlers named after HTTP verb + resource: `tus_create`, `tus_head`, `tus_patch`, `serve_video`, `start_analysis`

**Variables:**
- `snake_case` throughout: `upload_id`, `video_dir`, `frame_count`, `best_iou`
- Module-level constants use `UPPER_SNAKE_CASE`: `TUS_VERSION`, `TUS_MAX_SIZE`, `COURT_LENGTH_M`, `COURT_GRID_CELLS`

**Types / Classes:**
- Pydantic models use `PascalCase`: `BoundingBox`, `AnalysisStats`, `AnalyzeRequest`, `StorageBackend`
- Protocol types named by role, not implementation: `StorageBackend` (not `IStorageBackend`)

## Code Style

**Formatting:**
- Tool: `ruff` (configured in `backend/pyproject.toml`)
- Line length: 88 characters
- Target Python version: 3.12

**Linting:**
- Ruff rule sets: `E` (pycodestyle), `F` (pyflakes), `I` (isort)
- Import sorting enforced via ruff's `I` ruleset

## Import Organization

**Order (enforced by ruff isort):**
1. Standard library (`import os`, `import json`, `import uuid`)
2. Third-party packages (`from fastapi import ...`, `import cv2`, `import numpy as np`)
3. Local modules (`from models.schemas import ...`, `from services.storage import ...`)

**Pattern:**
- Standard library imports grouped at top
- Blank line separating each group
- Local imports use relative-style module paths from `backend/` root (e.g., `from services.storage import get_storage`)

**Example from `backend/routers/detect.py`:**
```python
import base64

import cv2
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import DetectRequest, DetectResponse
from services.detection import detect_persons
from services.storage import StorageBackend, get_storage
```

## Error Handling

**Router layer:**
- All errors surfaced as `HTTPException` with explicit `status_code` and `detail` string
- Service-layer exceptions (`FileNotFoundError`, `ValueError`) are caught in routers and re-raised as `HTTPException`
- Example from `backend/routers/tus.py`:
```python
try:
    meta = storage.get_upload_meta(upload_id)
except FileNotFoundError:
    raise HTTPException(status_code=404, detail="Upload not found")
```

**Service layer:**
- Services raise standard Python exceptions (`FileNotFoundError`, `ValueError`) — never `HTTPException`
- Example from `backend/services/storage.py`:
```python
raise FileNotFoundError(f"Upload {upload_id} not found")
raise ValueError(f"Upload incomplete: {meta['offset']}/{meta['total_size']} bytes written")
```

**Background jobs:**
- Background thread exceptions are caught with a bare `except Exception:` and logged with `logger.exception()`
- Job status is set to `"failed"` on exception; no re-raise
- Example from `backend/routers/analyze.py`:
```python
except Exception:
    logger.exception("Analysis %s failed", analysis_id)
    with _status_lock:
        job = _analysis_status.get(analysis_id)
        if job:
            job.status = "failed"
```

## Logging

**Framework:** Python standard `logging` module

**Setup:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Pattern:**
- Logger defined at module level as `logger = logging.getLogger(__name__)`
- Currently only used in `backend/routers/analyze.py` for background job failure
- Use `logger.exception()` to capture full tracebacks in exception handlers (not `logger.error()`)

## Function Design

**Size:** Functions are generally short and single-purpose. Service functions are pure logic; router functions handle HTTP concerns only.

**Parameters:** Typed throughout using Python type hints. Union types use `X | Y` syntax (Python 3.10+ style), not `Optional[X]` or `Union[X, Y]`.

**Return Values:**
- Functions always annotated with return type
- `None` returned explicitly when no match found (e.g., `track_person_in_frame` returns `BoundingBox | None`)
- Pydantic models used for all structured return values from routes

**Example from `backend/services/tracking.py`:**
```python
def track_person_in_frame(
    prev_box: BoundingBox,
    candidates: list[BoundingBox],
    iou_threshold: float = 0.2,
) -> BoundingBox | None:
```

## Module Design

**Exports:** No explicit `__all__` declarations. Public API is implicit (underscore-prefixed names are private).

**`__init__.py` files:** Present in `routers/`, `models/`, `services/`, `tests/` — content is empty (used to mark packages only).

**Dependency Injection:**
- FastAPI `Depends()` is used for storage injection across all routers
- The `StorageBackend` Protocol defines the DI interface
- The dependency factory function is `get_storage()` in `backend/services/storage.py`
- Override pattern for tests: `app.dependency_overrides[get_storage] = lambda: storage`

**Pydantic Models:**
- All request/response schemas live in `backend/models/schemas.py`
- All models inherit from `pydantic.BaseModel`
- Fields use Python primitive types and `list[T]` syntax (not `List[T]`)

## Comments

**When to Comment:**
- Inline comments explain non-obvious logic: `# 0 = person class in COCO`, `# atomic on POSIX`
- Section dividers used for backwards-compat shims: `# --- Backwards-compat shims ---`
- Algorithm notes inline: `# Skip 5 frames after a shot to avoid double-counting`

**Docstrings:**
- Used selectively on non-trivial functions with parameters that need explanation
- Google-style format with `Args:` and `Returns:` sections
- Example from `backend/services/pose.py`:
```python
def estimate_pose(frame: np.ndarray, bbox: tuple[float, float, float, float]) -> list[dict] | None:
    """Placeholder pose estimation function.

    Args:
        frame: Full video frame (BGR).
        bbox: (x, y, width, height) of the person region.

    Returns:
        None for now - pose estimation requires additional model setup.
    """
```

---

*Convention analysis: 2026-03-29*
