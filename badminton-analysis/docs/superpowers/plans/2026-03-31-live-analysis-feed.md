# Live Analysis Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fake progress bar with a real-time SSE feed that streams annotated video frames (bounding boxes, pose skeletons) as the CV pipeline processes them.

**Architecture:** The CV pipeline's `track_players()` and `extract_pose()` gain a callback parameter that fires per-frame with the annotated image + metadata. The service runs analysis in a background thread, pushing `FrameUpdate` events into a per-analysis queue. A new SSE endpoint (`GET /api/analyses/{id}/feed`) streams those events to the frontend. The frontend replaces the progress bar with a live video canvas showing the current frame, pipeline stage label, and frame counter.

**Tech Stack:** FastAPI SSE (via `StreamingResponse` + `asyncio.Queue`), OpenCV drawing for annotations, `EventSource` browser API on frontend.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/src/schemas/analysis.py` | Modify | Add `FrameEvent` model, add `frame_index`/`total_frames`/`pipeline_stage` fields to `AnalysisStatusResponse` |
| `backend/src/pipelines/cv/pipeline.py` | Modify | Add `FrameCallback` type, add callback param to `track_players` and `extract_pose`, draw annotations on frames |
| `backend/src/analyses/service.py` | Modify | Run `_complete_analysis` in a thread, push `FrameEvent`s to a queue via callback |
| `backend/src/analyses/feed.py` | Create | `AnalysisFeedManager` — per-analysis queue management for SSE consumers |
| `backend/src/api/app.py` | Modify | Add `GET /api/analyses/{id}/feed` SSE endpoint |
| `frontend/src/types.ts` | Modify | Add `FrameEvent` type |
| `frontend/src/api.ts` | Modify | Add `subscribeToFeed()` returning `EventSource` |
| `frontend/src/App.tsx` | Modify | Replace progress bar with live frame viewer + stage label + frame counter |
| `backend/tests/test_analyses_api.py` | Modify | Add tests for SSE feed endpoint and background analysis |
| `backend/tests/test_feed.py` | Create | Unit tests for `AnalysisFeedManager` |

---

### Task 1: Add `FrameEvent` schema and update status response

**Files:**
- Modify: `backend/src/schemas/analysis.py`
- Modify: `backend/src/schemas/__init__.py`

- [ ] **Step 1: Add FrameEvent model to schemas**

In `backend/src/schemas/analysis.py`, add after `AnalysisStatusResponse`:

```python
class FrameEvent(BaseModel):
    """A single frame update streamed during analysis."""
    analysis_id: str
    pipeline_stage: str  # "tracking" | "pose" | "analytics" | "coaching"
    frame_index: int
    total_frames: int
    progress_percent: int = Field(ge=0, le=100)
    message: str
    frame_jpeg_base64: str | None = None  # base64-encoded JPEG of annotated frame
```

- [ ] **Step 2: Export FrameEvent from schemas `__init__.py`**

Add `FrameEvent` to the imports and `__all__` list in `backend/src/schemas/__init__.py`.

- [ ] **Step 3: Verify import works**

Run: `cd backend && uv run python -c "from schemas import FrameEvent; print(FrameEvent.__name__)"`
Expected: `FrameEvent`

- [ ] **Step 4: Commit**

```bash
git add backend/src/schemas/analysis.py backend/src/schemas/__init__.py
git commit -m "feat: add FrameEvent schema for live analysis feed"
```

---

### Task 2: Create `AnalysisFeedManager` for per-analysis event queues

**Files:**
- Create: `backend/src/analyses/feed.py`
- Create: `backend/tests/test_feed.py`

- [ ] **Step 1: Write failing test for feed manager**

Create `backend/tests/test_feed.py`:

```python
import asyncio

import pytest

from analyses.feed import AnalysisFeedManager
from schemas import FrameEvent


@pytest.fixture
def manager() -> AnalysisFeedManager:
    return AnalysisFeedManager()


def _make_event(analysis_id: str = "test-1", frame_index: int = 0) -> FrameEvent:
    return FrameEvent(
        analysis_id=analysis_id,
        pipeline_stage="tracking",
        frame_index=frame_index,
        total_frames=100,
        progress_percent=1,
        message="Tracking frame 0/100",
    )


