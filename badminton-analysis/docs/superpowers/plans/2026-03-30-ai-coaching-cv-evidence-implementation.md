# AI Coaching CV Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the deterministic coach-feedback path with a provider-configurable AI path that exposes expanded shuttle evidence, AI rationale, and provider provenance in the backend API and frontend report.

**Architecture:** Keep `AnalysisService` as the orchestrator. Add typed evidence models plus a dedicated evidence builder, then route coaching generation through a provider-agnostic LLM engine that defaults to Gemini Flash but can swap providers via config. Preserve deterministic fallback inside the service, then update the frontend to render the richer report contract.

**Tech Stack:** FastAPI, Pydantic v2, pytest, React, TypeScript, Vitest, provider-specific SDKs or adapters for LLM access

---

### Task 1: Expand Backend Report Schema With Tests First

**Files:**
- Create: `backend/src/badminton_analysis_api/evidence.py`
- Modify: `backend/src/badminton_analysis_api/models.py`
- Modify: `backend/tests/test_analyses_api.py`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing backend API tests for the expanded report**

```python
def test_completed_report_includes_llm_provenance_and_analysis_evidence(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client)

    client.post(f"/api/analyses/{analysis_id}/run")
    _poll_until_terminal(client, analysis_id)
    report = client.get(f"/api/analyses/{analysis_id}/report").json()

    assert report["generation_mode"] in {"ai", "fallback"}
    assert "analysis_evidence" in report
    assert "shuttle" in report["analytics_view"]
    assert "ai_rationale" in report
```

```python
def test_fallback_report_preserves_evidence_when_llm_generation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(
            store=AnalysisStore(),
            media_artifact_pipeline=FakeMediaArtifactPipeline(tmp_path),
            cv_pipeline=FakeCVPipeline(),
            coach_feedback_engine=FailingCoachFeedbackEngine(),
        ),
    )
    with TestClient(main_module.app) as client:
        analysis_id, _ = _ready_analysis(client)
        client.post(f"/api/analyses/{analysis_id}/run")
        _poll_until_terminal(client, analysis_id)
        report = client.get(f"/api/analyses/{analysis_id}/report").json()

    assert report["generation_mode"] == "fallback"
    assert report["analysis_evidence"]["shuttle"]["summary"]
    assert report["llm_provider"] is None
```

- [ ] **Step 2: Run the backend tests to verify they fail for the missing schema**

Run: `cd backend && uv run pytest tests/test_analyses_api.py -k "llm_provenance or preserves_evidence" -v`
Expected: `FAIL` with missing `generation_mode`, `analysis_evidence`, `shuttle`, or `ai_rationale` fields in the response model.

- [ ] **Step 3: Add the minimal typed models for provenance, rationale, and shuttle evidence**

```python
class ShuttleSample(BaseModel):
    timestamp_seconds: float
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class PressureWindow(BaseModel):
    label: str
    start_timestamp: str
    end_timestamp: str
    summary: str


class ShuttleMetrics(BaseModel):
    summary: str
    uncertainty_note: str
    samples: list[ShuttleSample]
    pressure_windows: list[PressureWindow]
    heatmap: list[HeatmapCell]


class AIRationale(BaseModel):
    summary: str
    evidence_highlights: list[str]


class AnalysisEvidence(BaseModel):
    shuttle: ShuttleMetrics
    movement_summary: str
    mechanics_summary: str
    shot_selection_summary: str
```

```python
class AnalyticsView(BaseModel):
    mechanics: MechanicsMetrics
    movement: MovementMetrics
    positioning: PositioningMetrics
    shot_selection: ShotSelectionMetrics
    shuttle: ShuttleMetrics


class AnalysisReport(BaseModel):
    analysis_id: str
    match_type: MatchType
    tracked_player_label: str
    coach_view: CoachView
    analytics_view: AnalyticsView
    confidence_annotations: list[ConfidenceAnnotation]
    generated_at: datetime
    llm_provider: str | None = None
    llm_model: str | None = None
    generation_mode: Literal["ai", "fallback"]
    analysis_evidence: AnalysisEvidence
    ai_rationale: AIRationale | None = None
```

