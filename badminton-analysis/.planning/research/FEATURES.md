# Feature Landscape

**Domain:** AI-powered sports video analysis coaching tool
**Project:** Badminton Analysis
**Researched:** 2026-03-29
**Confidence:** MEDIUM-HIGH (architecture patterns drawn from training knowledge; library-specific behaviors verified against codebase)

---

## Existing Feature Baseline (What Already Works)

The codebase already has scaffolding for most pipeline stages. Research findings are scoped to
what needs to be *completed or added*, not rebuilt from scratch.

| Feature | State | Location |
|---------|-------|----------|
| Video upload (multipart POST) | Working | `routers/upload.py` |
| Video upload (TUS resumable) | Working | `routers/tus.py` |
| Video storage + serving | Working | `services/storage.py`, `routers/video.py` |
| YOLOv8n person detection | Working | `services/detection.py` |
| Click-to-select player UI | Working (fragile) | `pages/SelectPage.tsx` — hardcoded 640x480 |
| Analysis job lifecycle (create/poll/result) | Working scaffold | `routers/analyze.py` |
| Progress polling (2s interval) | Working | `pages/ResultsPage.tsx` |
| Distance/speed/coverage stats | Working | `services/analysis.py` |
| Movement chart (Recharts LineChart) | Working | `pages/ResultsPage.tsx` |
| Annotated video render (bounding box + trail) | Partially working | `services/analysis.py` |
| Pose estimation | **Stub — returns None** | `services/pose.py` |
| Skeleton overlay on video | **Broken (key name mismatch)** | `services/analysis.py::_draw_skeleton` |

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Working pose skeleton overlay on annotated video | Core visual deliverable; users expect to see their body tracked | Medium | Two bugs to fix: (1) pose.py stub, (2) `LANDMARK_N` key naming in `_draw_skeleton` |
| Browser-playable annotated video | Output is useless if it won't play | Medium | Current codec is `mp4v` (MPEG-4 Part 2) — browsers need H.264; must switch to `avc1` fourcc |
| Scored metrics per category | Users expect a grade, not just raw numbers | Medium | Need scoring functions for footwork, posture, court coverage — not yet in schemas |
| AI coaching notes text block | Core value prop: "what should I improve?" | Medium-High | Missing entirely from `AnalysisResult` schema and `ResultsPage` |
| Progress indicator during processing | Long jobs (several minutes) need user feedback | Low | Progress float exists in `AnalysisStatus` schema but ResultsPage only shows spinner, not % |
| Court coverage heatmap | More intuitive than a percentage number | Medium | Not in current UI; `movement_over_time` data is available to drive it |

---

## Differentiators

Features that set the product apart. Not expected but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-shot joint angle breakdown | Shows *how* a swing differs from ideal — not just that it happened | High | Requires pose per frame; computed from shoulder/elbow/wrist angle triangle |
| Side-by-side comparison vs. ideal form | Concrete visual reference point for improvement | High | Needs a reference dataset or hand-authored ideal angle ranges per shot type |
| Session-to-session progress tracking | Players improve over weeks; tracking that is motivating | High | Requires persistence (currently no DB) |
| Frame-scrubbing annotated video player with landmark popups | Tap a frame, see joint angles displayed | Medium | Needs a custom video player component, not just `<video controls>` |
| Footwork pattern classification | Label movements as "split step", "lunge", "recovery" | Very High | Sequence model territory; out of scope for v1 |
| Shot type classification (smash, drop, clear) | Understand what shots are being played | Very High | Out of scope for v1 per PROJECT.md |

---

## Anti-Features