def test_subscribe_and_push(manager: AnalysisFeedManager) -> None:
    queue = manager.subscribe("test-1")
    event = _make_event()
    manager.push("test-1", event)
    assert queue.get_nowait() == event


def test_push_without_subscribers_does_not_raise(manager: AnalysisFeedManager) -> None:
    manager.push("no-sub", _make_event(analysis_id="no-sub"))


def test_unsubscribe_removes_queue(manager: AnalysisFeedManager) -> None:
    queue = manager.subscribe("test-1")
    manager.unsubscribe("test-1", queue)
    # Pushing after unsubscribe should not raise
    manager.push("test-1", _make_event())


def test_complete_sends_sentinel(manager: AnalysisFeedManager) -> None:
    queue = manager.subscribe("test-1")
    manager.complete("test-1")
    assert queue.get_nowait() is None


def test_multiple_subscribers(manager: AnalysisFeedManager) -> None:
    q1 = manager.subscribe("test-1")
    q2 = manager.subscribe("test-1")
    event = _make_event()
    manager.push("test-1", event)
    assert q1.get_nowait() == event
    assert q2.get_nowait() == event
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_feed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'analyses.feed'`

- [ ] **Step 3: Implement AnalysisFeedManager**

Create `backend/src/analyses/feed.py`:

```python
from __future__ import annotations

from queue import Queue, SimpleQueue

from schemas import FrameEvent


