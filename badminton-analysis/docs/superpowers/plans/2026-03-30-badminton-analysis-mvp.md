# Badminton Analysis MVP Plan
---

## Summary

Build badminton-analysis as a mobile-friendly web app with a React + TypeScript + TailwindCSS + Vite frontend
and a FastAPI backend managed with uv, ruff, and ty. The MVP flow is: paste a public YouTube URL,
choose match type, confirm the tracked player from detected people on court, optionally correct
auto-detected court lines, run async analysis, then review a two-tab report with Coach View as the
primary tab and Analytics View as the supporting tab.

The product is explicitly coach-oriented, but every insight must be backed by structured evidence
and timestamps. The system supports men's singles, women's singles, men's doubles, women's doubles,
and mixed doubles, with match-type-aware heuristics for movement, positioning, and shot-selection
analysis.

---

## Key Changes From Original Plan

- Create a monorepo under `badminton-analysis/` with:
  - `frontend/` for the Vite SPA
  - `backend/` for FastAPI, async analysis orchestration, and CV/report services
  - `docs/` for metric definitions, report schema, and future AI notes
- Use `analyses` as the main domain resource instead of generic jobs.
- Frontend screens: Analyze → Setup → Processing → Report
- Backend pipeline stages (see Pipeline Stages section below)
- Report model contains four top-level sections: `mechanics`, `movement`, `positioning`,
  `shot_selection` (see Data Model section below)
- Tactical analysis uses heuristic scoring in MVP
- API surface as defined below
- Stable typed report contract shared across deterministic analysis and future AI commentary
- AI boundary: core CV deterministic, `CoachFeedbackEngine` interface on top
- Future account readiness: single-user MVP, `owner_id` nullable for future auth

---

## Frontend Screens

### Analyze
- YouTube URL input (type=url, required)
- Match type selector (all five types)
- Brief description of coach-first vs. analytics-tab purpose

### Setup
- Render the actual `setup_frame_url` returned by the backend (not a placeholder)
- Overlay detected court corners as draggable handles; user can adjust
- Player candidate cards (one per detected player), user selects one
- Show court detection confidence and adjustment hint
- "Save setup and run" CTA — disabled until a player is selected

### Processing
- Poll `GET /api/analyses/{id}/status` every 2 seconds
- Display `progress_percent` from the status response (not a hardcoded value)
- Show any `warnings` returned in the status payload
- On `stage = failed`, surface `error_details` and allow user to restart from Setup

### Report
- Two tabs: **Coach View** (primary, default) and **Analytics View**
- Coach View: summary, strengths, priority issues, recommended drills,
  shot-selection notes, footwork notes, positioning notes, confidence notes
- Analytics View: movement metrics, positioning (zone occupancy + heatmap),
  shot events with execution and decision scores, evidence references

---

## Backend Pipeline Stages

All stages are currently mocked. The plan documents what each stage will do when real CV is added.

1. YouTube ingestion and video normalization
2. Setup-frame extraction (key frame sampled from the first 30 s)
3. Court detection plus manual override support
4. Multi-person detection and tracking
5. Target-player assignment after user selection
6. Pose and movement signal extraction
7. Shot event inference
8. Tactical shot-quality scoring
9. Report assembly

---

## Analysis Lifecycle

The core domain object is `AnalysisRecord`. It progresses through five stages:

```
setup_required → ready_to_run → analyzing → completed
                                          ↘ failed
```

| Stage | Meaning |
|---|---|
| `setup_required` | Created; waiting for player selection and court confirmation |
| `ready_to_run` | Selection saved; ready to execute |
| `analyzing` | Pipeline running |
| `completed` | Report available |
| `failed` | Pipeline error; `error_details` set on the status response |

The `failed` stage is terminal. The UI must surface the failure reason and allow the user to
re-run from the Setup screen (which does not reset the selection).

---

## Data Model

### `AnalysisStage`

```python
class AnalysisStage(StrEnum):
    SETUP_REQUIRED = "setup_required"
    READY_TO_RUN   = "ready_to_run"
    ANALYZING      = "analyzing"
    COMPLETED      = "completed"
    FAILED         = "failed"          # NEW — was missing from original plan
```

### `AnalysisStatusResponse`

```python
class AnalysisStatusResponse(BaseModel):
    analysis_id:     str
    stage:           AnalysisStage
    progress_percent: int              # 0–100
    message:         str
    warnings:        list[str]         # NEW — operational warnings (e.g. low confidence)
    error_details:   str | None        # NEW — set only when stage = failed
```

### `MechanicsMetrics` (NEW — was in plan but not built)

