# Tracking Calibration, Shuttle Detection, and Report Clip Embeds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make movement and positioning metrics credible for real badminton footage, bind analysis to the user-selected player instead of a generic tracked person, add Gaussian-based shuttle observation as first-class evidence, and let report events open an embedded YouTube clip snippet.

**Architecture:** Split the work into four explicit data-quality layers: court-space calibration, selected-player focus locking, observed shuttle tracking, and report clip playback metadata. The backend should stop treating normalized image deltas and inferred shuttle lanes as production metrics; instead it should project tracked samples into court meters, explicitly choose a focused track from the setup selection, use observed shuttle samples when available, and expose clip windows to the frontend. The frontend should keep a single shared embedded player instead of rendering many iframes.

**Tech Stack:** FastAPI, Pydantic, OpenCV, NumPy, YOLO tracking, MediaPipe pose, React, TypeScript, YouTube embed iframe.

---

## Current Findings

- `backend/src/pipelines/cv/pipeline.py` computes `total_distance_meters` from normalized image-space deltas with a hard-coded `* 12.0` scale. That is not court-calibrated and will undercount badly when samples are sparse or the wrong track is chosen.
- `backend/src/analyses/service.py` still picks the tracked player by heuristic proximity if IDs do not line up. That means the selected setup detection is not a hard lock on the downstream analysis target.
- `backend/src/analyses/evidence.py` builds shuttle samples entirely from shot labels and timestamps, then Gaussian-smooths those inferred points. The Gaussian is only used for density smoothing, not shuttle detection.
- `frontend/src/App.tsx` currently links timestamps out to YouTube. It does not have report-side clip playback, clip windows, or a shared embedded player.

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/src/schemas/cv.py` | Modify | Add focused-track and observed-shuttle result types |
| `backend/src/schemas/report.py` | Modify | Add clip window metadata to shot events and pressure windows |
| `backend/src/schemas/analysis.py` | Modify | Persist selected track and shuttle-processing warnings on the record if needed |
| `backend/src/pipelines/cv/geometry.py` | Create | Pure court-space projection and distance summarization helpers |
| `backend/src/pipelines/cv/shuttle.py` | Create | Gaussian-based shuttle candidate detection and short-gap linking |
| `backend/src/pipelines/cv/pipeline.py` | Modify | Focus-lock selected player, project movement into meters, run shuttle tracking |
| `backend/src/analyses/service.py` | Modify | Pass selected player into CV, consume focused track and observed shuttle samples |
| `backend/src/analyses/evidence.py` | Modify | Prefer observed shuttle samples, degrade honestly to inferred fallback |
| `backend/tests/test_cv_geometry.py` | Create | Regression tests for court-space distance and player focus locking |
| `backend/tests/test_shuttle_tracking.py` | Create | Regression tests for Gaussian shuttle observation and evidence fallback |
| `backend/tests/test_analyses_api.py` | Modify | API-level regression coverage for selected-player focus and clip metadata |
| `frontend/src/types.ts` | Modify | Add clip window fields and clip-player state types |
| `frontend/src/App.tsx` | Modify | Add shared embedded clip player and event preview controls |
| `frontend/src/App.test.tsx` | Modify | Add report snippet regression coverage |

---

### Task 1: Add court-space calibration helpers and regression tests

**Files:**
- Create: `backend/src/pipelines/cv/geometry.py`
- Create: `backend/tests/test_cv_geometry.py`
- Modify: `backend/src/pipelines/cv/pipeline.py`

- [ ] **Step 1: Write the failing geometry tests**

Create `backend/tests/test_cv_geometry.py`:

```python
from pipelines.cv.geometry import (
    build_court_homography,
    summarize_projected_track,
)
from schemas import CourtModel, CourtPoint, MatchType, TrackSample


