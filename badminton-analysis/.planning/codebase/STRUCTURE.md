# Codebase Structure

**Analysis Date:** 2026-03-29

## Directory Layout

```
badminton-analysis/
├── backend/                  # Python FastAPI backend
│   ├── main.py               # FastAPI app entry point, router registration
│   ├── pyproject.toml        # Python project config and dependencies
│   ├── setup.cfg             # Pytest and tool config
│   ├── uv.lock               # Locked dependency manifest
│   ├── models/               # Pydantic request/response schemas
│   ├── routers/              # FastAPI route handlers (one file per domain)
│   ├── services/             # Business logic and infrastructure services
│   ├── storage/              # Runtime file storage (uploads, analyses, videos)
│   └── tests/                # pytest test suite
├── frontend/                 # TypeScript React frontend
│   ├── index.html            # Vite HTML entry point
│   ├── package.json          # Node dependencies and scripts
│   ├── vite.config.ts        # Vite bundler config
│   ├── tailwind.config.js    # Tailwind CSS config
│   ├── tsconfig.json         # TypeScript config
│   └── src/                  # Application source
│       ├── main.tsx          # React app bootstrap
│       ├── App.tsx           # Root router component
│       ├── index.css         # Global styles
│       ├── api/              # API client layer
│       ├── components/       # Reusable UI components
│       ├── pages/            # Page-level route components
│       └── types/            # Shared TypeScript interfaces
├── docs/                     # Project documentation
│   └── superpowers/          # Planning specs and plans
├── Makefile                  # Developer task runner
└── .planning/                # GSD planning documents (not committed)
    └── codebase/             # Codebase analysis documents
```

## Directory Purposes

**`backend/models/`:**
- Purpose: Pydantic data models for API request/response validation
- Contains: One file `schemas.py` with all models
- Key files: `backend/models/schemas.py`

**`backend/routers/`:**
- Purpose: FastAPI `APIRouter` instances — each file owns one domain
- Contains: `upload.py`, `tus.py`, `video.py`, `detect.py`, `analyze.py`
- Pattern: Routers receive `StorageBackend` via dependency injection
- Key files: `backend/routers/analyze.py`, `backend/routers/tus.py`

**`backend/services/`:**
- Purpose: Business logic and infrastructure abstractions
- Contains: `analysis.py`, `detection.py`, `tracking.py`, `pose.py`, `storage.py`
- Key files:
  - `backend/services/storage.py` — `StorageBackend` protocol and `LocalStorageBackend` implementation
  - `backend/services/analysis.py` — core analysis pipeline
  - `backend/services/detection.py` — person detection logic
  - `backend/services/tracking.py` — movement tracking logic

**`backend/storage/`:**
- Purpose: Runtime data directory for uploaded videos, in-progress uploads, and analysis outputs
- Contains: UUID-named subdirectories per video/upload, `uploads/` subdirectory for in-progress tus uploads, `analyses/` subdirectory for analysis results
- Generated: Yes (at runtime)
- Committed: No (in `.gitignore`)

**`backend/tests/`:**
- Purpose: pytest unit and integration tests
- Contains: `conftest.py` plus one `test_*.py` file per router/service domain
- Key files: `backend/tests/conftest.py`, `backend/tests/test_tus.py`

**`frontend/src/api/`:**
- Purpose: All HTTP communication with the backend
- Contains: `client.ts` — a single `ApiClient` class exported as `apiClient` singleton
- Key files: `frontend/src/api/client.ts`

**`frontend/src/components/`:**
- Purpose: Reusable UI components used across pages
- Contains: `VideoUploader.tsx`
- Key files: `frontend/src/components/VideoUploader.tsx`

**`frontend/src/pages/`:**
- Purpose: Full-page route components mapped to React Router routes
- Contains: `UploadPage.tsx`, `SelectPage.tsx`, `ResultsPage.tsx`
- Routes: `/` → `UploadPage`, `/select/:videoId` → `SelectPage`, `/results/:videoId` → `ResultsPage`

