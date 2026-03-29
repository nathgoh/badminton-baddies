# External Integrations

**Analysis Date:** 2026-03-29

## APIs & External Services

**ML Model Registry:**
- Ultralytics model hub — `yolov8n.pt` is fetched automatically on first call to `_get_model()` in `backend/services/detection.py` if not present locally
  - SDK/Client: `ultralytics` 8.4.31
  - Auth: None (public model weights)
  - No persistent external dependency once model file is cached

**No other external APIs or third-party services are integrated.** All processing is local.

## Data Storage

**Databases:**
- None. No SQL or NoSQL database is used.
- Analysis job state is held entirely in-memory via `_analysis_status` dict in `backend/routers/analyze.py` (lost on server restart).

**File Storage:**
- Local filesystem only via `LocalStorageBackend` in `backend/services/storage.py`
- Storage root: `backend/storage/` by default, overridable via `STORAGE_DIR` env var
- Directory layout at runtime:
  - `storage/uploads/<upload_id>/` — in-progress tus uploads (data + meta.json)
  - `storage/<video_id>/` — finalized video files
  - `storage/analyses/<analysis_id>/` — annotated output videos

**Caching:**
- None. No Redis, Memcached, or other cache layer.

## Authentication & Identity

**Auth Provider:**
- None. No authentication or authorization is implemented.
- All API endpoints are publicly accessible.

## Upload Protocol

**tus Resumable Upload (server-side):**
- Protocol: tus 1.0.0 implemented from scratch
- Endpoints: `OPTIONS /api/tus`, `POST /api/tus`, `HEAD /api/tus/{id}`, `PATCH /api/tus/{id}`
- Implementation: `backend/routers/tus.py`
- Max upload size: 10 GB
- Extensions supported: `creation`
- Client-side tus support: Not present in frontend; `frontend/src/api/client.ts` uses standard `FormData` POST to `/api/upload` instead

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Datadog, or similar service.

**Logs:**
- Standard Python `logging` module used in `backend/routers/analyze.py`
- `logger.exception("Analysis %s failed", analysis_id)` captures tracebacks on analysis failure
- No structured logging or log aggregation configured

## CI/CD & Deployment

**Hosting:**
- Not configured. No Dockerfile, docker-compose, or cloud platform manifests.

**CI Pipeline:**
- Not configured. No `.github/workflows/`, `.circleci/`, or similar.

## Environment Configuration

**Required env vars:**
- None required for basic operation

**Optional env vars:**
- `STORAGE_DIR` — Override the local storage base directory (default: `backend/storage/`)
  - Used in: `backend/services/storage.py`

**Secrets location:**
- No secrets required. No `.env` file detected.

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Internal API Surface (Frontend → Backend)

The frontend `frontend/src/api/client.ts` communicates exclusively with the backend via these REST endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/upload` | Multipart video upload (legacy, non-resumable) |
| OPTIONS | `/api/tus` | tus capability negotiation |
| POST | `/api/tus` | tus upload creation |
| HEAD | `/api/tus/{id}` | tus offset query |
| PATCH | `/api/tus/{id}` | tus chunk upload |
| POST | `/api/detect` | Person detection on a video frame |
| POST | `/api/analyze` | Start async analysis job |
| GET | `/api/analyze/{id}/status` | Poll analysis progress |
| GET | `/api/analyze/{id}/results` | Fetch analysis results |
| GET | `/api/video/{video_id}/{filename}` | Stream original video |
| GET | `/api/video/analyses/{analysis_id}/{filename}` | Stream annotated output video |
| GET | `/api/health` | Health check |

All requests proxied through Vite dev server (`/api` → `http://localhost:8000`) in development.

---

*Integration audit: 2026-03-29*