def test_summarize_projected_track_uses_court_meters_not_image_norms() -> None:
    court = CourtModel(
        confidence=0.9,
        adjustment_hint="",
        points=[
            CourtPoint(x=0.1, y=0.1),
            CourtPoint(x=0.9, y=0.1),
            CourtPoint(x=0.9, y=0.9),
            CourtPoint(x=0.1, y=0.9),
        ],
    )
    samples = [
        TrackSample(frame_index=0, timestamp_seconds=0.0, x=0.25, y=0.75),
        TrackSample(frame_index=1, timestamp_seconds=0.2, x=0.25, y=0.55),
        TrackSample(frame_index=2, timestamp_seconds=0.4, x=0.25, y=0.35),
    ]

    homography = build_court_homography(court, MatchType.MENS_SINGLES)
    summary = summarize_projected_track(samples, homography)

    assert summary.total_distance_meters > 5.0
    assert summary.total_distance_meters < 9.0


def test_selected_player_focus_lock_prefers_high_iou_track() -> None:
    from pipelines.cv.geometry import select_focused_track_id
    from schemas import DetectionBox, PlayerCandidate, PlayerTrackSummary

    selected_player = PlayerCandidate(
        player_id="detected-player-1",
        label="Detected Player A",
        side="near",
        focus_hint="Selected",
        bounding_box=DetectionBox(x=0.18, y=0.56, width=0.12, height=0.23),
    )
    track_a = PlayerTrackSummary(
        track_id="track-7",
        source_player_id=None,
        total_distance_meters=0.0,
        recovery_score=0,
        court_coverage_percent=0,
        change_of_direction_count=0,
        burst_count=0,
        directional_balance={"left": 0.5, "right": 0.5},
        zone_occupancy={"front": 0, "mid": 100, "rear": 0},
        heatmap=[],
        samples=[],
    )
    track_b = track_a.model_copy(update={"track_id": "track-11"})

    first_boxes = {
        "track-7": DetectionBox(x=0.19, y=0.57, width=0.12, height=0.22),
        "track-11": DetectionBox(x=0.62, y=0.31, width=0.1, height=0.2),
    }

    assert select_focused_track_id(selected_player, [track_a, track_b], first_boxes) == "track-7"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_cv_geometry.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing helper imports.

- [ ] **Step 3: Add the minimal geometry helper**

Create `backend/src/pipelines/cv/geometry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

import cv2
import numpy as np

from schemas import (
    CourtModel,
    DetectionBox,
    MatchType,
    PlayerCandidate,
    PlayerTrackSummary,
    TrackSample,
)


@dataclass(slots=True)
class ProjectedTrackSummary:
    total_distance_meters: float


def build_court_homography(court: CourtModel, match_type: MatchType) -> np.ndarray:
    # Map normalized image court corners to real badminton court meters.
    width_m = 5.18 if match_type in {MatchType.MENS_SINGLES, MatchType.WOMENS_SINGLES} else 6.10
    height_m = 13.40
    src = np.array([[p.x, p.y] for p in court.points], dtype=np.float32)
    dst = np.array(
        [[0.0, 0.0], [width_m, 0.0], [width_m, height_m], [0.0, height_m]],
        dtype=np.float32,
    )
    return cv2.getPerspectiveTransform(src, dst)


def summarize_projected_track(samples: list[TrackSample], homography: np.ndarray) -> ProjectedTrackSummary:
    if len(samples) < 2:
        return ProjectedTrackSummary(total_distance_meters=0.0)

    points = np.array([[[sample.x, sample.y]] for sample in samples], dtype=np.float32)
    projected = cv2.perspectiveTransform(points, homography)
    distance = 0.0
    for previous, current in zip(projected, projected[1:], strict=False):
        x1, y1 = previous[0]
        x2, y2 = current[0]
        distance += hypot(float(x2 - x1), float(y2 - y1))
    return ProjectedTrackSummary(total_distance_meters=distance)


def select_focused_track_id(
    selected_player: PlayerCandidate,
    tracks: list[PlayerTrackSummary],
    first_boxes: dict[str, DetectionBox],
) -> str | None:
    if selected_player.bounding_box is None:
        return None

    def iou(left: DetectionBox, right: DetectionBox) -> float:
        x1 = max(left.x, right.x)
        y1 = max(left.y, right.y)
        x2 = min(left.x + left.width, right.x + right.width)
        y2 = min(left.y + left.height, right.y + right.height)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        intersection = (x2 - x1) * (y2 - y1)
        left_area = left.width * left.height
        right_area = right.width * right.height
        return intersection / max(left_area + right_area - intersection, 1e-6)

    selected = selected_player.bounding_box
    best_track_id: str | None = None
    best_score = -1.0
    for track in tracks:
        candidate = first_boxes.get(track.track_id)
        if candidate is None:
            continue
        center_dx = (candidate.x + candidate.width / 2) - (selected.x + selected.width / 2)
        center_dy = (candidate.y + candidate.height / 2) - (selected.y + selected.height / 2)
        score = (iou(selected, candidate) * 10.0) - hypot(center_dx, center_dy)
        if score > best_score:
            best_score = score
            best_track_id = track.track_id
    return best_track_id
```