Features to explicitly NOT build for v1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time analysis during play | MediaPipe Pose + YOLO inference on a ThreadPoolExecutor cannot meet real-time latency; would require GPU pipeline redesign | Process post-match videos only |
| Multi-player simultaneous analysis | IoU tracking breaks under occlusion; pose assignment across players is unsolved at this scale | Single player per run; user selects who to track |
| LLM API call per frame | Cost and latency are prohibitive; also poses privacy risk for club players | Generate coaching notes once per analysis from aggregated stats |
| WebSocket / SSE for live progress streaming | Adds complexity; 2s polling at this scale is adequate | Keep polling pattern; just show actual progress % instead of spinner |
| Public auth / user accounts | Out of scope per PROJECT.md | Skip; club tool with known users |
| Automated shot detection pipeline | Shot classification requires sequence labeling beyond wrist-speed threshold | Keep wrist-acceleration heuristic as proxy for v1 |

---

## Feature Deep-Dives: Five Focus Areas

### 1. AI Coaching Notes — How to Generate Them

**Recommendation: Rule-based scoring engine first; optional LLM pass second.**

**Confidence: HIGH** (rule-based approach) / **MEDIUM** (LLM integration pattern)

#### Why rule-based first

An LLM can generate fluent prose from structured data, but it needs structured data to be
meaningful. The source of truth is always the computed stats, not the model's priors about
badminton. Rule-based scoring is deterministic, testable, free, and offline-capable — all
critical for a club tool with no budget and no API keys.

#### Rule-based scoring engine (implement this)

Define thresholds derived from sport science literature or club coach input:

```
court_coverage_score:
  >= 60%  → 9-10   "Excellent range — you're covering the court well"
  40-59%  → 6-8    "Adequate coverage — look to extend your reach zones"
  < 40%   → 1-5    "Limited coverage — focus on base position recovery"

avg_speed_score:
  >= 2.5 m/s → 9-10  "High intensity movement throughout"
  1.5-2.5    → 6-8   "Moderate pace — typical for club play"
  < 1.5      → 1-5   "Low movement speed — work on explosive first step"

estimated_shot_count + avg_speed combined:
  High shots + low coverage → "Positional player — consider more aggressive court coverage"
  Low shots + high speed    → "High movement, low shot volume — check rally completion"
```

This produces:
- A numeric score per category (e.g. `footwork_score: 7`)
- A one-sentence observation per category
- A "primary recommendation" (the lowest-scoring category)

These map directly to the `AnalysisResult` schema extension needed.

#### Schema additions required

Current `AnalysisResult` only contains `stats` and `annotated_video_url`. Need:

```python
class ScoredMetric(BaseModel):
    category: str          # "court_coverage", "movement_speed", "shot_mechanics"
    score: int             # 1-10
    label: str             # "Good", "Fair", "Needs Work"
    observation: str       # one-sentence finding
    recommendation: str    # one-sentence action

class CoachingReport(BaseModel):
    scored_metrics: list[ScoredMetric]
    primary_recommendation: str   # worst-scoring category's recommendation
    summary: str                  # 2-3 sentence overall synthesis
```

#### Optional LLM pass (add later, not v1 blocker)

If an LLM API key is available, pass the structured `CoachingReport` dict as a prompt context
to generate a more natural paragraph-form coaching note. Use as a post-processing step, not
the primary source:

```python
# Pseudocode — not a v1 requirement
def enrich_with_llm(report: CoachingReport, model="gpt-4o-mini") -> str:
    prompt = f"""
    You are a badminton coach. A player has just completed a match analysis.
    Here are their stats: {report.model_dump_json()}
    Write 3-4 sentences of coaching feedback in plain English.
    Focus on their weakest area: {report.primary_recommendation}.
    """
    return llm_client.complete(prompt)
```

Keep LLM as optional enrichment. The rule-based `CoachingReport` must stand alone.

The env var pattern already established in this project (`STORAGE_DIR`) extends naturally:
`OPENAI_API_KEY` or `ANTHROPIC_API_KEY` checked at startup; if absent, LLM step is skipped.

---

### 2. Frontend Dashboard Patterns

**Confidence: HIGH** (Recharts and HTML5 video are already in the stack)

#### What exists