- [ ] **Step 4: Run the backend tests to verify the new response contract passes**

Run: `cd backend && uv run pytest tests/test_analyses_api.py -k "llm_provenance or preserves_evidence" -v`
Expected: `PASS`

- [ ] **Step 5: Commit the schema task**

```bash
git add backend/src/badminton_analysis_api/models.py \
        backend/src/badminton_analysis_api/evidence.py \
        backend/tests/test_analyses_api.py
git commit -m "feat: add report evidence and provenance schema"
```

### Task 2: Implement Evidence Builder And Provider-Configurable Coaching Engine

**Files:**
- Create: `backend/src/badminton_analysis_api/evidence.py`
- Modify: `backend/src/badminton_analysis_api/coach_feedback.py`
- Modify: `backend/src/badminton_analysis_api/main.py`
- Modify: `backend/src/badminton_analysis_api/service.py`
- Modify: `backend/README.md`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing backend tests for provider config, AI generation, and fallback preservation**

```python
def test_build_coach_feedback_engine_defaults_to_gemini_flash() -> None:
    engine = build_coach_feedback_engine_from_env(engine_name="llm", provider=None, model=None)
    assert getattr(engine, "_provider") == "gemini"
    assert getattr(engine, "_model") == "gemini-3-flash-preview"
```

```python
def test_provider_engine_can_generate_ai_feedback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeLLMClient:
        def generate(self, *, provider: str, model: str, payload: dict[str, object]) -> dict[str, object]:
            assert provider == "gemini"
            assert model == "gemini-3-flash-preview"
            assert "analysis_evidence" in payload
            return {
                "coach_view": {
                    "summary": "AI summary",
                    "strengths": ["AI strength"],
                    "priority_issues": ["AI issue"],
                    "shot_selection_notes": "AI shot notes",
                    "footwork_notes": "AI footwork notes",
                    "positioning_notes": "AI positioning notes",
                    "confidence_notes": "AI confidence notes",
                    "recommended_drills": ["AI drill"],
                },
                "ai_rationale": {
                    "summary": "AI rationale",
                    "evidence_highlights": ["Shuttle pressure came from repeated forecourt occupancy."],
                },
            }
```

```python
    monkeypatch.setattr("badminton_analysis_api.coach_feedback._build_llm_client", lambda provider: FakeLLMClient())
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_analyses_api.py -k "defaults_to_gemini_flash or generate_ai_feedback" -v`
Expected: `FAIL` because the config path and provider-agnostic engine do not exist yet.

- [ ] **Step 3: Implement a minimal evidence builder and generic LLM engine**

```python
def build_analysis_evidence(
    *,
    analytics: AnalyticsView,
    tracking_summary: PlayerTrackSummary | None,
    pose_summary: PoseSummary | None,
) -> AnalysisEvidence:
    shuttle = build_shuttle_metrics(
        analytics=analytics,
        tracking_summary=tracking_summary,
    )
    return AnalysisEvidence(
        shuttle=shuttle,
        movement_summary=f"Tracked distance {analytics.movement.total_distance_meters:.1f}m",
        mechanics_summary=analytics.mechanics.recovery_note,
        shot_selection_summary=analytics.shot_selection.overview,
    )
```

```python
class LLMCoachFeedbackEngine:
    def __init__(
        self,
        *,
        provider: str = "gemini",
        model: str = "gemini-3-flash-preview",
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
    ) -> None:
        self._provider = provider
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
```

```python
def build_coach_feedback_engine_from_env(
    *,
    engine_name: str | None,
    provider: str | None,
    model: str | None,
) -> CoachFeedbackEngine:
    if engine_name == "llm":
        return LLMCoachFeedbackEngine(
            provider=provider or "gemini",
            model=model or "gemini-3-flash-preview",
        )
    return PlaceholderCoachFeedbackEngine()
```