- [ ] **Step 4: Thread the helper into the CV pipeline**

Update `backend/src/pipelines/cv/pipeline.py` to replace:

```python
distance += hypot(dx, dy) * 12.0
```

with:

```python
homography = build_court_homography(court, match_type)
projected = summarize_projected_track(samples, homography)
total_distance_meters = round(projected.total_distance_meters, 1)
```

- [ ] **Step 5: Run the geometry tests again**

Run: `cd backend && .venv/bin/python -m pytest tests/test_cv_geometry.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/pipelines/cv/geometry.py backend/src/pipelines/cv/pipeline.py backend/tests/test_cv_geometry.py
git commit -m "feat: calibrate movement metrics in court-space meters"
```

---

### Task 2: Lock tracking to the selected setup player

**Files:**
- Modify: `backend/src/schemas/cv.py`
- Modify: `backend/src/pipelines/cv/pipeline.py`
- Modify: `backend/src/analyses/service.py`
- Modify: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Add the failing API regression**

Add to `backend/tests/test_analyses_api.py`:

```python
def test_analysis_uses_focused_track_for_selected_player(monkeypatch, tmp_path: Path) -> None:
    class FocusedPipeline(FakeCVPipeline):
        def track_players(self, video_path, court, match_type, *, selected_player=None, on_frame=None):
            return SimpleNamespace(
                focused_track_id="track-selected",
                tracks=[
                    SimpleNamespace(
                        track_id="track-selected",
                        source_player_id="detected-player-1",
                        total_distance_meters=31.6,
                        recovery_score=74,
                        court_coverage_percent=79,
                        change_of_direction_count=18,
                        burst_count=5,
                        directional_balance={"left": 0.47, "right": 0.53},
                        zone_occupancy={"front": 25, "mid": 46, "rear": 29},
                        heatmap=[],
                        samples=[],
                    ),
                    SimpleNamespace(
                        track_id="track-other",
                        source_player_id="detected-player-2",
                        total_distance_meters=4.9,
                        recovery_score=40,
                        court_coverage_percent=52,
                        change_of_direction_count=2,
                        burst_count=1,
                        directional_balance={"left": 0.1, "right": 0.9},
                        zone_occupancy={"front": 5, "mid": 10, "rear": 85},
                        heatmap=[],
                        samples=[],
                    ),
                ],
                warnings=[],
            )

    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(
            store=AnalysisStore(),
            media_artifact_pipeline=FakeMediaArtifactPipeline(tmp_path),
            cv_pipeline=FocusedPipeline(),
        ),
    )
```

Assert that the final report uses the `31.6` meter track and not the `4.9` meter bystander track.

- [ ] **Step 2: Run the regression**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py -k focused_track -v`
Expected: FAIL because `focused_track_id` is ignored.

- [ ] **Step 3: Extend the CV contract minimally**

Update `backend/src/schemas/cv.py`:

```python
class TrackingResult(BaseModel):
    tracks: list[PlayerTrackSummary]
    focused_track_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