```python
class MechanicsMetrics(BaseModel):
    stance_note:           str
    preparation_note:      str
    balance_note:          str
    recovery_note:         str
    stroke_execution_note: str
```

### `MovementMetrics`

```python
class MovementMetrics(BaseModel):
    total_distance_meters:      float
    recovery_score:             int        # 0–100
    court_coverage_percent:     int        # 0–100
    change_of_direction_count:  int
    burst_count:                int        # NEW — explosive acceleration sequences
    directional_balance:        dict[str, float]  # NEW — e.g. {"left": 0.48, "right": 0.52}
```

### `HeatmapCell`

```python
class HeatmapCell(BaseModel):
    zone: str   # e.g. "front-left", "mid-centre", "rear-right"
    weight: float  # 0.0–1.0 normalised occupancy
```

### `PositioningMetrics`

```python
class PositioningMetrics(BaseModel):
    base_position_note: str
    zone_occupancy:     dict[str, int]   # % per zone (front/mid/rear)
    heatmap:            list[HeatmapCell]  # NEW — 9-zone or finer grid
    spacing_note:       str              # singles: base depth; doubles: partner spacing
```

### `ShotSelectionEvent`

```python
class ShotSelectionEvent(BaseModel):
    timestamp:        str   # "MM:SS"
    shot_type:        str
    execution_score:  int   # 0–100
    decision_score:   int   # 0–100
    decision_quality: Literal["strong", "neutral", "poor"]  # NEW — explicit classification
    recommendation:   str
    evidence:         str   # was "rationale" — renamed for plan consistency
```

### `AnalyticsView`

```python
class AnalyticsView(BaseModel):
    mechanics:     MechanicsMetrics      # NEW — was omitted from implementation
    movement:      MovementMetrics
    positioning:   PositioningMetrics
    shot_selection: ShotSelectionMetrics
```

### `CoachView`

```python
class CoachView(BaseModel):
    summary:              str
    strengths:            list[str]
    priority_issues:      list[str]
    shot_selection_notes: str        # NEW — was in plan, missing from model
    footwork_notes:       str        # NEW — was in plan, missing from model
    positioning_notes:    str        # NEW — was in plan, missing from model
    confidence_notes:     str        # NEW — caveats on evidence quality
    recommended_drills:   list[str]
```

### `ConfidenceAnnotation` (NEW)

```python
class ConfidenceAnnotation(BaseModel):
    field:      str    # dotted path e.g. "analytics.movement.recovery_score"
    confidence: float  # 0.0–1.0
    reason:     str    # e.g. "short clip — fewer than 20 events sampled"
```

### `AnalysisReport`

```python
class AnalysisReport(BaseModel):
    analysis_id:          str
    match_type:           MatchType
    tracked_player_label: str
    coach_view:           CoachView
    analytics_view:       AnalyticsView
    confidence_annotations: list[ConfidenceAnnotation]  # NEW
    generated_at:         datetime
```

---

## API Surface

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/analyses` | Create analysis (returns `setup_required`) |
| GET | `/api/analyses` | List analyses (paginated — see below) |
| GET | `/api/analyses/{id}/setup` | Return setup frame, player candidates, court |
| POST | `/api/analyses/{id}/selection` | Save player + court → `ready_to_run` |
| POST | `/api/analyses/{id}/run` | Trigger pipeline → `analyzing` |
| GET | `/api/analyses/{id}/status` | Poll stage, progress, warnings, error |
| GET | `/api/analyses/{id}/report` | Fetch completed report |
| DELETE | `/api/analyses/{id}` | Remove analysis record (NEW) |

### `GET /api/analyses` — Pagination

```
GET /api/analyses?page=1&page_size=20
```

Response adds:

```json
{ "items": [...], "total": 42, "page": 1, "page_size": 20 }
```

Default `page_size` is 20, max is 100.

---

## `CoachFeedbackEngine` Interface

```python
class CoachFeedbackEngine(Protocol):
    def create_feedback(
        self,
        *,
        analytics: AnalyticsView,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
    ) -> CoachView: ...