`ResultsPage.tsx` already has:
- `StatCard` component (4x metric cards in a grid)
- `VideoPlayer` component wrapping `<video controls>`
- `MovementChart` component using Recharts `LineChart`
- Basic 2-column layout (chart + video)

#### What's missing from the dashboard

**Court coverage heatmap** — a 20x20 grid visualisation of court zones visited.

The `compute_stats` function already produces visited cell coordinates via the grid logic.
Those cells just aren't surfaced in the API response. Pattern:

1. Add `court_heatmap: list[list[int]]` (20x20 grid of visit counts) to `AnalysisStats`
2. In `ResultsPage`, render it as a CSS grid or SVG — each cell colored by intensity
3. No additional library needed; a simple inline SVG or `<div>` grid with Tailwind background-
   color classes based on visit count works well and has zero added bundle size

**Progress bar during analysis** — `AnalysisStatus.progress` (0.0–1.0) is already returned by
the status endpoint. The UI currently ignores it and shows only a spinner. Change:

```tsx
// Current: only a spinner
<Loader2 className="animate-spin" />
<p>Analyzing video...</p>

// Target: spinner + progress bar
<div className="w-full bg-gray-200 rounded-full h-2">
  <div
    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
    style={{ width: `${(status.progress ?? 0) * 100}%` }}
  />
</div>
<p>{Math.round((status.progress ?? 0) * 100)}% complete</p>
```

**Scored metrics with visual grade indicators** — replace the plain `StatCard` for new metrics
with a card that shows score/10 + color-coded label:

```
[7/10] Court Coverage    [bar ████████░░]  "Good — extending range recommended"
[5/10] Movement Speed    [bar █████░░░░░]  "Fair — work on first-step explosiveness"
```

Use Tailwind `bg-green-500` / `bg-yellow-500` / `bg-red-500` for grade colors.

**AI coaching notes panel** — a dedicated card below the metrics grid with the coaching
summary text and per-category recommendations. Style like a coach's handwritten note:

```
┌─ Coaching Report ─────────────────────────────────────────────────────┐
│ Overall: 6.3/10                                                        │
│                                                                        │
│ Your court coverage is good but movement speed is the main area to    │
│ improve. Focus on your split step between shots.                       │
│                                                                        │
│ Key focus: Movement Speed (5/10)                                       │
│   Work on explosive first-step drills 3x per week.                   │
└───────────────────────────────────────────────────────────────────────┘
```

**Player selection UX fix** — `SelectPage.tsx` hardcodes `640` and `480` as divisors for
bounding box positioning percentages. When the displayed `<img>` is a different intrinsic size,
boxes are misaligned. Fix: use `onLoad` to read `naturalWidth`/`naturalHeight` from the image
element and use those values. No new library needed.

---

### 3. Async Video Processing Patterns in FastAPI

**Confidence: HIGH** (current pattern is already in the codebase; analysis here is about what
to keep, what to fix, and what to add)

#### Current pattern: ThreadPoolExecutor + poll

`analyze.py` submits `_run_analysis` to a `ThreadPoolExecutor(max_workers=2)`. Status is
stored in `_analysis_status` dict protected by a `threading.Lock`. Frontend polls every 2s.

This is **the right pattern for this project** — no Celery, no Redis, no distributed queue
needed for a single-machine club tool.

#### What to keep

- `ThreadPoolExecutor` with `max_workers=2` — correct for CPU-bound MediaPipe work; prevents
  overloading the machine with concurrent analyses
- Lock-guarded status dict — correct for thread safety
- 2-second polling interval — appropriate; not too chatty, not too slow for a 2-5 minute job
- `atexit.register(_executor.shutdown, wait=False)` — correct cleanup pattern

#### What to fix

**Progress is reported but not surfaced in UI.** The `AnalysisStatus` schema already has
`progress: float | None`. `_update_progress()` is called at seven points in `_run_analysis`.
The only missing piece is using it in the frontend polling loop (see Section 2 above).