```

Update `backend/src/pipelines/cv/pipeline.py` protocol:

```python
def track_players(
    self,
    video_path: str,
    court: CourtModel,
    match_type: MatchType,
    *,
    selected_player: PlayerCandidate | None = None,
    on_frame: FrameCallback | None = None,
) -> TrackingResult:
    pass
```

- [ ] **Step 4: Pass the selected player into CV and honor the focus lock**

Update `backend/src/analyses/service.py`:

```python
raw_result = self._cv_pipeline.track_players(
    record.source_video_path,
    record.court,
    record.match_type,
    selected_player=self._find_player(record, record.selected_player_id),
    on_frame=on_frame,
)
```

Then in `_select_track_for_player`:

```python
if tracking_result.focused_track_id is not None:
    for track in tracking_result.tracks:
        if track.track_id == tracking_result.focused_track_id:
            return track
```

- [ ] **Step 5: Focus-lock the hybrid pipeline**

Update `backend/src/pipelines/cv/pipeline.py` to collect first-frame boxes per track and compute:

```python
track_summaries = [
    self._summarize_track(track_id, samples) for track_id, samples in raw_tracks.items()
]
focused_track_id = (
    select_focused_track_id(selected_player, track_summaries, first_boxes)
    if selected_player is not None
    else None
)
```

Dim non-focused boxes in the live feed once `focused_track_id` is known.

- [ ] **Step 6: Run the regression again**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py -k focused_track -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/schemas/cv.py backend/src/pipelines/cv/pipeline.py backend/src/analyses/service.py backend/tests/test_analyses_api.py
git commit -m "feat: lock CV analysis to the selected player track"
```

---

### Task 3: Add Gaussian-based shuttle observation and observed-sample evidence

**Files:**
- Create: `backend/src/pipelines/cv/shuttle.py`
- Modify: `backend/src/schemas/cv.py`
- Modify: `backend/src/analyses/evidence.py`
- Modify: `backend/src/pipelines/cv/pipeline.py`
- Create: `backend/tests/test_shuttle_tracking.py`

- [ ] **Step 1: Write the failing shuttle regression tests**

Create `backend/tests/test_shuttle_tracking.py`:

```python
from analyses.evidence import build_shuttle_metrics
from schemas import HeatmapCell, PlayerTrackSummary, ShotSelectionMetrics, ShuttleSample


def test_build_shuttle_metrics_prefers_observed_samples() -> None:
    shot_selection = ShotSelectionMetrics(
        overview="",
        events=[],
    )
    observed = [
        ShuttleSample(timestamp_seconds=1.0, x=0.48, y=0.22, confidence=0.91, source="observed"),
        ShuttleSample(timestamp_seconds=1.2, x=0.51, y=0.27, confidence=0.88, source="observed"),
    ]

    metrics = build_shuttle_metrics(
        shot_selection,
        tracking_summary=None,
        observed_samples=observed,
    )

    assert metrics.samples[:2] == observed
    assert "directly observed" in metrics.uncertainty_note.lower()


def test_gaussian_shuttle_detector_rejects_large_player_blobs() -> None:
    from pipelines.cv.shuttle import score_shuttle_candidate

    small_fast = score_shuttle_candidate(area_px=18, speed_px=24, distance_to_track_px=32)
    large_blob = score_shuttle_candidate(area_px=340, speed_px=24, distance_to_track_px=32)

    assert small_fast > large_blob
```

- [ ] **Step 2: Run the shuttle tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_shuttle_tracking.py -v`
Expected: FAIL because `observed_samples` and shuttle helpers do not exist.

- [ ] **Step 3: Add the shuttle helper module**

Create `backend/src/pipelines/cv/shuttle.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import cv2

from schemas import CourtModel, DetectionBox, ShuttleSample


@dataclass(slots=True)
class ShuttleTrackingResult:
    samples: list[ShuttleSample]
    warnings: list[str]


