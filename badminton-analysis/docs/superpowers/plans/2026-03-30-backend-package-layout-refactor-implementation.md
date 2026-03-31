# Backend Package Layout Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `backend/src/badminton_analysis_api` into focused subpackages with clearer ownership while preserving runtime behavior and test outcomes.

**Architecture:** Split the flat backend package into `api`, `analyses`, `coaching`, `pipelines`, and `schemas`. Move code in dependency order: schemas first, then provider/pipeline boundaries, then analysis orchestration, then app bootstrap and test imports. Keep behavior stable and validate after each move.

**Tech Stack:** FastAPI, Pydantic v2, pytest, Ruff

---

### Task 1: Split Schemas Into Focused Modules

**Files:**
- Create: `backend/src/badminton_analysis_api/schemas/__init__.py`
- Create: `backend/src/badminton_analysis_api/schemas/shared.py`
- Create: `backend/src/badminton_analysis_api/schemas/analysis.py`
- Create: `backend/src/badminton_analysis_api/schemas/coaching.py`
- Create: `backend/src/badminton_analysis_api/schemas/cv.py`
- Create: `backend/src/badminton_analysis_api/schemas/report.py`
- Modify: `backend/tests/test_analyses_api.py`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write a failing import-smoke test against the new schema package**

```python
def test_schema_package_exports_analysis_and_report_types() -> None:
    from badminton_analysis_api.schemas import AnalysisReport, AnalysisStage, MatchType

    assert AnalysisReport.__name__ == "AnalysisReport"
    assert AnalysisStage.COMPLETED == "completed"
    assert MatchType.MENS_SINGLES == "mens_singles"
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `cd backend && ../backend/.venv/bin/python -m pytest tests/test_analyses_api.py -k schema_package_exports -v`
Expected: `FAIL` because `badminton_analysis_api.schemas` does not exist yet.

- [ ] **Step 3: Create the schema modules and re-export surface**

```python
# backend/src/badminton_analysis_api/schemas/shared.py
from badminton_analysis_api.schemas.shared import (
    CourtPoint,
    DetectionBox,
    MatchType,
)
```

```python
# backend/src/badminton_analysis_api/schemas/__init__.py
from .analysis import (
    AnalysisActionResponse,
    AnalysisCreateInput,
    AnalysisCreateResponse,
    AnalysisListItem,
    AnalysisListResponse,
    AnalysisRecord,
    AnalysisSelectionInput,
    AnalysisSetupResponse,
    AnalysisStage,
    AnalysisStatusResponse,
)
from .coaching import AIRationale, CoachFeedbackResult, CoachView
from .cv import (
    PlayerTrackSummary,
    PoseSummary,
    SetupDetectionResult,
    TrackSample,
    TrackingResult,
)
from .report import (
    AnalysisEvidence,
    AnalysisReport,
    AnalyticsView,
    ConfidenceAnnotation,
    HeatmapCell,
    MechanicsMetrics,
    MovementMetrics,
    PositioningMetrics,
    PressureWindow,
    ShotSelectionEvent,
    ShotSelectionMetrics,
    ShuttleMetrics,
    ShuttleSample,
)
from .shared import CourtModel, CourtPoint, DetectionBox, MatchType, PlayerCandidate
```

- [ ] **Step 4: Update test imports to use the new package**

```python
from badminton_analysis_api.schemas import (
    CoachView,
    CourtModel,
    CourtPoint,
    MatchType,
    PlayerCandidate,
)
```

- [ ] **Step 5: Run the targeted test and then the backend suite**

Run: `cd backend && ../backend/.venv/bin/python -m pytest tests/test_analyses_api.py -k schema_package_exports -v`
Expected: `PASS`

Run: `cd backend && ../backend/.venv/bin/python -m pytest`
Expected: `PASS`

### Task 2: Move Coaching And Pipeline Boundaries Into Packages

**Files:**
- Create: `backend/src/badminton_analysis_api/coaching/__init__.py`
- Create: `backend/src/badminton_analysis_api/coaching/engine.py`
- Create: `backend/src/badminton_analysis_api/pipelines/__init__.py`
- Create: `backend/src/badminton_analysis_api/pipelines/cv/__init__.py`
- Create: `backend/src/badminton_analysis_api/pipelines/cv/pipeline.py`
- Create: `backend/src/badminton_analysis_api/pipelines/media/__init__.py`
- Create: `backend/src/badminton_analysis_api/pipelines/media/pipeline.py`
- Modify: `backend/tests/test_analyses_api.py`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write a failing import-smoke test for the new package paths**

```python
def test_new_package_paths_expose_engines_and_pipelines() -> None:
    from badminton_analysis_api.coaching.engine import LLMCoachFeedbackEngine
    from badminton_analysis_api.pipelines.cv.pipeline import CVPipeline
    from badminton_analysis_api.pipelines.media.pipeline import MediaArtifactPipeline

    assert LLMCoachFeedbackEngine.__name__ == "LLMCoachFeedbackEngine"
    assert CVPipeline.__name__ == "CVPipeline"
    assert MediaArtifactPipeline.__name__ == "MediaArtifactPipeline"
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `cd backend && ../backend/.venv/bin/python -m pytest tests/test_analyses_api.py -k package_paths_expose -v`
Expected: `FAIL` because the package paths do not exist yet.