**VideoCapture is opened once per frame.** `detect_persons(video_path, frame_idx)` inside the
analysis loop opens `cv2.VideoCapture(video_path)`, seeks to `frame_idx`, reads one frame, and
releases — ~150 times for a 300-frame run. Fix: open the capture once before the loop, seek
with `cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)`, and close after the loop. This is a
performance fix but also affects correctness (repeated filesystem open calls can fail under
load).

**In-memory job state is lost on restart.** For v1, this is an accepted tradeoff per the
codebase docs. The fix for future phases is to persist job state to a SQLite file or a simple
JSON file in `storage/`. Do not introduce Celery or Redis for v1.

#### SSE vs polling (for future reference)

If the polling pattern becomes unsatisfactory (e.g. finer-grained progress or live frame
preview), FastAPI supports Server-Sent Events via `StreamingResponse` with `text/event-stream`
content type. Pattern:

```python
from fastapi.responses import StreamingResponse
import asyncio

async def progress_stream(analysis_id: str):
    while True:
        with _status_lock:
            job = _analysis_status.get(analysis_id)
        if not job or job.status in ("completed", "failed"):
            yield f"data: {job.model_dump_json()}\n\n"
            break
        yield f"data: {job.model_dump_json()}\n\n"
        await asyncio.sleep(1)

@router.get("/analyze/{analysis_id}/stream")
async def stream_progress(analysis_id: str):
    return StreamingResponse(progress_stream(analysis_id), media_type="text/event-stream")
```

This is **not needed for v1** but is low complexity if polling becomes annoying in practice.

---

### 4. Annotated Video Rendering and Browser-Compatible Output

**Confidence: HIGH** (OpenCV codec behavior is well-established)

#### The codec problem

`render_annotated_video` uses `cv2.VideoWriter_fourcc(*"mp4v")`. This produces MPEG-4 Part 2
video inside an `.mp4` container. **Chrome and Safari will not play this in an HTML5 `<video>`
tag without transcoding.** The browser requires H.264 (MPEG-4 Part 10 / AVC).

**Fix: change the fourcc to `"avc1"` (or `"h264"`).**

```python
# Current — produces MPEG-4 Part 2 (not browser-playable)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")

# Fixed — produces H.264/AVC (browser-playable in all major browsers)
fourcc = cv2.VideoWriter_fourcc(*"avc1")
```

**Caveats:**
- `avc1` requires OpenCV to be built with FFmpeg support. The project uses
  `opencv-python-headless` (PyPI), which ships with FFmpeg — so this should work on Linux.
- If `avc1` fails to open the writer (returns `False`), fall back to `mp4v` and flag in logs.
  Add a writer-open check: `if not writer.isOpened(): raise RuntimeError("VideoWriter failed")`
- Alternatively, add a post-processing FFmpeg subprocess call:
  ```python
  import subprocess
  subprocess.run([
      "ffmpeg", "-y", "-i", str(tmp_path),
      "-vcodec", "libx264", "-crf", "23",
      str(output_path)
  ], check=True)
  ```
  This is more reliable but adds `ffmpeg` as a system dependency.

#### The skeleton key-name bug

`_draw_skeleton` builds `lm_map` keyed by `lm["name"]` (e.g. `"RIGHT_WRIST"`) but then
looks up `f"LANDMARK_{idx}"` (e.g. `"LANDMARK_15"`). The lookup always misses.

MediaPipe Pose landmark names follow the `mp.solutions.pose.PoseLandmark` enum. The connection
list uses integer indices. The fix has two valid approaches:

**Option A — index-keyed map (simplest):**
```python
# In pose.py: store index alongside name when building landmarks list
# landmark dict: {"name": "RIGHT_WRIST", "index": 15, "x": ..., "y": ..., "visibility": ...}

# In _draw_skeleton: key by index
lm_map = {lm["index"]: (int(lm["x"]), int(lm["y"])) for lm in landmarks}
for start_idx, end_idx in connections:
    if start_idx in lm_map and end_idx in lm_map:
        cv2.line(frame, lm_map[start_idx], lm_map[end_idx], (0, 255, 255), 2)
```

