# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Mobile-friendly web app for badminton video analysis. Users paste a YouTube URL, select a player, and get a coach-first report with movement/shot-selection analytics.

## Structure

```
badminton-analysis/
├── backend/   # FastAPI + Python (uv, ruff, ty)
├── frontend/  # React + TypeScript + Vite + Tailwind CSS v4 (pnpm)
└── docs/      # Plans and specs (docs/plans/)
```

## Commands

All commands run from `badminton-analysis/`.

### Running the full stack

```bash
source backend/.venv/bin/activate  # required before `make run`
make run                            # starts backend :8000 + frontend :5173 (real pipelines: MEDIA_PIPELINE=shell CV_PIPELINE=hybrid)
make run-mock                       # starts with mock pipelines (no yt-dlp/ffmpeg/YOLO needed)
make kill                           # stop both servers
```

### Install dependencies

```bash
make install          # both
make install-backend  # uv sync (backend only)
make install-frontend # pnpm install (frontend only)
```

### Tests

```bash
make test              # backend + frontend
make test-backend      # uv run pytest (requires venv)
make test-frontend     # pnpm test (vitest run)
```

### Backend

```bash
cd badminton-analysis/backend
uv run pytest                          # all tests
uv run pytest tests/test_analyses_api.py::test_name  # single test
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
                                          ↘ failed
```

1. `POST /api/analyses` — downloads video (yt-dlp), extracts setup frame (ffmpeg), runs YOLO player detection + court detection → `setup_required`
2. `GET /api/analyses/{id}/setup` — returns detected players (with bounding boxes) and court corners for the setup screen
3. `POST /api/analyses/{id}/selection` — user picks a player and confirms court points → `ready_to_run`
4. `POST /api/analyses/{id}/run` — runs YOLO tracking, MediaPipe pose estimation, builds `AnalyticsView` + `ShuttleMetrics` + `AnalysisEvidence`, passes to `CoachFeedbackEngine` (LLM or placeholder), assembles `AnalysisReport` → `completed`
5. `GET /api/analyses/{id}/report` — returns the completed report

### Backend layers

| File | Role |
|------|------|
| `main.py` | FastAPI routes — thin, delegates to `AnalysisService` |
| `service.py` | `AnalysisService` — orchestrates all lifecycle logic, builds analytics |
| `models.py` | All Pydantic models (`AnalysisRecord`, `AnalysisReport`, `ShuttleMetrics`, `AnalysisEvidence`, etc.) |
| `store.py` | `AnalysisStore` — in-memory dict keyed by `analysis_id` (no persistence) |
| `coach_feedback.py` | `CoachFeedbackEngine` Protocol + `PlaceholderCoachFeedbackEngine` + `LLMCoachFeedbackEngine` (Gemini default) |
| `cv.py` | `CVPipeline` Protocol + `MockCVPipeline` + `HybridCVPipeline` (YOLO detection/tracking, MediaPipe pose) |
| `media.py` | `MediaArtifactPipeline` Protocol + `MockMediaArtifactPipeline` + `ShellMediaArtifactPipeline` (yt-dlp + ffmpeg + ffprobe) |
| `evidence.py` | `build_analysis_evidence()`, `build_shuttle_metrics()` — inferred shuttle positions, pressure windows, Gaussian heatmaps |

### CV pipeline

`HybridCVPipeline` uses YOLO (ultralytics) for person detection and tracking, and MediaPipe Tasks API (`PoseLandmarker`) for pose estimation. Player detection uses court-proximity scoring with a 30% margin to filter spectators. Track-to-player mapping uses spatial matching (bounding box positions). The pose model (`pose_landmarker_lite.task`) auto-downloads to `~/.cache/badminton-analysis/`.

### AI boundary

`CoachFeedbackEngine` is a Protocol that separates deterministic CV/metrics from coaching commentary. Three implementations exist:
- `PlaceholderCoachFeedbackEngine` — fully deterministic fallback
- `LLMCoachFeedbackEngine` — generic LLM via `StructuredLLMClient` Protocol (defaults to Gemini Flash)
- `PydanticAICoachFeedbackEngine` — PydanticAI variant of the LLM engine

If AI fails, the app degrades to placeholder content without breaking the report schema. Reports include `generation_mode` ("ai" | "fallback"), `llm_provider`, `llm_model`, and `ai_rationale` for provenance.

### Frontend

Single-file SPA (`App.tsx`) styled with Tailwind CSS v4 (blue/slate theme). `Screen` state machine: `analyze → setup → processing → report`. All API calls in `api.ts`. Types mirror backend models in `types.ts`. Vite proxies `/api/*` to `localhost:8000`.

Key UI features:
- **Setup screen** — clickable bounding box overlays on the setup frame for player selection
- **Report screen** — two tabs (`coach | analytics`):
  - **Coach tab** — narrative summary, strengths, priority issues, notes, recommended drills, LLM provenance badge, AI rationale
  - **Analytics tab** — mechanics, movement stats, visual court heatmap (colored 3×3 grid), shuttle metrics, shot selection events with clickable YouTube timestamp links
- Back/navigation buttons on every screen, "Analyze another video" on report

### Report data model

`AnalysisReport` includes:
- `coach_view` — narrative coaching feedback
- `analytics_view` — mechanics, movement, positioning (with heatmap), shot selection (with events), shuttle metrics (samples, pressure windows, heatmap)
- `analysis_evidence` — structured evidence summaries passed to the LLM
- `confidence_annotations` — per-field confidence scores with reasons
- `ai_rationale` — LLM's reasoning highlights (null for placeholder)
- `llm_provider`, `llm_model`, `generation_mode` — provenance fields

## Key constraints

- `AnalysisStore` is in-memory — all data is lost on server restart
- `owner_id` is `null` throughout MVP (auth not implemented yet, field reserved)
- `make run` requires `yt-dlp`, `ffmpeg`, and `ffprobe` installed on PATH
- `make run-mock` works without external tools (all player/court/video data is mocked)
- CORS defaults to `http://localhost:5173`, configurable via `ALLOWED_ORIGINS` env var (comma-separated)
- Shot event timestamps are distributed proportionally across the actual video duration (probed via ffprobe)
- Specs live in `docs/plans/`
