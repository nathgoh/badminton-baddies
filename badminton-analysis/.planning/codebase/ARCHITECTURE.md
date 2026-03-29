# Architecture

**Analysis Date:** 2026-03-29

## Pattern Overview

**Overall:** Client-Server SPA with async background processing

**Key Characteristics:**
- Decoupled React frontend (Vite/TypeScript) communicates with a FastAPI backend over REST
- Backend uses a layered architecture: routers → services → models
- Long-running analysis work is offloaded to a `ThreadPoolExecutor`; clients poll for status
- File storage is abstracted behind a `StorageBackend` Protocol, with a `LocalStorageBackend` implementation
- All domain models are Pydantic schemas shared across layers

## Layers

**Routing Layer:**
- Purpose: HTTP request handling, input validation, response shaping
- Location: `backend/routers/`
- Contains: `upload.py`, `tus.py`, `video.py`, `detect.py`, `analyze.py`
- Depends on: services layer, models/schemas
- Used by: FastAPI app (`backend/main.py`)

**Service Layer:**
- Purpose: Domain logic — CV processing, storage operations, statistics
- Location: `backend/services/`
- Contains: `storage.py`, `detection.py`, `pose.py`, `tracking.py`, `analysis.py`
- Depends on: models/schemas, external libraries (OpenCV, Ultralytics, MediaPipe)
- Used by: routers layer

**Models Layer:**
- Purpose: Shared data contracts (request/response shapes)
- Location: `backend/models/schemas.py`
- Contains: Pydantic models for all API contracts
- Depends on: nothing (pure Pydantic)
- Used by: routers and services

**Frontend:**
- Purpose: User interface — upload, player selection, results display
- Location: `frontend/src/`
- Contains: pages, components, API client, TypeScript types
- Depends on: backend REST API via `fetch`
- Used by: end users via browser

## Data Flow

**Upload Flow (simple):**

1. User drops a video in `VideoUploader.tsx`
2. `POST /api/upload` handled by `backend/routers/upload.py`
3. `services/storage.get_video_dir(video_id)` creates UUID-named directory under `backend/storage/`
4. File saved to `backend/storage/{video_id}/{filename}`
5. Returns `video_id` → frontend navigates to `/select/{videoId}`

**Upload Flow (tus resumable):**

1. Client sends `OPTIONS /api/tus` to discover capabilities
2. Client sends `POST /api/tus` with `Upload-Length` and `Upload-Metadata` headers
3. `StorageBackend.create_upload()` pre-allocates a sparse file and writes `meta.json`
4. Client sends `PATCH /api/tus/{upload_id}` chunks; `write_chunk()` updates offset atomically
5. When `new_offset == total_size`, `finalize_upload()` moves data file to video directory
6. Response includes `X-Video-Id` header with the finalized `upload_id`

**Detection Flow:**

1. Frontend navigates to `/select/{videoId}`, triggers `POST /api/detect`
2. `detect.py` router calls `services/detection.detect_persons(video_path, frame_number)`
3. YOLOv8n model runs inference; person bounding boxes returned
4. Frame encoded as base64 JPEG, returned to frontend with bounding box list
5. User clicks a person bounding box overlay; selected `BoundingBox` stored in state

**Analysis Flow:**

1. `POST /api/analyze` creates an `analysis_id`, stores `AnalysisJob` in `_analysis_status` dict
2. `_executor.submit(_run_analysis, ...)` offloads work to `ThreadPoolExecutor(max_workers=2)`
3. Background job iterates frames (every 2nd frame, up to 300), running detection + tracking + pose
4. `services/tracking.track_person_in_frame()` uses IoU to follow selected player across frames
5. `services/pose.estimate_pose()` returns per-frame landmarks (currently a stub returning `None`)
6. `services/analysis.compute_stats()` calculates distance, speed, court coverage, shot count
7. `services/analysis.render_annotated_video()` writes annotated MP4 to `backend/storage/analyses/{analysis_id}/`
8. Frontend polls `GET /api/analyze/{analysis_id}/status` every 2 seconds
9. On `completed`, frontend fetches `GET /api/analyze/{analysis_id}/results`

**State Management (Frontend):**
- Local React `useState` per page; no global state store
- Analysis polling implemented via recursive `setTimeout` in `ResultsPage.tsx`
- Navigation state carried via URL params (`/results/:videoId?analysis_id=...`)

## Key Abstractions

**StorageBackend Protocol:**
- Purpose: Interface for all file I/O, enabling testability via monkeypatching
- Definition: `backend/services/storage.py` — `class StorageBackend(Protocol)`
- Methods: `create_upload`, `get_upload_meta`, `write_chunk`, `finalize_upload`, `get_video_dir`, `get_video_path`, `get_analysis_dir`
- Implementation: `LocalStorageBackend` in `backend/services/storage.py`
- Injected via FastAPI `Depends(get_storage)` in all routers except `upload.py` (uses legacy shim)

**BoundingBox:**
- Purpose: Core data structure passed from detection → tracking → analysis
- Definition: `backend/models/schemas.py` — also mirrored in `frontend/src/types/index.ts`
- Contains: `id`, `x`, `y`, `width`, `height`, `confidence`

**AnalysisJob (in-memory):**
- Purpose: Tracks background job status (progress, result, failure)
- Definition: `backend/routers/analyze.py` — `class AnalysisJob(BaseModel)`
- Storage: `_analysis_status: dict[str, AnalysisJob]` (process-local, not persisted)
- Thread safety: `_status_lock: Lock()` guards all reads/writes

**ApiClient:**
- Purpose: Single entry point for all frontend HTTP calls
- Definition: `frontend/src/api/client.ts` — `class ApiClient`, exported as singleton `apiClient`

## Entry Points

**Backend:**
- Location: `backend/main.py`
- Triggers: `uvicorn main:app` (port 8000 in development)
- Responsibilities: Creates FastAPI app, registers CORS middleware, mounts all routers

**Frontend:**
- Location: `frontend/src/main.tsx`
- Triggers: Vite dev server (`npm run dev`, port 5173); browser loads bundle
- Responsibilities: Mounts React app into DOM, wraps with `BrowserRouter`

**Frontend Routes:**
- `/` → `UploadPage` — video upload entry
- `/select/:videoId` → `SelectPage` — YOLOv8 detection + player selection
- `/results/:videoId?analysis_id=...` → `ResultsPage` — polling + stats display

## Error Handling

**Strategy:** Exceptions surface as HTTP errors in routers; background jobs catch all exceptions and set `status = "failed"`

**Patterns:**
- Routers raise `HTTPException` with appropriate status codes (404, 400, 409, 412, 413, 415)
- Background analysis job wraps entire body in `try/except Exception`, logs via `logger.exception()`, marks job as failed
- Frontend catches API errors with `try/catch`, stores message in `error` state, renders error UI
- `StorageBackend` raises `FileNotFoundError` for missing uploads; routers translate to 404

## Cross-Cutting Concerns

**Logging:** Python `logging` module; `logger = logging.getLogger(__name__)` in `backend/routers/analyze.py`. No structured logging configured.

**Validation:** Pydantic models on all request/response bodies via FastAPI. Frontend types in `frontend/src/types/index.ts` mirror backend schemas manually.

**Authentication:** None implemented. All endpoints are publicly accessible.

**CORS:** Configured in `backend/main.py` to allow `http://localhost:5173` only. Production origins not configured.

**Concurrency:** Analysis jobs run in `ThreadPoolExecutor(max_workers=2)`. Status dict protected by `threading.Lock`. In-memory only — restarting the server loses all job state.

---

*Architecture analysis: 2026-03-29*