def score_shuttle_candidate(*, area_px: float, speed_px: float, distance_to_track_px: float) -> float:
    size_score = max(0.0, 1.0 - min(area_px / 180.0, 1.0))
    speed_score = min(speed_px / 35.0, 1.0)
    separation_score = min(distance_to_track_px / 120.0, 1.0)
    return round((size_score * 0.5) + (speed_score * 0.35) + (separation_score * 0.15), 4)


def detect_shuttle_samples(
    video_path: str,
    court: CourtModel,
    *,
    focused_boxes: dict[int, DetectionBox],
) -> ShuttleTrackingResult:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        return ShuttleTrackingResult(samples=[], warnings=[f"Unable to open video at {video_path}"])

    ok, previous = capture.read()
    if not ok:
        capture.release()
        return ShuttleTrackingResult(samples=[], warnings=["Unable to read the first video frame."])

    frame_index = 1
    previous_blur = cv2.GaussianBlur(cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    samples: list[ShuttleSample] = []

    while True:
        ok, frame = capture.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        motion = cv2.absdiff(previous_blur, blurred)
        _, thresholded = cv2.threshold(motion, 18, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            score = score_shuttle_candidate(
                area_px=float(w * h),
                speed_px=float(max(w, h)),
                distance_to_track_px=40.0,
            )
            if score < 0.45:
                continue
            samples.append(
                ShuttleSample(
                    timestamp_seconds=frame_index / 30.0,
                    x=(x + w / 2) / frame.shape[1],
                    y=(y + h / 2) / frame.shape[0],
                    confidence=min(score, 0.95),
                    source="observed",
                )
            )
            break

        previous_blur = blurred
        frame_index += 1

    capture.release()
    warnings = [] if samples else ["Observed shuttle coverage was too sparse; falling back to inferred samples."]
    return ShuttleTrackingResult(samples=samples, warnings=warnings)
```

- [ ] **Step 4: Teach the pipeline and evidence layer about observed shuttle samples**

Update `backend/src/analyses/evidence.py`:

```python
def build_shuttle_metrics(
    shot_selection: ShotSelectionMetrics,
    *,
    tracking_summary: PlayerTrackSummary | None,
    observed_samples: list[ShuttleSample] | None = None,
) -> ShuttleMetrics:
    samples = observed_samples or _build_shuttle_samples(
        shot_selection,
        tracking_summary=tracking_summary,
    )
```

Use:

```python
uncertainty_note = (
    "Shuttle positions were directly observed in sampled frames, then Gaussian-smoothed into zone density."
    if observed_samples
    else "Shuttle positions are inferred from shot context and tracked-player movement, then smoothed into zone density."
)
```

- [ ] **Step 5: Call the shuttle detector after the focused track is known**

In `backend/src/pipelines/cv/pipeline.py`, once `focused_track_id` is resolved:

```python
focused_track = next(track for track in track_summaries if track.track_id == focused_track_id)
focused_track_boxes = {
    sample.frame_index: sample.bounding_box
    for sample in focused_track.samples
    if sample.bounding_box is not None
}
shuttle_result = detect_shuttle_samples(
    video_path,
    court,
    focused_boxes=focused_track_boxes,
)
```

Expose those observed samples through `TrackingResult` or a separate return field consumed by `AnalysisService`.

- [ ] **Step 6: Run shuttle tests again**

Run: `cd backend && .venv/bin/python -m pytest tests/test_shuttle_tracking.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/pipelines/cv/shuttle.py backend/src/pipelines/cv/pipeline.py backend/src/analyses/evidence.py backend/tests/test_shuttle_tracking.py
git commit -m "feat: add gaussian-based shuttle observation pipeline"
```

---

### Task 4: Add clip-window metadata to shot events and pressure windows

**Files:**
- Modify: `backend/src/schemas/report.py`
- Modify: `backend/src/analyses/service.py`
- Modify: `backend/src/analyses/evidence.py`
- Modify: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing API metadata regression**

Add to `backend/tests/test_analyses_api.py`:

```python
def test_report_events_include_clip_windows(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client)
    client.post(f"/api/analyses/{analysis_id}/run")
    _poll_until_terminal(client, analysis_id)

    report = client.get(f"/api/analyses/{analysis_id}/report").json()
    event = report["analytics_view"]["shot_selection"]["events"][0]

    assert event["clip_start_seconds"] < event["clip_end_seconds"]
    assert event["clip_start_seconds"] >= 0
```

- [ ] **Step 2: Run the regression**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py -k clip_windows -v`
Expected: FAIL because clip fields are missing.

- [ ] **Step 3: Extend the report schema**

Update `backend/src/schemas/report.py`:

```python
class ShotSelectionEvent(BaseModel):
    timestamp: str
    shot_type: str
    execution_score: int
    decision_score: int
    decision_quality: Literal["strong", "neutral", "poor"]
    recommendation: str
    evidence: str
    clip_start_seconds: int
    clip_end_seconds: int


class PressureWindow(BaseModel):
    label: str
    start_timestamp: str
    end_timestamp: str
    summary: str
    clip_start_seconds: int | None = None
    clip_end_seconds: int | None = None
```

- [ ] **Step 4: Populate clip windows when building shot events**

Update `_build_shot_event` in `backend/src/analyses/service.py`:

```python
def _build_shot_event(
    *,
    timestamp: str,
    shot_type: str,
    execution_score: int,
    decision_score: int,
    recommendation: str,
    evidence: str,
    clip_start_seconds: int,
    clip_end_seconds: int,
) -> ShotSelectionEvent:
    return ShotSelectionEvent(
        timestamp=timestamp,
        shot_type=shot_type,
        execution_score=execution_score,
        decision_score=decision_score,
        decision_quality=_decision_quality(decision_score),
        recommendation=recommendation,
        evidence=evidence,
        clip_start_seconds=clip_start_seconds,
        clip_end_seconds=clip_end_seconds,
    )
```

Compute windows in `_build_shot_selection`:

```python
event_seconds = int(fraction * duration)
clip_start = max(0, event_seconds - 3)
clip_end = min(int(duration), event_seconds + 3)
```

- [ ] **Step 5: Add pressure-window clip metadata**

Update `backend/src/analyses/evidence.py`:

```python
PressureWindow(
    label=current_label,
    start_timestamp=start_timestamp,
    end_timestamp=end_timestamp,
    summary=_pressure_summary(current_label, start_timestamp, end_timestamp),
    clip_start_seconds=max(0, int(_parse_timestamp(start_timestamp)) - 2),
    clip_end_seconds=int(_parse_timestamp(end_timestamp)) + 2,
)
```

- [ ] **Step 6: Run the regression again**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analyses_api.py -k clip_windows -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/schemas/report.py backend/src/analyses/service.py backend/src/analyses/evidence.py backend/tests/test_analyses_api.py
git commit -m "feat: add clip window metadata to report events"
```

---

### Task 5: Add a shared embedded YouTube clip viewer to the report

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing frontend regression**

Add to `frontend/src/App.test.tsx`:

```tsx
test("loads a shared embedded clip player for the selected shot event", async () => {
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);
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
        message: "Analysis started. Connect to the feed for live updates.",
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
      body: {
        ...completedReport,
        analytics_view: {
          ...completedReport.analytics_view,
          shot_selection: {
            ...completedReport.analytics_view.shot_selection,
            events: [
              {
                ...completedReport.analytics_view.shot_selection.events[0],
                clip_start_seconds: 9,
                clip_end_seconds: 15,
              },
            ],
          },
        },
      },
    },
  ]);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));
  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument();
  });
  fireEvent.click(screen.getByRole("button", { name: /player 1/i }));
  fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }));
  MockEventSource.latest().emitDone();

  fireEvent.click(screen.getByRole("button", { name: /preview clip/i }));

  const iframe = await screen.findByTitle(/shot clip preview/i);
  expect(iframe).toHaveAttribute("src", expect.stringContaining("/embed/"));
  expect(iframe).toHaveAttribute("src", expect.stringContaining("start="));
});
```

- [ ] **Step 2: Run the regression**

Run: `cd frontend && pnpm test -- App.test.tsx`
Expected: FAIL because there is no clip preview UI.

- [ ] **Step 3: Extend the frontend types**

Update `frontend/src/types.ts`:

```typescript
export interface ShotSelectionEvent {
  timestamp: string;
  shot_type: string;
  execution_score: number;
  decision_score: number;
  decision_quality: "strong" | "neutral" | "poor";
  recommendation: string;
  evidence: string;
  clip_start_seconds: number;
  clip_end_seconds: number;
}
```

- [ ] **Step 4: Add a single shared player, not one iframe per row**

Update `frontend/src/App.tsx`:

```tsx
const [activeClip, setActiveClip] = useState<ShotSelectionEvent | null>(null);

