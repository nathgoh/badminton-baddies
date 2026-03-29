# Technology Stack

**Analysis Date:** 2026-03-29

## Languages

**Primary:**
- Python 3.12 (backend) - All server-side logic, ML inference, video processing
- TypeScript 5.x (frontend) - React SPA

**Secondary:**
- CSS - Tailwind utility classes via `frontend/src/index.css`

## Runtime

**Environment:**
- Python 3.12 (pinned in `backend/.venv/pyvenv.cfg`)
- Node.js (frontend dev tooling only; no server-side Node runtime)

**Package Manager:**
- Backend: `uv` 0.9.22 — `backend/uv.lock` present and committed
- Frontend: `npm` — `frontend/package-lock.json` present and committed

**Lockfiles:**
- `backend/uv.lock` — full dependency lock
- `frontend/package-lock.json` — full dependency lock

## Frameworks

**Core:**
- FastAPI 0.135.2 — HTTP API server (`backend/main.py`)
- Uvicorn 0.42.0 — ASGI server (with `standard` extras for production performance)
- Pydantic 2.12.5 — Data validation and serialisation (`backend/models/schemas.py`)
- React 18.2.0 — Frontend SPA (`frontend/src/main.tsx`)
- React Router DOM 6.8.0 — Client-side routing (`frontend/src/App.tsx`)

**Build/Dev:**
- Vite 8.0.3 — Frontend bundler and dev server (`frontend/vite.config.ts`)
- `@vitejs/plugin-react` 5.0.0 — React Fast Refresh for Vite

**Styling:**
- Tailwind CSS 3.3.0 — Utility-first CSS (`frontend/tailwind.config.js`)
- PostCSS 8.4.23 — Required by Tailwind (`frontend/`)

**Testing:**
- pytest 9.0.2 — Backend test runner (`backend/pyproject.toml`)
- pytest-asyncio 0.24.0 — Async test support (`asyncio_mode = "auto"`)
- httpx 0.28.1 — HTTP client for FastAPI test client
- ESLint 8.45.0 — Frontend linting

**Linting/Formatting:**
- ruff 0.15.8 — Python linter and formatter (`backend/pyproject.toml`, line-length 88, rules E/F/I)

## Key Dependencies

**Critical (ML/CV):**
- `ultralytics` 8.4.31 — YOLOv8 object detection; loads `yolov8n.pt` model at runtime (`backend/services/detection.py`)
- `opencv-python-headless` 4.13.0.92 — Video I/O and frame processing (`backend/services/analysis.py`, `backend/services/detection.py`)
- `mediapipe` 0.10.33 — Pose estimation (imported in `backend/pyproject.toml`; actual usage stubbed in `backend/services/pose.py`)
- `numpy` 2.4.3 — Numerical operations throughout backend services
- `torch` 2.11.0 — PyTorch; pulled in as transitive dependency by ultralytics
- `cuda-toolkit` 13.0.2 / `cuda-bindings` 13.2.0 — GPU acceleration (transitive via torch/ultralytics)

**Frontend:**
- `recharts` 2.5.0 — Chart/data visualisation (`frontend/src/pages/ResultsPage.tsx`)
- `lucide-react` 0.263.1 — Icon set
- `react-dom` 18.2.0 — DOM rendering

**Infrastructure:**
- `python-multipart` 0.0.9 — Multipart form upload support for FastAPI (`/api/upload`)

## Configuration

**Environment:**
- Single optional env var: `STORAGE_DIR` — overrides where uploaded videos and analyses are stored
  - Default: `backend/services/../storage` (i.e., `backend/storage/`)
  - Set in `backend/services/storage.py`
- No `.env` file detected; no secrets required for local development

**Build:**
- Backend build config: `backend/pyproject.toml` (setuptools, requires-python ≥ 3.12)
- Frontend build config: `frontend/vite.config.ts`, `frontend/tsconfig.json`
- TypeScript target: ES2020, strict mode enabled, `noUnusedLocals`/`noUnusedParameters` enforced

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js (any recent LTS)
- `uv` for Python dependency management
- ML model file `yolov8n.pt` auto-downloaded by ultralytics on first run
- GPU optional (CUDA packages present but CPU inference works)

**Production:**
- No deployment configuration detected (no Dockerfile, no CI config, no cloud platform config)
- Backend: `uvicorn main:app --reload --host 0.0.0.0 --port 8000` (per `Makefile`)
- Frontend: Vite static build served separately or via reverse proxy
- Vite dev proxy forwards `/api/*` to `http://localhost:8000` (`frontend/vite.config.ts`)
- CORS configured to allow `http://localhost:5173` only (`backend/main.py`)

---

*Stack analysis: 2026-03-29*
