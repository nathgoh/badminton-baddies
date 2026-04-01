# Annotated Report Clips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend-rendered annotated report clips with stick-figure overlays for report windows, while keeping automatic YouTube fallback when clip rendering is unavailable.

**Architecture:** Extend the media artifact pipeline so it can render short MP4 clip artifacts from the local source video using the selected player’s tracking and pose data. Wire those artifacts into the report contract and API, then update the frontend shared clip viewer to prefer a native video player when annotated clips exist and fall back to the existing YouTube embed otherwise.

**Tech Stack:** FastAPI, Pydantic, OpenCV, ffmpeg shell tooling, React, TypeScript, Vitest, pytest

---

### Task 1: Extend The Report Contract For Annotated Clips

**Files:**
- Modify: `backend/src/schemas/report.py`
- Modify: `frontend/src/types.ts`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing backend/API test**

```python
def test_report_events_can_include_rendered_clip_metadata(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")

    run_response = client.post(f"/api/analyses/{analysis_id}/run")

    assert run_response.status_code == 202
    _poll_until_terminal(client, analysis_id)

    report = client.get(f"/api/analyses/{analysis_id}/report").json()
    shot_event = report["analytics_view"]["shot_selection"]["events"][0]
    pressure_window = report["analysis_evidence"]["shuttle"]["pressure_windows"][0]

    assert "rendered_clip_url" in shot_event
    assert "rendered_clip_media_type" in shot_event
    assert "rendered_clip_url" in pressure_window
    assert "rendered_clip_media_type" in pressure_window
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py::test_report_events_can_include_rendered_clip_metadata -v`
Expected: FAIL because the report schema does not yet include rendered clip fields.

- [ ] **Step 3: Add the minimal schema fields**

```python
class ShotSelectionEvent(BaseModel):
    ...
    clip_start_seconds: int
    clip_end_seconds: int
    rendered_clip_url: str | None = None
    rendered_clip_media_type: str | None = None


class PressureWindow(BaseModel):
    ...
    clip_start_seconds: int | None = None
    clip_end_seconds: int | None = None
    rendered_clip_url: str | None = None
    rendered_clip_media_type: str | None = None
```

- [ ] **Step 4: Mirror the new fields in frontend types**

```ts
export interface ShotSelectionEvent {
  ...
  clip_start_seconds: number;
  clip_end_seconds: number;
  rendered_clip_url?: string | null;
  rendered_clip_media_type?: string | null;
}

export interface PressureWindow {
  ...
  clip_start_seconds?: number | null;
  clip_end_seconds?: number | null;
  rendered_clip_url?: string | null;
  rendered_clip_media_type?: string | null;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py::test_report_events_can_include_rendered_clip_metadata -v`
Expected: PASS

### Task 2: Add Annotated Clip Rendering To The Media Pipeline

**Files:**
- Modify: `backend/src/pipelines/media/pipeline.py`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing media/route tests**

```python
def test_report_clip_file_is_served_when_rendered(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")
    client.post(f"/api/analyses/{analysis_id}/run")
    _poll_until_terminal(client, analysis_id)

    report = client.get(f"/api/analyses/{analysis_id}/report").json()
    clip_url = report["analytics_view"]["shot_selection"]["events"][0]["rendered_clip_url"]

    clip_response = client.get(clip_url)

    assert clip_response.status_code == 200
    assert clip_response.headers["content-type"] == "video/mp4"


def test_clip_render_failure_keeps_report_usable(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")
    client.post(f"/api/analyses/{analysis_id}/run")
    _poll_until_terminal(client, analysis_id)

    report = client.get(f"/api/analyses/{analysis_id}/report").json()

    assert report["analytics_view"]["shot_selection"]["events"][0]["rendered_clip_url"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py::test_report_clip_file_is_served_when_rendered tests/test_analyses_api.py::test_clip_render_failure_keeps_report_usable -v`
Expected: FAIL because the media pipeline cannot render or serve report clip artifacts yet.

- [ ] **Step 3: Extend the media artifact contract**

```python
@dataclass(slots=True)
class RenderedClipArtifact:
    clip_id: str
    path: str
    media_type: str


class MediaArtifactPipeline(Protocol):
    def prepare_analysis(self, analysis_id: str, youtube_url: str) -> PreparedMediaArtifacts: ...
    def render_report_clip(
        self,
        *,
        analysis_id: str,
        clip_id: str,
        source_video_path: str,
        clip_start_seconds: int,
        clip_end_seconds: int,
        annotate_frame: Callable[[Any, int], Any],
    ) -> RenderedClipArtifact: ...
    def cleanup_analysis(self, analysis_id: str) -> None: ...
```

- [ ] **Step 4: Implement mock and shell rendering support**

```python
class MockMediaArtifactPipeline:
    def render_report_clip(... ) -> RenderedClipArtifact:
        clip_path = analysis_dir / f"{clip_id}.mp4"
        clip_path.write_bytes(b"mock-clip")
        return RenderedClipArtifact(clip_id=clip_id, path=str(clip_path), media_type="video/mp4")


class ShellMediaArtifactPipeline:
    def render_report_clip(... ) -> RenderedClipArtifact:
        # extract frames from the requested window, call annotate_frame for each frame,
        # then encode the annotated frames to mp4 and return the artifact path
```