```

### Prompt bundle for AI path

When `PydanticAICoachFeedbackEngine` is configured, it serialises the following as the prompt
context (JSON, trimmed):

- `match_type`
- `tracked_player.label` and `tracked_player.side`
- `analytics.mechanics` (all notes)
- `analytics.movement` (all metrics)
- `analytics.positioning` (base note, zone occupancy, spacing note)
- `analytics.shot_selection.overview` + first 10 events (timestamp, type, scores, evidence)
- `confidence_annotations` summary

The expected typed output is `CoachView` validated via Pydantic. On validation failure or model
error, the service falls back to `PlaceholderCoachFeedbackEngine` without surfacing the error to
the user (a `warning` is added to the status instead).

---

## CORS Configuration

- Development: `allow_origins=["http://localhost:5173"]`
- Production: read from environment variable `ALLOWED_ORIGINS` (comma-separated list)
- The FastAPI middleware must be updated before any public deployment

---

## Assumptions And Defaults

- MVP uses public YouTube URLs only; local upload is out of scope.
- MVP is a responsive web app, not a native mobile app.
- Court detection is automatic first, with user drag-adjustment available at all times
  (not only when confidence is low).
- Player tracking is human-in-the-loop; the user explicitly selects the athlete to analyse.
- AI is not on the critical path for MVP correctness.
- `analyses` is the canonical API/domain name.
- `AnalysisStore` is in-memory — all data is lost on server restart (MVP constraint).
- `owner_id` is `null` throughout MVP; field is reserved for future auth.
- YouTube ingestion, video processing, and CV pipeline are not yet implemented — all
  player/court data is mocked.

---

## Test Plan

Coverage targets per area (all as integration tests against the real in-memory service):

### URL intake
- Valid public YouTube URL → 201 with `stage = setup_required`
- Malformed URL → 422 validation error with descriptive message

### Setup flow
- Player candidates returned for singles (2) and doubles (4) match types
- User can select any player and override court geometry; stage advances to `ready_to_run`
- Selecting a non-existent `player_id` → 404

### Match-type behaviour
- Singles analyses use singles positional heuristics (base depth note)
- Doubles analyses use partner spacing note
- Mixed doubles does not hard-code role advice without evidence

### Report generation
- Deterministic report renders without AI enabled (`PlaceholderCoachFeedbackEngine`)
- Report includes all four `AnalyticsView` sections (`mechanics`, `movement`, `positioning`,
  `shot_selection`)
- AI output, when enabled, conforms to the typed `CoachView` schema
- AI failure degrades to deterministic content; a warning appears in status

### Tactical shot analysis
- Shot events carry `execution_score`, `decision_score`, `decision_quality`, and `evidence`
- Low-confidence scenarios suppress overconfident alternatives (no recommendation when
  `decision_score < 50` and `execution_score < 60`)

### Lifecycle and status polling
- `run` on a non-`ready_to_run` record → 409 conflict
- Status transitions are reflected in `progress_percent` and `message`
- `failed` stage sets `error_details` and returns 200 (not 5xx) on status poll
- `DELETE /api/analyses/{id}` removes the record; subsequent GET → 404

### UI behaviour (manual / Playwright — out of scope for unit tests)
- Setup and report flows are usable on 375 px mobile widths
- Coach tab is the default; Analytics tab is accessible
- Processing screen polls and updates progress from real status response
- Failed analysis surfaces error and re-enables Setup screen

---

## Phasing

### Phase 0 (complete)
- FastAPI skeleton with all seven endpoints (mocked data)
- In-memory store
- `PlaceholderCoachFeedbackEngine`
- React SPA with four-screen flow
- Two integration tests

### Phase 1 (next)
- Add `FAILED` stage and `warnings`/`error_details` to status response
- Add `mechanics` to `AnalyticsView` and `MechanicsMetrics` model
- Expand `CoachView` with the four additional text fields
- Rename `ShotSelectionEvent.rationale` → `evidence`; add `decision_quality`
- Add `burst_count` and `directional_balance` to `MovementMetrics`
- Add `heatmap` to `PositioningMetrics`
- Add `ConfidenceAnnotation` list to `AnalysisReport`
- Add `DELETE /api/analyses/{id}`
- Paginate `GET /api/analyses`
- Expand test suite to cover all test plan items above

### Phase 2 (future)
- Frontend: render actual `setup_frame_url` (real or placeholder image)
- Frontend: draggable court corner handles
- Frontend: real status polling (replace hardcoded 72%)
- Frontend: display `warnings` and `failed` error state
- Frontend: Coach View additions (shot-selection notes, footwork notes, etc.)
- Frontend: heatmap visualisation (9-zone grid)

### Phase 3 (future)
- PydanticAI coach feedback integration
- YouTube download and frame extraction
- Real CV pipeline (person detection, pose estimation, court line detection)
- Production CORS configuration from environment
- Auth and `owner_id` population

---

## References

- PydanticAI docs: https://ai.pydantic.dev/
- OpenAI Agents SDK docs: https://openai.github.io/openai-agents-python/
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