- [ ] **Step 3: Move the existing modules into their new package files and update imports**

```python
from badminton_analysis_api.coaching.engine import (
    CoachFeedbackEngine,
    PlaceholderCoachFeedbackEngine,
)
from badminton_analysis_api.pipelines.cv.pipeline import (
    CVPipeline,
    _default_court,
    _default_players,
    _player_count,
)
from badminton_analysis_api.pipelines.media.pipeline import (
    MediaArtifactPipeline,
    MediaPreparationError,
)
```

- [ ] **Step 4: Update tests to import the moved engine path**

```python
from badminton_analysis_api.coaching.engine import (
    LLMCoachFeedbackEngine,
    build_coach_feedback_engine_from_env,
)
```

- [ ] **Step 5: Run the targeted test and then the backend suite**

Run: `cd backend && ../backend/.venv/bin/python -m pytest tests/test_analyses_api.py -k package_paths_expose -v`
Expected: `PASS`

Run: `cd backend && ../backend/.venv/bin/python -m pytest`
Expected: `PASS`

### Task 3: Move Analysis Orchestration Into `analyses/`

**Files:**
- Create: `backend/src/badminton_analysis_api/analyses/__init__.py`
- Create: `backend/src/badminton_analysis_api/analyses/progress.py`
- Create: `backend/src/badminton_analysis_api/analyses/store.py`
- Create: `backend/src/badminton_analysis_api/analyses/service.py`
- Modify: `backend/tests/test_analyses_api.py`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write a failing import-smoke test for the new analysis package**