```python
record.report = AnalysisReport(
    analysis_id=record.analysis_id,
    match_type=record.match_type,
    tracked_player_label=tracked_player.label,
    coach_view=coach_view,
    analytics_view=analytics,
    confidence_annotations=confidence_annotations,
    generated_at=datetime.now(UTC),
    llm_provider=provider_name_or_none,
    llm_model=model_name_or_none,
    generation_mode=generation_mode,
    analysis_evidence=analysis_evidence,
    ai_rationale=ai_rationale,
)
```

- [ ] **Step 4: Wire env config into the application bootstrap and docs**

```python
service = AnalysisService(
    coach_feedback_engine=build_coach_feedback_engine_from_env(
        engine_name=os.getenv("COACH_FEEDBACK_ENGINE"),
        provider=os.getenv("LLM_PROVIDER"),
        model=os.getenv("LLM_MODEL"),
    ),
    media_artifact_pipeline=build_media_artifact_pipeline_from_env(
        mode=os.getenv("MEDIA_PIPELINE"),
        artifact_root=os.getenv("MEDIA_ARTIFACT_ROOT"),
    ),
    cv_pipeline=build_cv_pipeline_from_env(
        mode=os.getenv("CV_PIPELINE"),
        yolo_model=os.getenv("YOLO_MODEL"),
        tracking_sample_fps=_env_float("TRACKING_SAMPLE_FPS", 2.0),
    ),
)
```

Update `backend/README.md` to document:

- `COACH_FEEDBACK_ENGINE=llm`
- `LLM_PROVIDER=gemini`
- `LLM_MODEL=gemini-3-flash-preview`
- provider-specific API key env vars

- [ ] **Step 5: Run the targeted backend tests, then the full backend suite**

Run: `cd backend && uv run pytest tests/test_analyses_api.py -k "gemini_flash or generate_ai_feedback or fallback" -v`
Expected: `PASS`

Run: `cd backend && uv run pytest`
Expected: `PASS`

- [ ] **Step 6: Commit the backend engine task**

```bash
git add backend/src/badminton_analysis_api/coach_feedback.py \
        backend/src/badminton_analysis_api/main.py \
        backend/src/badminton_analysis_api/service.py \
        backend/src/badminton_analysis_api/evidence.py \
        backend/src/badminton_analysis_api/models.py \
        backend/tests/test_analyses_api.py \
        backend/README.md \
        backend/pyproject.toml
git commit -m "feat: add provider-configurable AI coaching engine"
```

### Task 3: Render The Expanded AI And Shuttle Report In The Frontend

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing frontend test for the expanded report sections**

```tsx
test("renders provider provenance, AI rationale, and shuttle evidence", async () => {
  vi.useFakeTimers()
  queueFetchResponses([
    {
      status: 201,
      body: {
        analysis_id: "analysis-123",
        youtube_url: "https://www.youtube.com/watch?v=badminton-demo",
        match_type: "mixed_doubles",
        selection_required: true,
        stage: "setup_required",
        created_at: "2026-03-30T20:00:00Z",
      },
    },
    { body: setupResponse },
    {
      status: 202,
      body: {
        analysis_id: "analysis-123",
        stage: "ready_to_run",
        message: "Player selection saved. Analysis is ready to run.",
      },
    },
    {
      status: 202,
      body: {
        analysis_id: "analysis-123",
        stage: "analyzing",
        message: "Analysis started. Poll status for progress updates.",
      },
    },
    {
      body: {
        analysis_id: "analysis-123",
        stage: "completed",
        progress_percent: 100,
        message: "Report generated successfully.",
        warnings: [],
        error_details: null,
      },
    },
    {
      body: Object.assign({}, completedReport, {
        llm_provider: "gemini",
        llm_model: "gemini-3-flash-preview",
        generation_mode: "ai",
        ai_rationale: {
          summary: "AI rationale",
          evidence_highlights: ["Forecourt pressure repeated in three shuttle windows."],
        },
        analysis_evidence: {
          movement_summary: "Tracked distance 54.2m",
          mechanics_summary: "Recovery shape degrades after deep forehand movements.",
          shot_selection_summary: "Shot decisions are strongest when the feet arrive early.",
          shuttle: {
            summary: "Birdie pressure stayed front-court heavy.",
            uncertainty_note: "Shuttle path was inferred from sampled events.",
            samples: [{ timestamp_seconds: 12, x: 0.51, y: 0.24, confidence: 0.62 }],
            pressure_windows: [
              {
                label: "Forecourt pressure",
                start_timestamp: "00:10",
                end_timestamp: "00:18",
                summary: "Repeated forecourt interceptions kept pressure on the opponent.",
              },
            ],
            heatmap: [{ zone: "front-centre", weight: 0.34 }],
          },
        },
      }),
    },
  ])

  render(<App />)

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }))
  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument()
  })

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /player 1/i }))
    fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }))
    await Promise.resolve()
    await Promise.resolve()
  })

  expect(screen.getByText(/gemini-3-flash-preview/i)).toBeInTheDocument()
  expect(screen.getByText(/ai rationale/i)).toBeInTheDocument()
  expect(screen.getByText(/forecourt pressure/i)).toBeInTheDocument()
  expect(screen.getByText(/inferred from sampled events/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the frontend test to verify it fails**

Run: `cd frontend && pnpm test -- --run src/App.test.tsx`
Expected: `FAIL` because the report types and UI do not yet render the new fields.

- [ ] **Step 3: Update types and render the new report sections**

```ts
export interface AIRationale {
  summary: string;
  evidence_highlights: string[];
}