**`frontend/src/types/`:**
- Purpose: TypeScript interface definitions mirroring backend Pydantic schemas
- Contains: `index.ts` with all shared interfaces
- Key files: `frontend/src/types/index.ts`

## Key File Locations

**Entry Points:**
- `backend/main.py`: FastAPI app creation, middleware, router registration
- `frontend/src/main.tsx`: React app bootstrap (ReactDOM.createRoot)
- `frontend/src/App.tsx`: Root component with React Router route definitions

**Configuration:**
- `backend/pyproject.toml`: Python dependencies, ruff linting/formatting config
- `backend/setup.cfg`: pytest configuration
- `frontend/vite.config.ts`: Vite build and proxy config
- `frontend/tailwind.config.js`: Tailwind CSS configuration
- `Makefile`: Developer commands for running, testing, formatting

**Core Logic:**
- `backend/services/storage.py`: `StorageBackend` protocol — the DI interface for all file I/O
- `backend/services/analysis.py`: Main badminton analysis pipeline
- `backend/models/schemas.py`: All Pydantic request/response models

**Testing:**
- `backend/tests/conftest.py`: Shared pytest fixtures
- `backend/tests/test_*.py`: One test file per domain

## Naming Conventions

**Backend files:**
- Service files: `snake_case.py` matching the domain noun (e.g., `analysis.py`, `detection.py`)
- Router files: `snake_case.py` matching the HTTP resource (e.g., `upload.py`, `video.py`)
- Test files: `test_<domain>.py` mirroring the router or service name

**Frontend files:**
- Page components: `PascalCasePage.tsx` (e.g., `UploadPage.tsx`, `ResultsPage.tsx`)
- Reusable components: `PascalCase.tsx` (e.g., `VideoUploader.tsx`)
- Non-component modules: `camelCase.ts` (e.g., `client.ts`)

**Backend classes:**
- Pydantic models: `PascalCase` with `Request`/`Response`/`Result` suffixes (e.g., `AnalyzeRequest`, `AnalysisResult`)
- Service classes: `PascalCase` with descriptive suffix (e.g., `LocalStorageBackend`)
- Protocols: `PascalCase` ending in verb-noun (e.g., `StorageBackend`)

## Where to Add New Code

**New API endpoint (backend):**
- Add router file: `backend/routers/<domain>.py`
- Add Pydantic schemas: `backend/models/schemas.py`
- Register router in: `backend/main.py` via `app.include_router(...)`
- Add business logic: `backend/services/<domain>.py`
- Add tests: `backend/tests/test_<domain>.py`

**New frontend page:**
- Add component: `frontend/src/pages/<Name>Page.tsx`
- Register route in: `frontend/src/App.tsx`

**New reusable UI component:**
- Implementation: `frontend/src/components/<ComponentName>.tsx`

**New API method (frontend):**
- Add method to `ApiClient` class in: `frontend/src/api/client.ts`
- Add supporting TypeScript interfaces to: `frontend/src/types/index.ts`

**New storage operation:**
- Add method to `StorageBackend` protocol in: `backend/services/storage.py`
- Implement in `LocalStorageBackend` in the same file
- Inject via `Depends(get_storage)` in routers

## Special Directories

**`backend/storage/`:**
- Purpose: Runtime file storage — video uploads, in-progress tus chunks, analysis outputs
- Generated: Yes, at runtime by `LocalStorageBackend`
- Committed: No

**`backend/.venv/`:**
- Purpose: Python virtual environment managed by `uv`
- Generated: Yes
- Committed: No

**`frontend/node_modules/`:**
- Purpose: Node.js dependencies
- Generated: Yes
- Committed: No

**`backend/badminton_analysis.egg-info/`:**
- Purpose: Python package metadata generated by editable install
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-03-29*
