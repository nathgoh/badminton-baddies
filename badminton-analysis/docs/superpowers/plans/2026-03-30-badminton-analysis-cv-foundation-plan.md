# Badminton Analysis CV Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace mocked setup/player inputs with a CV pipeline foundation that supports real setup detection, sampled player tracking, and selected-player pose extraction while keeping report scoring heuristic.

**Architecture:** Add a `CVPipeline` boundary with `detect_setup`, `track_players`, and `extract_pose`. Persist setup detections, tracking summaries, and pose summaries on `AnalysisRecord`, then feed those derived signals into the existing report assembly path. Keep a `mock` CV mode for tests/dev and a `hybrid` mode that uses OpenCV for court geometry, YOLO for person detect/track, and MediaPipe for selected-player pose.

**Tech Stack:** FastAPI, Pydantic, OpenCV, Ultralytics YOLO, MediaPipe Pose, pytest

---

### Task 1: Add CV domain models and pipeline boundary

**Files:**
- Create: `badminton-analysis/backend/src/badminton_analysis_api/cv.py`
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/models.py`
- Test: `badminton-analysis/backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_create_analysis_uses_cv_setup_detection_outputs(client: TestClient) -> None:
    response = client.post(
        "/api/analyses",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=badminton-demo",
            "match_type": "mens_singles",
        },
    )

    analysis_id = response.json()["analysis_id"]
    setup = client.get(f"/api/analyses/{analysis_id}/setup").json()

    assert setup["players"][0]["label"] == "Detected Player A"
    assert setup["court"]["confidence"] == 0.91
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_create_analysis_uses_cv_setup_detection_outputs -q`
Expected: FAIL because setup still returns mocked players/court.

- [ ] **Step 3: Write minimal implementation**

```python
class CVPipeline(Protocol):
    def detect_setup(self, frame_path: str, match_type: MatchType) -> SetupDetectionResult: ...
    def track_players(self, video_path: str, court: CourtModel, match_type: MatchType) -> TrackingResult: ...
    def extract_pose(self, video_path: str, selected_track_id: str) -> PoseExtractionResult: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_create_analysis_uses_cv_setup_detection_outputs -q`
Expected: PASS

### Task 2: Wire setup detection into analysis creation

**Files:**
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/service.py`
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/main.py`
- Test: `badminton-analysis/backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_low_confidence_setup_detection_adds_warning(client: TestClient) -> None:
    analysis_id = _create_analysis(client, match_type="mixed_doubles")
    status = client.get(f"/api/analyses/{analysis_id}/status").json()
    assert "court detection confidence is low" in " ".join(status["warnings"]).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_low_confidence_setup_detection_adds_warning -q`
Expected: FAIL because setup warnings are not persisted.

- [ ] **Step 3: Write minimal implementation**

```python
record.players = setup_detection.players
record.court = setup_detection.court
record.warnings = [*record.warnings, *setup_detection.warnings]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_low_confidence_setup_detection_adds_warning -q`
Expected: PASS

### Task 3: Add sampled tracking and selected-player mapping

**Files:**
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/cv.py`
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/service.py`
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/models.py`
- Test: `badminton-analysis/backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_analysis_uses_cv_tracking_to_build_selected_player_summary(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")
    client.post(f"/api/analyses/{analysis_id}/run")
    _poll_until_terminal(client, analysis_id)
    report = client.get(f"/api/analyses/{analysis_id}/report").json()
    assert report["analytics_view"]["movement"]["total_distance_meters"] == 41.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_run_analysis_uses_cv_tracking_to_build_selected_player_summary -q`
Expected: FAIL because analytics still come from fixed mock values.

- [ ] **Step 3: Write minimal implementation**

```python
tracking = self._cv_pipeline.track_players(...)
selected_track = tracking.match_selected_player(record.selected_player_id)
record.selected_track_id = selected_track.track_id
record.tracking_summary = tracking.summary
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_run_analysis_uses_cv_tracking_to_build_selected_player_summary -q`
Expected: PASS

### Task 4: Add selected-player pose extraction and real intermediate analytics inputs

**Files:**
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/cv.py`
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/service.py`
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/coach_feedback.py`
- Test: `badminton-analysis/backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_pose_extraction_reduces_confidence_when_samples_are_sparse(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="womens_singles")
    client.post(f"/api/analyses/{analysis_id}/run")
    statuses = _poll_until_terminal(client, analysis_id)
    assert any("pose coverage is sparse" in warning.lower() for warning in statuses[-1]["warnings"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_pose_extraction_reduces_confidence_when_samples_are_sparse -q`
Expected: FAIL because pose warnings are not generated.

- [ ] **Step 3: Write minimal implementation**

```python
pose = self._cv_pipeline.extract_pose(...)
record.warnings = [*record.warnings, *pose.warnings]
analytics = self._build_analytics(record.match_type, tracking=tracking, pose=pose)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_pose_extraction_reduces_confidence_when_samples_are_sparse -q`
Expected: PASS

### Task 5: Add hybrid runtime and documentation

**Files:**
- Modify: `badminton-analysis/backend/pyproject.toml`
- Modify: `badminton-analysis/README.md`
- Modify: `badminton-analysis/backend/README.md`
- Modify: `badminton-analysis/backend/src/badminton_analysis_api/main.py`
- Test: `badminton-analysis/backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_hybrid_cv_mode_without_runtime_dependencies_falls_back_cleanly(monkeypatch):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_hybrid_cv_mode_without_runtime_dependencies_falls_back_cleanly -q`
Expected: FAIL because no CV pipeline builder exists.

- [ ] **Step 3: Write minimal implementation**

```python
def build_cv_pipeline_from_env(...):
    if mode == "hybrid":
        return HybridCVPipeline(...)
    return MockCVPipeline(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest tests/test_analyses_api.py::test_hybrid_cv_mode_without_runtime_dependencies_falls_back_cleanly -q`
Expected: PASS

### Task 6: Full verification

**Files:**
- Modify: `badminton-analysis/backend/tests/test_analyses_api.py`

- [ ] **Step 1: Run backend tests**

Run: `cd badminton-analysis/backend && PYTHONPATH=src ../backend/.venv/bin/pytest`
Expected: PASS

- [ ] **Step 2: Run lint**

Run: `cd badminton-analysis/backend && ../backend/.venv/bin/ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 3: Run type check**

Run: `cd badminton-analysis/backend && ../backend/.venv/bin/ty check src`
Expected: `All checks passed!`

- [ ] **Step 4: Run frontend verification**

Run: `cd badminton-analysis/frontend && pnpm test && pnpm build`
Expected: tests pass and Vite build succeeds