- [ ] **Step 5: Run the targeted tests again**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py::test_report_clip_file_is_served_when_rendered tests/test_analyses_api.py::test_clip_render_failure_keeps_report_usable -v`
Expected: PASS

### Task 3: Wire Clip Rendering Into AnalysisService And The API

**Files:**
- Modify: `backend/src/analyses/service.py`
- Modify: `backend/src/api/app.py`
- Modify: `backend/src/schemas/analysis.py`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing service/API tests**

```python
def test_report_prefers_rendered_clip_metadata_from_service(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")
    client.post(f"/api/analyses/{analysis_id}/run")
    _poll_until_terminal(client, analysis_id)

    report = client.get(f"/api/analyses/{analysis_id}/report").json()
    event = report["analytics_view"]["shot_selection"]["events"][0]

    assert event["rendered_clip_url"] == f"/api/analyses/{analysis_id}/clips/shot-00-12-smash"
    assert event["rendered_clip_media_type"] == "video/mp4"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py::test_report_prefers_rendered_clip_metadata_from_service -v`
Expected: FAIL because the service does not render clips or publish clip URLs yet.

- [ ] **Step 3: Add clip serving and report enrichment**

```python
@app.get("/api/analyses/{analysis_id}/clips/{clip_id}")
def get_rendered_clip(... ) -> FileResponse:
    path, media_type = service.get_rendered_clip_file(analysis_id, clip_id, owner_id=owner_id)
    return FileResponse(path, media_type=media_type)


class AnalysisService:
    def get_rendered_clip_file(... ) -> tuple[Path, str]:
        ...

    def _attach_rendered_report_clips(
        self,
        record: AnalysisRecord,
        analytics: AnalyticsView,
        tracking_summary: PlayerTrackSummary | None,
        pose_summary: PoseSummary | None,
    ) -> AnalyticsView:
        ...
```

- [ ] **Step 4: Keep failures as warnings with empty metadata**

```python
try:
    artifact = self._media_artifact_pipeline.render_report_clip(...)
except Exception as exc:
    record.warnings = [*record.warnings, f"Annotated clip fallback applied after {exc}."]
    return event.model_copy(update={"rendered_clip_url": None, "rendered_clip_media_type": None})
```

- [ ] **Step 5: Run the targeted backend tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py::test_report_prefers_rendered_clip_metadata_from_service tests/test_analyses_api.py::test_report_clip_file_is_served_when_rendered tests/test_analyses_api.py::test_clip_render_failure_keeps_report_usable -v`
Expected: PASS

### Task 4: Prefer Annotated Clips In The Frontend Viewer

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/types.ts`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing frontend tests**

```tsx
test("prefers annotated video clips over YouTube embeds when available", async () => {
  const video = await screen.findByTitle(/annotated report clip/i);
  expect(video).toHaveAttribute("src", "/api/analyses/analysis-123/clips/shot-00-12-smash");
});

test("falls back to the YouTube iframe when rendered clips are unavailable", async () => {
  const iframe = screen.getByTitle(/report clip player/i);
  expect(iframe).toHaveAttribute("src", expect.stringContaining("/embed/badminton-demo"));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && pnpm test -- --runInBand src/App.test.tsx`
Expected: FAIL because the report viewer only knows how to render the YouTube iframe today.

- [ ] **Step 3: Update the clip selection and viewer rendering**

```tsx
const activeRenderedClipUrl = selectedClip?.renderedClipUrl ?? null;
const activeYoutubeClipUrl =
  activeRenderedClipUrl === null && selectedClip !== null
    ? youtubeEmbedUrl(reportYoutubeUrl, selectedClip.startSeconds, selectedClip.endSeconds)
    : null;

{activeRenderedClipUrl ? (
  <video title="Annotated report clip" src={activeRenderedClipUrl} controls className="aspect-video w-full" />
) : activeYoutubeClipUrl ? (
  <iframe title="Report clip player" src={activeYoutubeClipUrl} className="aspect-video w-full" />
) : (
  ...
)}
```

- [ ] **Step 4: Add clip-type labeling**

```tsx
<p className="mt-1 text-sm text-slate-300">
  {selectedClip
    ? `${selectedClip.assetLabel} • ${selectedClip.startSeconds}s-${selectedClip.endSeconds}s`
    : "Load a shot or shuttle clip to preview it here."}
</p>
```

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && pnpm test -- --runInBand src/App.test.tsx`
Expected: PASS

### Task 5: Final Verification

**Files:**
- Modify: `backend/tests/test_analyses_api.py`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Run backend lint**

Run: `cd backend && .venv/bin/python -m ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 2: Run backend tests**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: PASS

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && pnpm test`
Expected: PASS

- [ ] **Step 4: Run frontend build**

Run: `cd frontend && pnpm build`
Expected: PASS