**Option B — name-keyed map with name-to-index mapping:**
Define `POSE_CONNECTIONS` as a list of `(name_a, name_b)` tuples and look up by name.
More readable but more verbose.

Option A is simpler and requires fewer changes.

#### MediaPipe Pose wiring (the stub fix)

`pose.py` returns `None` unconditionally. The MediaPipe Pose API:

```python
import mediapipe as mp
import cv2
import numpy as np

_mp_pose = mp.solutions.pose
_pose = _mp_pose.Pose(
    static_image_mode=False,   # video mode — uses temporal filtering
    model_complexity=1,        # 0=lite, 1=full, 2=heavy; 1 is the right balance
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

def estimate_pose(frame: np.ndarray, bbox: tuple[float, float, float, float]) -> list[dict] | None:
    x, y, w, h = (int(v) for v in bbox)
    # Crop to person region with padding
    pad = 20
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(frame.shape[1], x + w + pad)
    y2 = min(frame.shape[0], y + h + pad)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    result = _pose.process(rgb)

    if not result.pose_landmarks:
        return None

    h_crop, w_crop = crop.shape[:2]
    landmarks = []
    for idx, lm in enumerate(result.pose_landmarks.landmark):
        landmarks.append({
            "index": idx,
            "name": _mp_pose.PoseLandmark(idx).name,  # e.g. "RIGHT_WRIST"
            "x": lm.x * w_crop + x1,   # back to full-frame pixel coords
            "y": lm.y * h_crop + y1,
            "visibility": lm.visibility,
        })
    return landmarks
```

Key decisions:
- `static_image_mode=False` — use video mode for temporal consistency across frames
- Crop + re-project — run pose on person crop for better accuracy, then convert
  coordinates back to full-frame pixel space for rendering
- Include `"index"` in the landmark dict — fixes the skeleton key-name bug (Option A above)
- Use a module-level `_pose` instance — MediaPipe Pose is not thread-safe; if two analysis
  jobs run concurrently, each needs its own instance. Move instantiation inside
  `_run_analysis` or use a `threading.local()` pattern.

**Thread safety note for MediaPipe:** The `ThreadPoolExecutor(max_workers=2)` means two
analysis jobs can run simultaneously. MediaPipe's `Pose` object is not documented as
thread-safe. Safe approach: instantiate inside the analysis function, not at module level.

---

### 5. Comparison / Benchmarking Patterns

**Confidence: MEDIUM** (design pattern; no comparable existing code in the project)

This feature does not exist yet anywhere in the codebase.

#### Option A — vs. Ideal Form (Threshold Ranges)

The simplest comparison that adds genuine coaching value without requiring prior sessions.

Author a set of "ideal form" angle ranges per movement type. For badminton these are grounded
in coaching literature:

```python
IDEAL_RANGES = {
    "overhead_swing_elbow_angle": (80, 120),   # degrees at contact
    "lunge_knee_angle": (90, 130),             # degrees at lunge depth
    "base_position_hip_width": (1.2, 1.8),    # ratio to shoulder width
}
```

For each metric, compute whether the player's measured value falls within the ideal range,
below it, or above it. Express as:

```
Elbow angle at swing: 143° (ideal: 80–120°)   [Too open — tighten racket arc]
Lunge knee angle:      95° (ideal: 90–130°)   [Within ideal range — good form]
```

This is deterministic, requires no prior sessions, and can be authored by a coach in a
config file. It is the right v1 comparison feature.

#### Option B — vs. Previous Sessions (Trend Comparison)

Shows improvement over time: "Your court coverage improved from 34% to 51% over 3 sessions."

Requires:
- Persisted analysis results (currently lost on restart — blocked by in-memory job store)
- A player identity model (currently no auth — blocked by no auth)

This is a post-v1 feature. It needs a SQLite or file-based persistence layer first.