function extractYouTubeVideoId(url: string): string | null {
  const parsed = new URL(url);
  if (parsed.hostname.includes("youtu.be")) {
    return parsed.pathname.slice(1) || null;
  }
  return parsed.searchParams.get("v");
}

function buildEmbedUrl(baseUrl: string, event: ShotSelectionEvent): string | null {
  const videoId = extractYouTubeVideoId(baseUrl);
  if (!videoId) return null;
  return `https://www.youtube.com/embed/${videoId}?start=${event.clip_start_seconds}&end=${event.clip_end_seconds}&playsinline=1&rel=0`;
}
```

Render one player above the event list:

```tsx
{activeClip ? (
  <iframe
    title="Shot clip preview"
    className="w-full aspect-video rounded-xl border border-slate-200"
    src={buildEmbedUrl(youtubeUrl, activeClip) ?? undefined}
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowFullScreen
  />
) : null}
```

Add a per-card button:

```tsx
<button onClick={() => setActiveClip(event)} type="button">
  Preview clip
</button>
```

- [ ] **Step 5: Run the frontend regression again**

Run: `cd frontend && pnpm test -- App.test.tsx`
Expected: PASS

- [ ] **Step 6: Build the frontend**

Run: `cd frontend && pnpm build`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add embedded report clip previews"
```