export interface ShuttleMetrics {
  summary: string;
  uncertainty_note: string;
  samples: ShuttleSample[];
  pressure_windows: PressureWindow[];
  heatmap: HeatmapCell[];
}

export interface AnalysisEvidence {
  shuttle: ShuttleMetrics;
  movement_summary: string;
  mechanics_summary: string;
  shot_selection_summary: string;
}
```

```tsx
{report.llm_model ? (
  <section>
    <h3>AI Provenance</h3>
    <p>{report.llm_provider} · {report.llm_model}</p>
  </section>
) : null}
```

```tsx
{report.ai_rationale ? (
  <section>
    <h3>AI Rationale</h3>
    <p>{report.ai_rationale.summary}</p>
    {report.ai_rationale.evidence_highlights.map((item) => (
      <li key={item}>{item}</li>
    ))}
  </section>
) : null}
```

```tsx
<section>
  <h3>Shuttle Evidence</h3>
  <p>{report.analysis_evidence.shuttle.summary}</p>
  <p>{report.analysis_evidence.shuttle.uncertainty_note}</p>
</section>
```

- [ ] **Step 4: Run the targeted frontend test, then the full frontend suite**

Run: `cd frontend && pnpm test -- --run src/App.test.tsx`
Expected: `PASS`

Run: `cd frontend && pnpm test`
Expected: `PASS`

- [ ] **Step 5: Commit the frontend task**

```bash
git add frontend/src/types.ts frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: render AI evidence and shuttle report sections"
```

### Task 4: Final Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-03-30-ai-coaching-cv-evidence-implementation.md`

- [ ] **Step 1: Run end-to-end verification commands**

Run: `cd backend && uv run pytest`
Expected: `PASS`

Run: `cd frontend && pnpm test`
Expected: `PASS`

Run: `cd frontend && pnpm build`
Expected: `PASS`

- [ ] **Step 2: Review the diff against the approved spec**

```bash
git status --short
git diff -- backend/src/badminton_analysis_api frontend/src
```

Expected: Only the planned backend and frontend files differ, and the diff shows provider config,
expanded evidence models, fallback preservation, and new report rendering.

- [ ] **Step 3: Request code review before claiming completion**

Capture the implementation diff and request review against:

- `docs/superpowers/specs/2026-03-30-ai-coaching-cv-evidence-design.md`
- `docs/superpowers/plans/2026-03-30-ai-coaching-cv-evidence-implementation.md`

- [ ] **Step 4: Commit any final review fixes**

```bash
git add backend/src/badminton_analysis_api frontend/src backend/tests backend/README.md
git commit -m "chore: finalize AI coaching evidence implementation"
```
