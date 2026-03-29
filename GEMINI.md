# Badminton Baddies (Badminton Video Analysis)

## Project Overview

**Badminton Video Analysis** is a web application designed to analyze badminton player performance from uploaded videos using AI-powered computer vision. 

The project is structured as a monorepo consisting of:
*   **Backend (`badminton-analysis/backend`)**: A REST API built with **FastAPI** (Python 3.12+). It handles video processing using **OpenCV**, person detection using **Ultralytics YOLOv8**, and pose estimation using **MediaPipe**. It also features a TUS-protocol implementation for handling large, resumable video uploads via a `StorageBackend` abstraction.
*   **Frontend (`badminton-analysis/frontend`)**: A mobile-first Single Page Application (SPA) built with **React 18**, **TypeScript**, **Vite**, and **Tailwind CSS**.
*   **Planning & Documentation**: Extensive architectural specs, design documents, and roadmaps are tracked in the `badminton-analysis/.planning/` and `badminton-analysis/docs/superpowers/` directories.

## Building and Running

### Prerequisites
*   Node.js 20+
*   Python 3.10+ (3.12+ recommended)
*   [uv](https://github.com/astral-sh/uv) (recommended Python package manager)

### Backend

Navigate to the backend directory:
```bash
cd badminton-analysis/backend
```

**Install dependencies (using Make/UV):**
```bash
make install
# or
uv sync
```

**Run the API Server:**
```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*(The API runs on port 8000 and serves as the target for frontend proxies).*

**Run Tests:**
```bash
make test
# or
python -m pytest tests/ -v
```

### Frontend

Navigate to the frontend directory:
```bash
cd badminton-analysis/frontend
```

**Install dependencies:**
```bash
npm install
```

**Run the Dev Server:**
```bash
npm run dev
```
*(The frontend runs on `http://localhost:5173` and proxies `/api` requests to the backend).*

## Development Conventions & Architecture

*   **Python Code Quality**: The backend strictly uses **Ruff** for linting and formatting. Run `make lint` and `make format` to ensure compliance.
*   **Frontend Types**: Backend Python schemas (Pydantic) are manually mirrored into TypeScript types under `frontend/src/types/index.ts`.
*   **Storage Abstraction**: File I/O in the backend relies heavily on dependency injection via the `StorageBackend` protocol (in `services/storage.py`) to decouple the application from the local filesystem and allow for future cloud (S3) scalability.
*   **State & Planning**: Before making large architectural changes, refer to `badminton-analysis/.planning/STATE.md` and `ROADMAP.md`. Unfinished tasks (such as fully wiring up MediaPipe and resolving OpenCV Codec compatibility for browser playback) are tracked in `badminton-analysis/.planning/REMAINING_IMPROVEMENTS.md`.