#### Option C — Side-by-Side Video Comparison

Two annotated videos in a synchronized `<video>` player: "this session" vs. "ideal form clip"
or "previous session".

Requires:
- An ideal-form reference video (manually sourced)
- Synchronized playback across two `<video>` elements via JS event listeners
- For session-vs-session: persisted analysis history

Out of scope for v1. Pattern for later: use a shared `currentTime` state updated by
`timeupdate` events on the primary video, and mirror to the secondary via `videoRef.current.
currentTime = primaryTime`.

#### Recommended v1 comparison approach

Implement Option A. Author threshold ranges as a Python dict in a new
`backend/services/scoring.py` module. The output feeds directly into the `ScoredMetric`
model defined in Section 1. The UI displays a delta badge: "Within range" / "Too high" /
"Too low" alongside the numeric score.

---

## Feature Dependencies

```
Working pose.py → Skeleton overlay on video
Working pose.py → Shot detection (wrist acceleration)
Working pose.py → Joint angle computation
Working pose.py → Scoring functions → AI coaching notes

Browser-compatible video (H.264) → Annotated video is actually viewable

Scoring functions → Scored metric cards in dashboard
Scoring functions → AI coaching notes text

Court grid data in API response → Heatmap overlay in dashboard
AnalysisStatus.progress in UI → Real progress bar (data already exists in API)

Persisted analysis results → Session-to-session comparison (v2)
Auth / player identity → Session history (v2)
```

---

## MVP Recommendation

Build in this order — each step unlocks the next:

1. **Fix pose estimation** — wire MediaPipe in `pose.py`; include `index` in landmark dict;
   thread-safe instantiation. This unblocks skeleton rendering, shot detection, and all
   downstream coaching features.

2. **Fix skeleton overlay** — change `_draw_skeleton` to key by `lm["index"]`. One-line fix
   once pose.py returns real data.

3. **Fix H.264 output codec** — change `fourcc` from `mp4v` to `avc1`; add writer-open
   check; add FFmpeg fallback. Without this, the annotated video won't play in browsers.

4. **Fix player selection coordinate math** — use `naturalWidth`/`naturalHeight` from the
   `<img>` element instead of hardcoded 640/480.

5. **Add scoring service** — `backend/services/scoring.py` with threshold-based scoring
   functions. Extend `AnalysisResult` schema with `CoachingReport`.

6. **Extend dashboard** — add coaching notes panel, scored metric cards with grade colors,
   real progress bar (using existing `progress` field), and heatmap grid.

7. **Add VideoCapture fix** — open capture once per analysis run, not per frame. Performance
   and reliability improvement.

**Defer:**
- LLM integration: nice-to-have; adds API cost and external dependency; rule-based engine
  provides full coaching value for v1
- Session-to-session comparison: blocked by persistence layer redesign
- Shot type classification: too complex for v1 per PROJECT.md

---

## Sources

- Codebase direct inspection (2026-03-29): `backend/services/pose.py`, `analysis.py`,
  `routers/analyze.py`, `models/schemas.py`, `frontend/src/pages/ResultsPage.tsx`,
  `frontend/src/pages/SelectPage.tsx`
- `.planning/codebase/CONCERNS.md` — bug catalogue used to scope feature fixes
- `.planning/codebase/ARCHITECTURE.md` — analysis pipeline data flow
- `.planning/codebase/STACK.md` — confirmed MediaPipe 0.10.33, OpenCV 4.13, Recharts 2.5
- MediaPipe Pose API behavior: HIGH confidence from training data (API stable since 0.8.x)
- OpenCV VideoWriter codec compatibility: HIGH confidence (well-documented browser constraint)
- FastAPI ThreadPoolExecutor pattern: HIGH confidence (pattern already in codebase and working)
- LLM integration pattern: MEDIUM confidence (general pattern; no specific version verified)
- Comparison/benchmarking design: MEDIUM confidence (design recommendation; no external source)