```python
def test_analysis_package_exports_service_and_store() -> None:
    from badminton_analysis_api.analyses.service import AnalysisService
    from badminton_analysis_api.analyses.store import AnalysisStore
    from badminton_analysis_api.analyses.progress import ANALYZING_PROGRESS_STEPS

    assert AnalysisService.__name__ == "AnalysisService"
    assert AnalysisStore.__name__ == "AnalysisStore"
    assert len(ANALYZING_PROGRESS_STEPS) > 0
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `cd backend && ../backend/.venv/bin/python -m pytest tests/test_analyses_api.py -k analysis_package_exports -v`
Expected: `FAIL` because `analyses/` does not exist yet.

- [ ] **Step 3: Move store and service into the new package and extract progress constants**

```python
# backend/src/badminton_analysis_api/analyses/progress.py
ANALYZING_PROGRESS_STEPS = [
    (12, "Ingesting the YouTube match and normalizing the video."),
    (24, "Extracting the setup frame from the opening rally window."),
    (36, "Detecting court geometry and applying any saved manual overrides."),
    (48, "Detecting players and building multi-person tracks."),
    (58, "Assigning the selected player to the tracked movement sequence."),
    (69, "Extracting pose landmarks and movement signals."),
    (80, "Inferring shot events from the tracked rally sequence."),
    (91, "Scoring tactical shot quality and decision outcomes."),
    (98, "Assembling the coach report and analytics evidence."),
]
```

```python
from badminton_analysis_api.analyses.progress import ANALYZING_PROGRESS_STEPS
from badminton_analysis_api.analyses.store import AnalysisStore
```

- [ ] **Step 4: Update tests and runtime imports**

```python
from badminton_analysis_api.analyses.service import AnalysisService
from badminton_analysis_api.analyses.store import AnalysisStore
```

- [ ] **Step 5: Run the targeted test and then the backend suite**

Run: `cd backend && ../backend/.venv/bin/python -m pytest tests/test_analyses_api.py -k analysis_package_exports -v`
Expected: `PASS`

Run: `cd backend && ../backend/.venv/bin/python -m pytest`
Expected: `PASS`

### Task 4: Move FastAPI Bootstrap Into `api/` And Remove Flat Modules

**Files:**
- Create: `backend/src/badminton_analysis_api/api/__init__.py`
- Create: `backend/src/badminton_analysis_api/api/app.py`
- Modify: `backend/tests/test_analyses_api.py`
- Delete: `backend/src/badminton_analysis_api/main.py`
- Delete: `backend/src/badminton_analysis_api/service.py`
- Delete: `backend/src/badminton_analysis_api/store.py`
- Delete: `backend/src/badminton_analysis_api/coach_feedback.py`
- Delete: `backend/src/badminton_analysis_api/cv.py`
- Delete: `backend/src/badminton_analysis_api/media.py`
- Delete: `backend/src/badminton_analysis_api/models.py`
- Test: `backend/tests/test_analyses_api.py`

- [ ] **Step 1: Write a failing test for the new app path**

```python
def test_api_app_module_exposes_fastapi_app() -> None:
    import badminton_analysis_api.api.app as app_module

    assert app_module.app.title == "Badminton Analysis API"
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `cd backend && ../backend/.venv/bin/python -m pytest tests/test_analyses_api.py -k api_app_module_exposes -v`
Expected: `FAIL` because `api/app.py` does not exist yet.

- [ ] **Step 3: Move the FastAPI bootstrap and update test bootstrap imports**

```python
import badminton_analysis_api.api.app as main_module
```

- [ ] **Step 4: Delete the obsolete flat modules once all imports are updated**

```bash
rm backend/src/badminton_analysis_api/main.py
rm backend/src/badminton_analysis_api/service.py
rm backend/src/badminton_analysis_api/store.py
rm backend/src/badminton_analysis_api/coach_feedback.py
rm backend/src/badminton_analysis_api/cv.py
rm backend/src/badminton_analysis_api/media.py
rm backend/src/badminton_analysis_api/models.py
```

- [ ] **Step 5: Run backend verification**

Run: `cd backend && ../backend/.venv/bin/python -m pytest`
Expected: `PASS`

Run: `cd backend && ../backend/.venv/bin/python -m ruff check src tests`
Expected: `PASS`

### Task 5: Final Cross-Check

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Run frontend verification after backend import churn**

Run: `cd frontend && pnpm test`
Expected: `PASS`

Run: `cd frontend && pnpm build`
Expected: `PASS`

- [ ] **Step 2: Review the diff for ownership clarity**

```bash
git diff --stat backend/src/badminton_analysis_api backend/tests
find backend/src/badminton_analysis_api -maxdepth 3 -type f | sort
```

Expected: flat root modules are replaced by `api`, `analyses`, `coaching`, `pipelines`, and `schemas`.