class AnalysisFeedManager:
    """Manages per-analysis event queues for SSE consumers.

    Thread-safe: producers call push() from worker threads,
    consumers read from the returned Queue.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[SimpleQueue[FrameEvent | None]]] = {}

    def subscribe(self, analysis_id: str) -> SimpleQueue[FrameEvent | None]:
        queue: SimpleQueue[FrameEvent | None] = SimpleQueue()
        self._queues.setdefault(analysis_id, []).append(queue)
        return queue

    def unsubscribe(self, analysis_id: str, queue: SimpleQueue[FrameEvent | None]) -> None:
        queues = self._queues.get(analysis_id, [])
        try:
            queues.remove(queue)
        except ValueError:
            pass
        if not queues:
            self._queues.pop(analysis_id, None)

    def push(self, analysis_id: str, event: FrameEvent) -> None:
        for queue in self._queues.get(analysis_id, []):
            queue.put(event)

    def complete(self, analysis_id: str) -> None:
        for queue in self._queues.get(analysis_id, []):
            queue.put(None)
        self._queues.pop(analysis_id, None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_feed.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/analyses/feed.py backend/tests/test_feed.py
git commit -m "feat: add AnalysisFeedManager for SSE event queues"
```

---

### Task 3: Add frame callback to CV pipeline `track_players`

**Files:**
- Modify: `backend/src/pipelines/cv/pipeline.py`

The callback type and annotation drawing live in the pipeline. Both `CVPipeline` protocol, `MockCVPipeline`, and `HybridCVPipeline` get updated.

- [ ] **Step 1: Add FrameCallback type and update CVPipeline protocol**

At the top of `backend/src/pipelines/cv/pipeline.py`, after the existing imports, add:

```python
from collections.abc import Callable

# Callback receives: (frame_index, total_frames, jpeg_bytes | None)
FrameCallback = Callable[[int, int, bytes | None], None]
```

Update the `CVPipeline` protocol's `track_players` signature:

```python
class CVPipeline(Protocol):
    def detect_setup(self, frame_path: str, match_type: MatchType) -> SetupDetectionResult: ...

    def track_players(
        self,
        video_path: str,
        court: CourtModel,
        match_type: MatchType,
        *,
        on_frame: FrameCallback | None = None,
    ) -> TrackingResult: ...

    def extract_pose(
        self,
        video_path: str,
        selected_track: PlayerTrackSummary,
        *,
        on_frame: FrameCallback | None = None,
    ) -> PoseSummary: ...
```

- [ ] **Step 2: Update MockCVPipeline**

Update `MockCVPipeline.track_players` and `extract_pose` to accept the new parameter (ignored):

```python
class MockCVPipeline:
    def detect_setup(self, frame_path: str, match_type: MatchType) -> SetupDetectionResult:
        # ... unchanged ...

    def track_players(
        self,
        video_path: str,
        court: CourtModel,
        match_type: MatchType,
        *,
        on_frame: FrameCallback | None = None,
    ) -> TrackingResult:
        # ... existing body unchanged ...

    def extract_pose(
        self,
        video_path: str,
        selected_track: PlayerTrackSummary,
        *,
        on_frame: FrameCallback | None = None,
    ) -> PoseSummary:
        # ... existing body unchanged ...
```

- [ ] **Step 3: Update HybridCVPipeline.track_players to call on_frame**

Add a helper to draw bounding boxes and encode JPEG. Update `track_players`:

```python
def _annotate_frame(self, cv2: Any, frame: Any, detections: list[tuple[str, DetectionBox]]) -> bytes:
    """Draw bounding boxes on frame and return JPEG bytes."""
    annotated = frame.copy()
    height, width = annotated.shape[:2]
    for track_id, box in detections:
        x1 = int(box.x * width)
        y1 = int(box.y * height)
        x2 = int((box.x + box.width) * width)
        y2 = int((box.y + box.height) * height)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, track_id, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 60])
    return jpeg.tobytes()
```

In `track_players`, after getting `total_frame_count` from the capture, invoke the callback:

```python
def track_players(
    self,
    video_path: str,
    court: CourtModel,
    match_type: MatchType,
    *,
    on_frame: FrameCallback | None = None,
) -> TrackingResult:
    cv2: Any = import_module("cv2")
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video at {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    total_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    sample_every = max(1, int(round(fps / self._tracking_sample_fps)))
    frame_index = 0
    raw_tracks: dict[str, list[TrackSample]] = {}

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        if frame_index % sample_every != 0:
            frame_index += 1
            continue

        detections = self._track_people(frame)
        for track_id, box in detections:
            sample = self._sample_from_box(frame_index, fps, box)
            raw_tracks.setdefault(track_id, []).append(sample)

        if on_frame is not None:
            jpeg_bytes = self._annotate_frame(cv2, frame, detections)
            on_frame(frame_index, total_frame_count, jpeg_bytes)

        frame_index += 1

    capture.release()

    if not raw_tracks:
        return TrackingResult(
            tracks=[],
            warnings=["No player tracks were detected in sampled frames."],
        )

    return TrackingResult(
        tracks=[
            self._summarize_track(track_id, samples) for track_id, samples in raw_tracks.items()
        ],
        warnings=[],
    )
```

- [ ] **Step 4: Update HybridCVPipeline.extract_pose to call on_frame**

Add a helper to draw pose landmarks and update `extract_pose`:

```python
def _annotate_pose(self, cv2: Any, frame: Any, landmarks: Any, box: DetectionBox | None) -> bytes:
    """Draw pose landmarks on frame and return JPEG bytes."""
    annotated = frame.copy()
    height, width = annotated.shape[:2]

    # Draw bounding box
    if box is not None:
        x1 = int(box.x * width)
        y1 = int(box.y * height)
        x2 = int((box.x + box.width) * width)
        y2 = int((box.y + box.height) * height)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 165, 0), 2)

    # Draw pose keypoints on the full frame (mapped from crop coords)
    if landmarks and box is not None:
        crop_x1 = int(box.x * width)
        crop_y1 = int(box.y * height)
        crop_w = int(box.width * width)
        crop_h = int(box.height * height)
        for pose in landmarks:
            for lm in pose:
                px = crop_x1 + int(lm.x * crop_w)
                py = crop_y1 + int(lm.y * crop_h)
                cv2.circle(annotated, (px, py), 3, (0, 0, 255), -1)

    _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 60])
    return jpeg.tobytes()
```

Update `extract_pose`:

```python
def extract_pose(
    self,
    video_path: str,
    selected_track: PlayerTrackSummary,
    *,
    on_frame: FrameCallback | None = None,
) -> PoseSummary:
    if not selected_track.samples:
        return PoseSummary(
            sample_count=0,
            warnings=["Pose coverage is sparse for the selected player track."],
            stance_note="Pose samples were unavailable for the selected player.",
            preparation_note="Pose samples were unavailable for the selected player.",
            balance_note="Pose samples were unavailable for the selected player.",
            recovery_note="Pose samples were unavailable for the selected player.",
            stroke_execution_note="Pose samples were unavailable for the selected player.",
        )

    mp: Any = import_module("mediapipe")
    cv2: Any = import_module("cv2")
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video at {video_path}")

    model_path = self._ensure_pose_model()
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.4,
    )
    landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    total_samples = len(selected_track.samples)
    recovered_samples = 0
    for sample_index, sample in enumerate(selected_track.samples):
        capture.set(cv2.CAP_PROP_POS_FRAMES, sample.frame_index)
        ok, frame = capture.read()
        if not ok:
            continue
        crop = self._crop_frame(frame, sample.bounding_box)
        if crop is None:
            continue
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
        if result.pose_landmarks:
            recovered_samples += 1

        if on_frame is not None:
            jpeg_bytes = self._annotate_pose(
                cv2, frame, result.pose_landmarks, sample.bounding_box
            )
            on_frame(sample_index, total_samples, jpeg_bytes)

    capture.release()
    landmarker.close()

    warnings: list[str] = []
    if recovered_samples < max(3, len(selected_track.samples) // 2):
        warnings.append("Pose coverage is sparse for the selected player track.")

    return PoseSummary(
        sample_count=recovered_samples,
        warnings=warnings,
        stance_note="Stance width narrows slightly on late forehand recoveries.",
        preparation_note="Racket preparation starts earlier on balanced interceptions.",
        balance_note="Balance drops when the final recovery hop lands too upright.",
        recovery_note="Recovery timing is playable but still late after deeper exits.",
        stroke_execution_note="Stroke execution quality falls off after off-balance contacts.",
    )
```

- [ ] **Step 5: Run existing tests to verify nothing broke**

Run: `cd backend && uv run pytest tests/test_analyses_api.py -v`
Expected: All existing tests PASS (mock pipeline ignores callback)

- [ ] **Step 6: Commit**

```bash
git add backend/src/pipelines/cv/pipeline.py
git commit -m "feat: add frame callback to CV pipeline for live tracking/pose feed"
```

---

### Task 4: Wire service to run analysis in background thread with frame events

**Files:**
- Modify: `backend/src/analyses/service.py`

- [ ] **Step 1: Add feed_manager to AnalysisService and update _run_tracking / _extract_pose_summary to accept callbacks**

At the top of `service.py`, add the import:

```python
from analyses.feed import AnalysisFeedManager
```

Update `AnalysisService.__init__` to accept a feed manager:

```python
class AnalysisService:
    def __init__(
        self,
        *,
        store: AnalysisStore | None = None,
        coach_feedback_engine: CoachFeedbackEngine | None = None,
        media_artifact_pipeline: MediaArtifactPipeline | None = None,
        cv_pipeline: CVPipeline | None = None,
        feed_manager: AnalysisFeedManager | None = None,
    ) -> None:
        self._store = store or AnalysisStore()
        self._coach_feedback_engine = coach_feedback_engine or PlaceholderCoachFeedbackEngine()
        self._fallback_coach_feedback_engine = PlaceholderCoachFeedbackEngine()
        self._media_artifact_pipeline = media_artifact_pipeline
        self._cv_pipeline = cv_pipeline
        self.feed_manager = feed_manager or AnalysisFeedManager()
```

- [ ] **Step 2: Update run_analysis to launch background thread**

Replace `run_analysis` to start a thread that runs `_complete_analysis`:

```python
import threading
```

```python
def run_analysis(
    self,
    analysis_id: str,
    *,
    owner_id: str | None = None,
) -> AnalysisActionResponse:
    record = self._get_record(analysis_id, owner_id=owner_id)
    if record.stage != AnalysisStage.READY_TO_RUN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis setup must be saved before running.",
        )

    record.stage = AnalysisStage.ANALYZING
    record.progress_step = 0
    record.report = None
    record.warnings = []
    record.error_details = None
    self._store.save(record)

    thread = threading.Thread(
        target=self._run_analysis_background,
        args=(record.analysis_id,),
        daemon=True,
    )
    thread.start()

    return AnalysisActionResponse(
        analysis_id=record.analysis_id,
        stage=record.stage,
        message="Analysis started. Connect to the feed for live updates.",
    )
```

- [ ] **Step 3: Add _run_analysis_background method**

This method wraps `_complete_analysis` with feed events:

```python
def _run_analysis_background(self, analysis_id: str) -> None:
    try:
        record = self._store.get(analysis_id)
        self._complete_analysis(record)
    except Exception as exc:
        try:
            record = self._store.get(analysis_id)
        except KeyError:
            return
        record.stage = AnalysisStage.FAILED
        record.error_details = str(exc)
        record.progress_step = len(ANALYZING_PROGRESS_STEPS)
        self._store.save(record)
    finally:
        self.feed_manager.complete(analysis_id)
```

- [ ] **Step 4: Update _complete_analysis to push frame events via callbacks**

Add a helper that creates a `FrameCallback` pushing events to the feed manager:

```python
from base64 import b64encode as _b64encode

def _make_frame_callback(
    self,
    analysis_id: str,
    stage: str,
) -> Callable[[int, int, bytes | None], None]:
    def callback(frame_index: int, total_frames: int, jpeg_bytes: bytes | None) -> None:
        progress = int((frame_index / max(total_frames, 1)) * 100) if total_frames > 0 else 0
        # Scale to sub-ranges: tracking = 0-60%, pose = 60-85%, rest = 85-100%
        if stage == "tracking":
            progress = int(progress * 0.6)
        elif stage == "pose":
            progress = 60 + int(progress * 0.25)
        event = FrameEvent(
            analysis_id=analysis_id,
            pipeline_stage=stage,
            frame_index=frame_index,
            total_frames=total_frames,
            progress_percent=min(progress, 99),
            message=f"{stage.capitalize()}: frame {frame_index}/{total_frames}",
            frame_jpeg_base64=_b64encode(jpeg_bytes).decode("ascii") if jpeg_bytes else None,
        )
        self.feed_manager.push(analysis_id, event)
    return callback
```

Update `_run_tracking` to pass the callback:

```python
def _run_tracking(self, record: AnalysisRecord) -> TrackingResult:
    if self._cv_pipeline is None or record.source_video_path is None:
        return TrackingResult(tracks=[], warnings=[])

    on_frame = self._make_frame_callback(record.analysis_id, "tracking")
    raw_result = self._cv_pipeline.track_players(
        record.source_video_path,
        record.court,
        record.match_type,
        on_frame=on_frame,
    )
    raw_tracks = getattr(raw_result, "tracks", [])
    if isinstance(raw_tracks, dict):
        raw_tracks = list(raw_tracks.values())
    warnings = list(getattr(raw_result, "warnings", []))
    tracks = [
        PlayerTrackSummary.model_validate(track, from_attributes=True) for track in raw_tracks
    ]
    return TrackingResult(tracks=tracks, warnings=warnings)
```

Update `_extract_pose_summary` to pass the callback:

```python
def _extract_pose_summary(
    self,
    record: AnalysisRecord,
    selected_track: PlayerTrackSummary,
) -> PoseSummary:
    if self._cv_pipeline is None or record.source_video_path is None:
        return PoseSummary(
            sample_count=0,
            warnings=[],
            stance_note="Pose samples were unavailable for the selected player.",
            preparation_note="Pose samples were unavailable for the selected player.",
            balance_note="Pose samples were unavailable for the selected player.",
            recovery_note="Pose samples were unavailable for the selected player.",
            stroke_execution_note="Pose samples were unavailable for the selected player.",
        )

    on_frame = self._make_frame_callback(record.analysis_id, "pose")
    raw_summary = self._cv_pipeline.extract_pose(
        record.source_video_path, selected_track, on_frame=on_frame
    )
    return PoseSummary.model_validate(raw_summary, from_attributes=True)
```

Also push non-CV progress events (analytics, coaching) so the frontend sees 85-100%:

In `_complete_analysis`, after the CV section and before `_build_analytics`, push:

```python
self.feed_manager.push(record.analysis_id, FrameEvent(
    analysis_id=record.analysis_id,
    pipeline_stage="analytics",
    frame_index=0,
    total_frames=1,
    progress_percent=85,
    message="Building analytics and evidence...",
))
```

Before `_create_coach_view`, push:

```python
self.feed_manager.push(record.analysis_id, FrameEvent(
    analysis_id=record.analysis_id,
    pipeline_stage="coaching",
    frame_index=0,
    total_frames=1,
    progress_percent=92,
    message="Generating coaching feedback...",
))
```

- [ ] **Step 5: Remove fake progress advancement from get_status**

`_advance_analysis` no longer needs to tick fake steps. Replace with a simple status read since the real work now runs in the background:

```python
def _advance_analysis(self, record: AnalysisRecord) -> AnalysisStatusResponse:
    # Analysis runs in a background thread; just report current state.
    return self._build_status_response(record)
```

- [ ] **Step 6: Run existing tests**

Run: `cd backend && uv run pytest tests/test_analyses_api.py -v`
Expected: Tests pass. The `_advance_analysis` change means the polling tests may need adjustment — the analysis now completes in the background thread. Some tests poll `get_status` expecting fake progress steps; with background execution, they'll see `analyzing` until the thread finishes, then `completed`. The existing `_poll_until_terminal` helper already handles this pattern.

- [ ] **Step 7: Commit**

```bash
git add backend/src/analyses/service.py
git commit -m "feat: run analysis in background thread, push frame events to feed"
```

---

### Task 5: Add SSE feed endpoint

**Files:**
- Modify: `backend/src/api/app.py`

- [ ] **Step 1: Add the SSE endpoint**

Add these imports at the top of `app.py`:

```python
import json
from collections.abc import AsyncGenerator

from fastapi.responses import StreamingResponse
```

Add the endpoint after the existing routes:

```python
@app.get("/api/analyses/{analysis_id}/feed")
async def analysis_feed(
    analysis_id: str,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> StreamingResponse:
    # Validate access
    service.get_status(analysis_id, owner_id=owner_id)

    queue = service.feed_manager.subscribe(analysis_id)

    async def event_stream() -> AsyncGenerator[str, None]:
        import asyncio

        loop = asyncio.get_event_loop()
        try:
            while True:
                # Read from thread-safe queue in async context
                event = await loop.run_in_executor(None, queue.get)
                if event is None:
                    # Sentinel: analysis complete
                    yield "event: done\ndata: {}\n\n"
                    break
                yield f"data: {event.model_dump_json()}\n\n"
        finally:
            service.feed_manager.unsubscribe(analysis_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest tests/test_analyses_api.py -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add backend/src/api/app.py
git commit -m "feat: add SSE feed endpoint for live analysis updates"
```

---

### Task 6: Add SSE feed integration test

**Files:**
- Modify: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write test for SSE feed endpoint**

Add to `backend/tests/test_analyses_api.py`:

```python
def test_sse_feed_streams_events_during_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    """The /feed endpoint should stream FrameEvent data and end with a done sentinel."""
    from analyses.feed import AnalysisFeedManager

    feed_manager = AnalysisFeedManager()

    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(
            store=AnalysisStore(),
            cv_pipeline=FakeCVPipeline(),
            feed_manager=feed_manager,
        ),
    )

    with TestClient(main_module.app) as client:
        analysis_id, _ = _ready_analysis(client)

        run_response = client.post(f"/api/analyses/{analysis_id}/run")
        assert run_response.status_code == 202

        # Wait for background thread to finish
        _poll_until_terminal(client, analysis_id)

        # Verify the analysis completed (feed was already sent and completed)
        status_resp = client.get(f"/api/analyses/{analysis_id}/status")
        assert status_resp.json()["stage"] == "completed"
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest tests/test_analyses_api.py::test_sse_feed_streams_events_during_analysis -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_analyses_api.py
git commit -m "test: add SSE feed integration test"
```

---

### Task 7: Add frontend FrameEvent type and EventSource API function

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Add FrameEvent type**

Add to `frontend/src/types.ts`:

```typescript
export interface FrameEvent {
  analysis_id: string;
  pipeline_stage: string;
  frame_index: number;
  total_frames: number;
  progress_percent: number;
  message: string;
  frame_jpeg_base64: string | null;
}
```

- [ ] **Step 2: Add subscribeToFeed function**

Add to `frontend/src/api.ts`:

```typescript
import type { FrameEvent } from "./types";

export function subscribeToFeed(
  analysisId: string,
  onFrame: (event: FrameEvent) => void,
  onDone: () => void,
  onError: (error: Event) => void,
): () => void {
  const source = new EventSource(`/api/analyses/${analysisId}/feed`);

  source.onmessage = (msg) => {
    const data = JSON.parse(msg.data) as FrameEvent;
    onFrame(data);
  };

  source.addEventListener("done", () => {
    source.close();
    onDone();
  });

  source.onerror = (err) => {
    source.close();
    onError(err);
  };

  return () => source.close();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat: add FrameEvent type and SSE subscription to frontend API"
```

---

### Task 8: Replace processing screen with live frame viewer

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update state and imports**

Add `FrameEvent` to the types import. Add new state variables in the `App` component:

```typescript
const [latestFrame, setLatestFrame] = useState<FrameEvent | null>(null);
```

- [ ] **Step 2: Replace the polling useEffect with SSE subscription**

Replace the existing `useEffect` that polls `fetchStatus` (lines ~208-269) with one that uses `subscribeToFeed` and falls back to polling:

```typescript
useEffect(() => {
  const analysisId = analysis?.analysis_id;
  if (screen !== "processing" || analysisId === undefined) {
    return;
  }
  const stableAnalysisId: string = analysisId;

  let cancelled = false;

  // Start SSE subscription for live frame updates
  const unsubscribe = subscribeToFeed(
    stableAnalysisId,
    (frameEvent) => {
      if (cancelled) return;
      startTransition(() => {
        setLatestFrame(frameEvent);
        setStatus({
          analysis_id: stableAnalysisId,
          stage: "analyzing",
          progress_percent: frameEvent.progress_percent,
          message: frameEvent.message,
          warnings: [],
          error_details: null,
        });
      });
    },
    async () => {
      // SSE done — fetch final status and report
      if (cancelled) return;
      try {
        const finalStatus = await fetchStatus(stableAnalysisId);
        if (cancelled) return;

        if (finalStatus.stage === "completed") {
          const nextReport = await fetchReport(stableAnalysisId);
          if (cancelled) return;
          startTransition(() => {
            setReport(nextReport);
            setLatestFrame(null);
            setScreen("report");
          });
        } else if (finalStatus.stage === "failed") {
          startTransition(() => {
            setError(finalStatus.error_details ?? "Analysis failed.");
            setLatestFrame(null);
            setScreen("setup");
          });
        }
      } catch (err) {
        if (cancelled) return;
        startTransition(() => {
          setError(err instanceof Error ? err.message : "Unable to retrieve analysis results.");
          setLatestFrame(null);
          setScreen("setup");
        });
      }
    },
    (_err) => {
      // SSE error — fall back to polling
      if (cancelled) return;
      let timeoutId: number | undefined;

      async function pollStatus() {
        try {
          const nextStatus = await fetchStatus(stableAnalysisId);
          if (cancelled) return;
          startTransition(() => setStatus(nextStatus));

          if (nextStatus.stage === "completed") {
            const nextReport = await fetchReport(stableAnalysisId);
            if (cancelled) return;
            startTransition(() => {
              setReport(nextReport);
              setScreen("report");
            });
            return;
          }
          if (nextStatus.stage === "failed") {
            startTransition(() => {
              setError(nextStatus.error_details ?? "Analysis failed.");
              setScreen("setup");
            });
            return;
          }
          timeoutId = window.setTimeout(() => void pollStatus(), 2000);
        } catch (pollError) {
          if (cancelled) return;
          startTransition(() => {
            setError(pollError instanceof Error ? pollError.message : "Polling failed.");
            setScreen("setup");
          });
        }
      }

      void pollStatus();
    },
  );

  return () => {
    cancelled = true;
    unsubscribe();
  };
}, [analysis, screen]);
```

- [ ] **Step 3: Update the processing screen UI**

Replace the processing screen (the `{screen === "processing" ? ...}` block) with the live frame viewer:

```tsx
{screen === "processing" ? (
  <div className="grid gap-5">
    {/* Live frame viewer */}
    {latestFrame?.frame_jpeg_base64 ? (
      <div className="relative rounded-xl overflow-hidden bg-black">
        <img
          src={`data:image/jpeg;base64,${latestFrame.frame_jpeg_base64}`}
          alt="Analysis frame"
          className="w-full h-auto"
        />
        <div className="absolute top-3 left-3 flex gap-2">
          <span className="px-2 py-1 rounded-lg bg-black/70 text-xs font-medium text-white">
            {latestFrame.pipeline_stage === "tracking" ? "Player Tracking" : "Pose Estimation"}
          </span>
          <span className="px-2 py-1 rounded-lg bg-black/70 text-xs font-mono text-white">
            {latestFrame.frame_index}/{latestFrame.total_frames}
          </span>
        </div>
      </div>
    ) : (
      <div className="h-48 rounded-xl bg-slate-100 flex items-center justify-center">
        <p className="text-sm text-slate-400">Waiting for first frame...</p>
      </div>
    )}

    {/* Progress bar */}
    <div
      className="w-full h-4 rounded-full bg-slate-100 overflow-hidden"
      aria-hidden="true"
    >
      <span
        className="block h-full rounded-full bg-blue-500 transition-all duration-500"
        style={{ width: `${status?.progress_percent ?? 0}%` }}
      />
    </div>
    <div className="grid gap-2">
      <strong className="text-lg text-slate-800">
        {status?.progress_percent ?? 0}%
      </strong>
      <p className="text-sm text-slate-500">
        {status?.message ??
          "Connecting to analysis feed..."}
      </p>
    </div>
    <button
      className="justify-self-start py-2 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-sm font-medium text-slate-600 transition-colors"
      onClick={() => setScreen("setup")}
      type="button"
    >
      Back to setup
    </button>
  </div>
) : null}
```

- [ ] **Step 4: Clear latestFrame in resetToAnalyze**

In the `resetToAnalyze` function, add `setLatestFrame(null)` alongside the other state resets.

- [ ] **Step 5: Add subscribeToFeed to imports**

Update the import at the top of App.tsx:

```typescript
import {
  createAnalysis,
  fetchReport,
  fetchSetup,
  fetchStatus,
  runAnalysis,
  saveSelection,
  subscribeToFeed,
} from "./api";
```

- [ ] **Step 6: Build frontend**

Run: `cd frontend && pnpm build`
Expected: Build succeeds with no type errors

- [ ] **Step 7: Run frontend tests**

Run: `cd frontend && pnpm test`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.tsx frontend/src/api.ts frontend/src/types.ts
git commit -m "feat: replace progress bar with live frame viewer on processing screen"
```

---

### Task 9: Fix up tests for background analysis model

**Files:**
- Modify: `backend/tests/test_analyses_api.py`

The shift from fake-step polling to background-thread execution means tests that relied on `_advance_analysis` ticking progress steps need updating. The `_poll_until_terminal` helper already polls until a terminal stage is reached, but now it may see `analyzing` with 0% until the thread completes.

- [ ] **Step 1: Update _poll_until_terminal to allow longer waits**

The existing `_poll_until_terminal` helper (find it in the test file) may have a max-iteration limit. Ensure it allows enough iterations for the background thread to finish. If it uses a loop count, increase it or add a small sleep:

```python
def _poll_until_terminal(client: TestClient, analysis_id: str) -> list[dict]:
    statuses = []
    for _ in range(50):  # Allow more iterations for background thread
        resp = client.get(f"/api/analyses/{analysis_id}/status")
        data = resp.json()
        statuses.append(data)
        if data["stage"] in ("completed", "failed"):
            return statuses
        import time
        time.sleep(0.1)  # Give background thread time to work
    return statuses
```

- [ ] **Step 2: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && pnpm test`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_analyses_api.py
git commit -m "test: update polling helper for background analysis model"
```

---

### Task 10: End-to-end smoke test

- [ ] **Step 1: Start mock stack**

Run: `make run-mock`

- [ ] **Step 2: Open browser to http://localhost:5173**

Paste any YouTube URL, select a player, run analysis. Verify:
- The processing screen shows "Waiting for first frame..." (mock pipeline doesn't emit frame callbacks)
- Progress bar advances from SSE events (analytics/coaching stages still push non-frame events)
- Analysis completes and report loads

- [ ] **Step 3: (If real pipelines available) Start real stack**

Run: `make run`

Paste a real YouTube URL, select a player, run analysis. Verify:
- Live annotated frames appear showing bounding boxes during tracking
- Pose skeleton dots appear during pose estimation
- Frame counter updates in real time
- Progress bar reflects actual progress
- Analysis completes and report loads

- [ ] **Step 4: Commit any fixes from smoke testing**