---

### Task 6: Full verification and smoke checks

**Files:**
- Modify as needed from prior tasks

- [ ] **Step 1: Run backend tests**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: PASS

- [ ] **Step 2: Run backend lint**

Run: `cd backend && .venv/bin/python -m ruff check src tests`
Expected: PASS

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && pnpm test`
Expected: PASS

- [ ] **Step 4: Run frontend build**

Run: `cd frontend && pnpm build`
Expected: PASS

- [ ] **Step 5: Run a mock smoke test**

Run: `make run-mock`

Verify:

```text
1. Setup selection chooses a player.
2. Completed report shows a realistic movement distance from the focused fake track, not a placeholder low value.
3. Shot events expose Preview clip controls and load the shared iframe.
```

- [ ] **Step 6: Run a real-pipeline smoke test**

Run: `make run`

Verify:

```text
1. The live feed locks visually onto the selected player after setup.
2. Distance traveled is directionally plausible for badminton footage and no longer stuck in single-digit meters.
3. Shuttle heatmap summary mentions observed coverage when detection succeeds.
4. Clicking a shot event opens the embedded clip window at the right rally timestamp.
```

- [ ] **Step 7: Commit any smoke-test fixes**

```bash
git add backend/src frontend/src backend/tests frontend/src/App.test.tsx
git commit -m "fix: polish calibrated tracking and clip preview flow"
```

---

## Self-Review

- Spec coverage: movement calibration, selected-player focus, Gaussian shuttle detection, and embedded clip playback are each covered by separate tasks with explicit verification.
- Placeholder scan: no `TODO`, `TBD`, or “appropriate handling” placeholders remain.
- Type consistency: the plan uses `focused_track_id`, `observed_samples`, and `clip_start_seconds` / `clip_end_seconds` consistently across schema, service, and frontend tasks.
