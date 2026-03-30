# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Mobile-friendly web app for badminton video analysis. Users paste a YouTube URL, select a player, and get a coach-first report with movement/shot-selection analytics.

## Structure

```
badminton-analysis/
├── backend/   # FastAPI + Python (uv, ruff, ty)
├── frontend/  # React + TypeScript + Vite (pnpm)
└── docs/      # Plans and specs (docs/plans/)
```

## Commands

All commands run from `badminton-analysis/`.

### Running the full stack

```bash
source backend/.venv/bin/activate  # required before `make run`
make run                            # starts backend :8000 + frontend :5173
make kill                           # stop both servers
```

### Install dependencies

```bash
make install          # both
make install-backend  # uv sync (backend only)
make install-frontend # pnpm install (frontend only)
```

### Backend

```bash
cd badminton-analysis/backend
uv run pytest                          # all tests
uv run pytest tests/test_analyses_api.py::test_runs_analysis_after_selection_and_returns_report  # single test
uv run ruff check src/ tests/          # lint
uv run ruff format src/ tests/         # format
uv run ty check src/                   # type check (ty, not mypy)
```

### Frontend

```bash
cd badminton-analysis/frontend
pnpm test      # vitest run
pnpm dev       # dev server
pnpm build     # tsc -b && vite build
```

## Architecture

### Analysis lifecycle

The core domain object is `AnalysisRecord`. It progresses through four stages:

```
setup_required → ready_to_run → analyzing → completed
```

1. `POST /api/analyses` — creates a record with mock player candidates and court detection
2. `GET /api/analyses/{id}/setup` — returns detected players and court corners for the setup screen
3. `POST /api/analyses/{id}/selection` — user picks a player and confirms court points → advances to `ready_to_run`
4. `POST /api/analyses/{id}/run` — builds `AnalyticsView` (hardcoded heuristics), passes it to `CoachFeedbackEngine`, assembles `AnalysisReport` → advances to `completed`
5. `GET /api/analyses/{id}/report` — returns the completed report

### Backend layers

| File | Role |
|------|------|
| `main.py` | FastAPI routes — thin, delegates to `AnalysisService` |
| `service.py` | `AnalysisService` — orchestrates all lifecycle logic |
| `models.py` | All Pydantic models (`AnalysisRecord`, `AnalysisReport`, etc.) |
| `store.py` | `AnalysisStore` — in-memory dict keyed by `analysis_id` (no persistence) |
| `coach_feedback.py` | `CoachFeedbackEngine` Protocol + `PlaceholderCoachFeedbackEngine` |

### AI boundary

`CoachFeedbackEngine` is a Protocol that separates deterministic CV/metrics from coaching commentary. The current implementation (`PlaceholderCoachFeedbackEngine`) is fully deterministic. The interface is designed for a future single-prompt PydanticAI path that produces typed `CoachView` output. If AI fails or is disabled, the app degrades to placeholder content without breaking the report schema.

### Frontend

Single-file SPA (`App.tsx`) with a `Screen` state machine: `analyze → setup → processing → report`. All API calls are in `api.ts`. Types mirror the backend Pydantic models in `types.ts`. The dev server proxies `/api/*` to `localhost:8000` via the Vite config.

## Key constraints

- `AnalysisStore` is in-memory — all data is lost on server restart
- `owner_id` is `null` throughout MVP (auth not implemented yet, field reserved)
- YouTube ingestion, actual video processing, and CV pipeline are not yet implemented — all player/court data is mocked
- CORS is locked to `http://localhost:5173`
