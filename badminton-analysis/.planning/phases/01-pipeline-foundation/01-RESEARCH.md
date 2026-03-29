# Phase 1: Pipeline Foundation - Research

**Researched:** 2026-03-29
**Domain:** MediaPipe Pose Tasks API, OpenCV video I/O, FastAPI upload security
**Confidence:** HIGH

---

## Summary

Phase 1 fixes five pre-existing bugs and adds one new security requirement. Every bug has been
confirmed by direct source-code inspection. No speculative issues — each fix target is
precisely located.

The three pipeline-blocking bugs are: (1) `services/pose.py` returns `None` unconditionally
(stub), (2) `_draw_skeleton` in `services/analysis.py` builds a name-keyed landmark map but
then looks up `"LANDMARK_N"` strings that MediaPipe never produces — zero skeleton lines are
ever drawn, and (3) `render_annotated_video` uses `cv2.VideoWriter_fourcc(*"mp4v")` which
produces MPEG-4 Part 2 — not playable in browsers. The analysis loop also opens and closes
`cv2.VideoCapture` roughly 150 times per video via `detect_persons`. Upload endpoints have
no filename sanitization or file type validation.

The critical path is: fix pose stub → fix skeleton rendering → confirm video codec → fix
VideoCapture lifecycle → harden uploads. Each fix is isolated to a single file/function.

**Primary recommendation:** Use the MediaPipe Tasks API (`PoseLandmarkerOptions` +
`VisionTaskRunningMode.VIDEO`) for pose estimation. It is the only available API in
mediapipe 0.10.33 — `mediapipe.solutions` is absent. The `avc1` fourcc returns `False` on
`writer.isOpened()` in this environment; use `mp4v` to write a temp file and transcode with
FFmpeg. FFmpeg is NOT installed on the target system — install it or use a pip alternative.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | Pose estimation implemented — MediaPipe Pose extracts joint landmarks per frame in VIDEO mode | Tasks API confirmed importable; no `.task` model file present — must be downloaded; `VisionTaskRunningMode.VIDEO` verified |
| PIPE-02 | Skeleton overlay renders correctly — landmark connections drawn using integer index keys | Bug confirmed at `analysis.py:179–186`; fix is keying `lm_map` by `enumerate` index, not `lm["name"]` |
| PIPE-03 | Annotated video browser-playable — output encoded as H.264 (not MPEG-4 Part 2) | `avc1` fourcc returns `False` on `isOpened()` in this env; FFmpeg not installed; must install ffmpeg and use subprocess transcode |
| PIPE-04 | Single VideoCapture instance across all frames (not per-frame open/close) | Bug confirmed in `analyze.py:_run_analysis` — `detect_persons(video_path, frame_idx)` called per frame, each opens/closes its own `VideoCapture` |
| PIPE-05 | Upload filenames sanitized against path traversal on both REST and TUS endpoints | REST: `upload.py:16` joins `file.filename` directly; TUS: `tus.py:58–59` decodes base64 filename without sanitizing |
| PIPE-06 | File type validation enforced on upload (video files only) | Neither endpoint validates MIME type or extension; no `python-magic` or `filetype` installed — use header `Content-Type` check + extension allowlist (stdlib only) |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mediapipe | 0.10.33 (installed) | Pose landmark extraction | Only pose API available in repo; Tasks API is the current API — `solutions` module absent |
| opencv-python-headless | 4.13.0 (installed) | Video read/write, frame annotation | Already in use throughout codebase |
| numpy | >=1.26.0 (installed) | Array operations for landmark coordinates | MediaPipe output is ndarray-compatible |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ffmpeg (system binary) | any | H.264 transcode of annotated video | Required because `avc1` VideoWriter does not open in this OpenCV build |
| mimetypes (stdlib) | stdlib | Basic MIME type lookup by extension | PIPE-06 validation — no third-party library needed |
| pathlib (stdlib) | stdlib | Safe filename construction | Already used in `storage.py`; use `Path(filename).name` to strip traversal |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ffmpeg subprocess transcode | `imageio-ffmpeg` pip package | imageio-ffmpeg bundles its own ffmpeg binary — eliminates system dependency but adds ~50MB to install |
| Extension allowlist + Content-Type header | `python-magic` (libmagic) | python-magic reads magic bytes — more robust but requires `libmagic` system lib; overkill for v1 |
| `VisionTaskRunningMode.VIDEO` | `VisionTaskRunningMode.IMAGE` | IMAGE mode has no temporal smoothing; jitter is worse; VIDEO mode requires monotonically increasing timestamps |

**Installation (if imageio-ffmpeg preferred over system ffmpeg):**
```bash
cd backend && uv add imageio-ffmpeg
```

**Version verification:** All versions confirmed against installed packages in
`backend/.venv/lib/python3.12/site-packages/` and `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

No restructuring needed for Phase 1. All changes are isolated to existing files:

```
backend/
├── services/
│   └── pose.py            # PIPE-01: implement estimate_pose()
├── services/
│   └── analysis.py        # PIPE-02: fix _draw_skeleton(); PIPE-03: fix codec
├── routers/
│   ├── analyze.py         # PIPE-04: open VideoCapture once, pass cap to detect_persons
│   ├── upload.py          # PIPE-05, PIPE-06: sanitize filename, validate file type
│   └── tus.py             # PIPE-05: sanitize decoded filename before storage.create_upload
└── models/
    └── schemas.py         # No changes needed for Phase 1
```

### Pattern 1: MediaPipe Tasks API — VIDEO Mode

**What:** PoseLandmarker with `VisionTaskRunningMode.VIDEO` processes frames sequentially
with temporal smoothing. Timestamps must be monotonically increasing.

**When to use:** Any batch video file processing. Not for real-time (use LIVE_STREAM).

**Thread safety:** `PoseLandmarker` instance must NOT be shared between concurrent analysis
jobs. The executor runs `max_workers=2`. Instantiate inside `_run_analysis`, not at module
level.

**Model file requirement (PIPE-01 blocker):** The Tasks API requires a `.task` bundle file
on disk. No model file exists in the repo. Must be downloaded before the implementation
can be tested:

```bash
curl -O https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
```

Place at `backend/pose_landmarker_full.task` or make the path configurable via an env var
`POSE_MODEL_PATH`.

**Example — Tasks API video mode (verified importable in this venv):**
```python
# Source: verified imports from backend/.venv mediapipe 0.10.33
import mediapipe as mp
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="pose_landmarker_full.task"),
    running_mode=VisionTaskRunningMode.VIDEO,
    num_poses=1,
    min_pose_detection_confidence=0.5,
    min_pose_presence_confidence=0.5,
    min_tracking_confidence=0.5,
    output_segmentation_masks=False,
)

with PoseLandmarker.create_from_options(options) as landmarker:
    # frame must be RGB — convert from OpenCV BGR
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    result = landmarker.detect_for_video(mp_image, timestamp_ms)
    # result.pose_landmarks: list[list[NormalizedLandmark]]
    # result.pose_world_landmarks: list[list[Landmark]] (scale-invariant, meters)
```

### Pattern 2: Skeleton Rendering Fix — Integer Index Keys

**What:** Build the landmark map keyed by list position (integer), not by `lm["name"]`.
The connection list already uses integer pairs — the map key type just needs to match.

**Current broken code (analysis.py:179–186):**
```python
lm_map = {lm["name"]: (int(lm["x"]), int(lm["y"])) for lm in landmarks}
for start_idx, end_idx in connections:
    start_name = f"LANDMARK_{start_idx}"   # never matches any key
    end_name = f"LANDMARK_{end_idx}"       # never matches any key
    if start_name in lm_map and end_name in lm_map:
        cv2.line(...)
```

**Fixed pattern:**
```python
# lm dict must include "index" key (set in pose.py during landmark serialization)
lm_map = {}
for lm in landmarks:
    if lm.get("visibility", 0) > 0.5:
        lm_map[lm["index"]] = (int(lm["x"]), int(lm["y"]))

for start_idx, end_idx in connections:
    if start_idx in lm_map and end_idx in lm_map:
        cv2.line(frame, lm_map[start_idx], lm_map[end_idx], (0, 255, 255), 2)
```

The landmark dicts produced by `pose.py` must include `"index"` (integer position in the 33-element list). `_draw_skeleton` must use `lm["index"]` as the map key.

### Pattern 3: H.264 Video Output — avc1 Unavailable, Use FFmpeg Fallback

**What:** `avc1` VideoWriter does not open in this environment (confirmed: `writer.isOpened()` returns `False`). ffmpeg is not installed. Two resolution paths:

**Path A — install ffmpeg system binary + subprocess transcode (recommended):**
```python
import subprocess
import os

# Write with mp4v first (always works)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
# ... write frames ...
writer.release()

# Transcode to H.264
subprocess.run([
    "ffmpeg", "-y", "-i", tmp_path,
    "-vcodec", "libx264", "-crf", "23", "-preset", "fast",
    "-pix_fmt", "yuv420p",   # required for broad browser compat
    output_path
], check=True)
os.unlink(tmp_path)
```

`-pix_fmt yuv420p` is required — browsers do not play yuv444p.

**Path B — add `imageio-ffmpeg` to pyproject.toml:**
Bundles its own FFmpeg binary. Eliminates system dependency. Slightly heavier install.

**Decision needed:** The planning task must choose Path A or B. Path A requires the machine
running the backend to have ffmpeg installed. For development/club deployment on Linux this
is straightforward (`apt install ffmpeg`). Path B is self-contained. **Recommend Path A with
a startup check** — log a warning at app start if ffmpeg is not on PATH.

### Pattern 4: VideoCapture Lifecycle Fix

**What:** `detect_persons(video_path, frame_idx)` is called inside the analysis loop
~150 times, each opening a fresh `VideoCapture`. Fix: open once, pass `cap` directly.

**Current (analyze.py:_run_analysis):**
```python
for frame_idx in range(0, min(frame_count, 300), 2):
    frame, persons = detect_persons(video_path, frame_idx)  # opens VideoCapture each call
```

**Fixed pattern:** Open cap before the loop, read sequentially, pass frame + existing
cap to detection:
```python
cap = cv2.VideoCapture(video_path)
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        persons = detect_persons_from_frame(frame)  # new signature, no cap open
        ...
finally:
    cap.release()
```

**NOTE:** `cap.set(cv2.CAP_PROP_POS_FRAMES, n)` is unreliable for H.264/HEVC sources due
to keyframe dependencies. Sequential read is correct here — the loop already processes
frames in order.

### Pattern 5: Filename Sanitization + File Type Validation

**Sanitization — REST upload (upload.py):**
```python
import re
from pathlib import Path

def _sanitize_filename(raw: str) -> str:
    # Strip path components — take only the basename
    name = Path(raw).name
    # Allow only safe characters: alphanumeric, dash, underscore, dot
    name = re.sub(r"[^\w.\-]", "_", name)
    # Prevent hidden files and double-dot sequences
    name = name.lstrip(".")
    return name or "upload"
```

**Sanitization — TUS create (tus.py):** Apply same `_sanitize_filename` to decoded
filename at line 59 before passing to `storage.create_upload`.

**File type validation — REST endpoint:**
```python
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
ALLOWED_MIME_TYPES = {"video/mp4", "video/avi", "video/quicktime",
                       "video/x-msvideo", "video/webm", "video/x-matroska"}

ext = Path(sanitized_filename).suffix.lower()
content_type = file.content_type or ""

if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(status_code=415, detail="Unsupported file type")
if content_type and content_type not in ALLOWED_MIME_TYPES:
    raise HTTPException(status_code=415, detail="Unsupported content type")
```

**File type validation — TUS create:** Check extension of decoded filename. The TUS
protocol does not carry a Content-Type for the video itself (PATCH uses
`application/offset+octet-stream`), so extension check only.

**Size limit — REST endpoint:** Currently absent. TUS already enforces `TUS_MAX_SIZE`
(10 GB). Add `MAX_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024` to `upload.py` and check
`len(content)` after `await file.read()`, or use `Content-Length` header for early reject.

### Anti-Patterns to Avoid

- **Using `mediapipe.solutions.pose`:** Not present in mediapipe 0.10.33. Only the Tasks
  API exists. FEATURES.md shows a `solutions.pose` example — this will `AttributeError`
  at import. Do not use it.
- **Module-level `PoseLandmarker` instance:** Not thread-safe. With `max_workers=2`, two
  concurrent analysis jobs would share the same instance. Instantiate inside `_run_analysis`.
- **`cap.set(CAP_PROP_POS_FRAMES, n)` for every frame:** Unreliable for H.264. Use
  sequential `cap.read()` in a loop instead.
- **Trusting client-supplied MIME type alone:** `file.content_type` is set by the browser
  and can be spoofed. Combine with extension check as defense-in-depth.
- **`avc1` without isOpened() check:** `cv2.VideoWriter` fails silently when the codec is
  unavailable. Always call `writer.isOpened()` immediately after construction.
- **Writing frames at wrong dimensions to VideoWriter:** VideoWriter silently drops frames
  if shape doesn't match constructor dimensions. Annotated frames must be `(width, height)`
  exactly as passed to `cv2.VideoWriter`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pose estimation | Custom keypoint detector | MediaPipe Tasks API | Already integrated; 33 landmarks; temporal smoothing in VIDEO mode |
| H.264 encoding | OpenCV-only encoding workaround | ffmpeg subprocess | avc1 is broken in this env; ffmpeg is the authoritative solution |
| Path traversal prevention | Custom regex | `Path(raw).name` (stdlib pathlib) | `.name` strips all leading path components including `../` chains |
| Video type detection | Magic byte parser | Extension + Content-Type header check | python-magic not installed; extension allowlist is adequate for a club tool |

**Key insight:** All five Phase 1 problems are fixes to existing code, not new features.
The hard part is understanding exactly what's broken and what the correct replacement is —
not building a new component.

---

## Common Pitfalls

### Pitfall 1: `mediapipe.solutions` Does Not Exist

**What goes wrong:** Code that imports `mp.solutions.pose` raises `AttributeError:
module 'mediapipe' has no attribute 'solutions'` at runtime.

**Why it happens:** mediapipe 0.10+ dropped the `solutions` submodule on the standard
PyPI distribution. Only the Tasks API is bundled.

**How to avoid:** Use only `mediapipe.tasks.python.vision.pose_landmarker`. All FEATURES.md
examples using `mp.solutions.pose` are wrong for this installation.

**Warning signs:** Any `from mediapipe.python.solutions import pose` or
`mp.solutions.pose.Pose(...)` in code.

### Pitfall 2: No Model File — PoseLandmarker Fails to Initialize

**What goes wrong:** `PoseLandmarker.create_from_options(options)` raises a runtime error
because the `.task` bundle file path in `BaseOptions(model_asset_path=...)` does not exist.

**Why it happens:** The model file is not committed to the repo (correct — it's ~28 MB).
There is no download script and no `POSE_MODEL_PATH` env var.

**How to avoid:** The plan must include a Wave 0 step to: (a) add the download command to
the project README or a setup script, and (b) read the path from `POSE_MODEL_PATH` env var
with a fallback to `backend/pose_landmarker_full.task`.

**Warning signs:** Any test or manual run of `estimate_pose` fails with "model file not
found" before the skeleton fix can be verified.

### Pitfall 3: avc1 VideoWriter Silently Fails

**What goes wrong:** `cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"avc1"), fps, size)`
returns a writer object where `writer.isOpened()` is `False`. All frames are silently
discarded. Output file is 0 bytes or corrupt.

**Why it happens:** `opencv-python-headless` on Linux frequently lacks H.264 encoder
support due to GPL licensing. Verified: `isOpened()` returns `False` in this environment.

**How to avoid:** Never assume the writer opened — always check. Use `mp4v` for writing
then transcode with FFmpeg.

**Warning signs:** Annotated video file exists but is 0 bytes or unreadable.

### Pitfall 4: FFmpeg Not Installed

**What goes wrong:** `subprocess.run(["ffmpeg", ...])` raises `FileNotFoundError` or
`subprocess.CalledProcessError` because `ffmpeg` is not on PATH.

**Why it happens:** ffmpeg is confirmed absent on this machine.

**How to avoid:** The plan must include a task to install ffmpeg before the codec fix
is implemented. Add a startup check in `main.py` that warns if ffmpeg is absent.

**Warning signs:** `which ffmpeg` returns nothing.

### Pitfall 5: Skeleton Uses Pixel Coords but analysis.py Uses Mixed Coordinate Spaces

**What goes wrong:** The current `_draw_skeleton` receives landmark dicts and does
`int(lm["x"])` directly as a pixel coordinate. With the Tasks API, `NormalizedLandmark.x`
is in [0,1] — `int(0.44)` is `0`. All skeleton points cluster at the origin.

**Why it happens:** The existing analysis code was written for a pixel-space landmark
format. The Tasks API returns normalized coordinates.

**How to avoid:** `pose.py` must convert normalized coords to pixel space before building
the landmark dict, using the crop + full-frame projection pattern from DOMAIN.md §1.5.
The stored `lm["x"]` and `lm["y"]` must be full-frame pixel coordinates, not [0,1] values.

**Warning signs:** Skeleton renders but all points appear at (0, 0).

### Pitfall 6: Wrist Speed Detection Breaks After pose.py Fix

**What goes wrong:** `_detect_shots` in `analysis.py` currently accesses `lm["name"]`
to find `"RIGHT_WRIST"` or `"LEFT_WRIST"`. The landmark dict must retain `"name"` after
the pose fix so shot detection continues to work.

**Why it happens:** Fixing pose.py changes the shape of landmark dicts. If `"name"` is
dropped, `_detect_shots` silently counts zero shots.

**How to avoid:** Landmark dicts must include both `"index"` (for skeleton) and `"name"`
(for named lookups). The Tasks API does not populate `NormalizedLandmark.name` reliably —
derive name from the `PoseLandmark` enum: `PoseLandmark(idx).name`.

**Warning signs:** Shot count is 0 in all analyses after PIPE-01 is implemented.

### Pitfall 7: VideoCapture Sequential Read vs. Stride Sampling

**What goes wrong:** The current analysis loop uses `range(0, min(frame_count, 300), 2)` —
a stride of 2, sampling every other frame. With sequential `cap.read()`, the loop reads
every frame but only processes alternate ones. This doubles processing time unnecessarily.

**Why it happens:** The loop was designed for seek-per-frame access. After switching to
sequential read, the stride logic must be adapted.

**How to avoid:** In sequential read mode, skip processing on odd frames (or stride by
calling `cap.read()` twice per processed frame, discarding the skipped frame). The frame
index counter and `timestamp_ms` calculation must remain correct regardless of stride.

---

## Code Examples

Verified patterns from official sources or direct codebase inspection:

### MediaPipe Tasks API — Import Chain (verified in venv)

```python
# All three imports verified working in backend/.venv mediapipe 0.10.33
import mediapipe as mp
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
```

### Landmark Serialization from Tasks API Result

```python
# Source: DOMAIN.md §2.3 + verified NormalizedLandmark fields from installed package
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmark

def _serialize_landmarks(result, frame_width: int, frame_height: int) -> list[dict] | None:
    if not result.pose_landmarks:
        return None
    landmarks = []
    for idx, lm in enumerate(result.pose_landmarks[0]):
        landmarks.append({
            "index": idx,                              # integer — for skeleton key
            "name": PoseLandmark(idx).name,            # string — for named lookups
            "x": lm.x * frame_width,                  # pixel coords, full frame
            "y": lm.y * frame_height,
            "z": lm.z,
            "visibility": lm.visibility or 0.0,
            "presence": lm.presence or 0.0,
        })
    return landmarks
```

### Skeleton Rendering Fix

```python
# Source: analysis.py lines 165-191 (existing structure), fix derived from DOMAIN.md §2.2
def _draw_skeleton(frame: np.ndarray, landmarks: list[dict]) -> None:
    connections = [
        (0,1),(1,2),(2,3),(3,7),
        (0,4),(4,5),(5,6),(6,8),
        (9,10),(11,12),(11,13),(13,15),(15,17),(15,19),(15,21),(17,19),
        (12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
        (11,23),(12,24),(23,24),(23,25),(24,26),(25,27),(26,28),
        (27,29),(28,30),(29,31),(30,32),(27,31),(28,32),
    ]
    # Key by integer index, not name string
    lm_map = {}
    for lm in landmarks:
        if lm.get("visibility", 0) > 0.5:
            lm_map[lm["index"]] = (int(lm["x"]), int(lm["y"]))

    for start_idx, end_idx in connections:
        if start_idx in lm_map and end_idx in lm_map:
            cv2.line(frame, lm_map[start_idx], lm_map[end_idx], (0, 255, 255), 2)

    for lm in landmarks:
        if lm.get("visibility", 0) > 0.5:
            cv2.circle(frame, (int(lm["x"]), int(lm["y"])), 3, (0, 0, 255), -1)
```

### H.264 Output via FFmpeg Subprocess

```python
# Source: DOMAIN.md §6.2; subprocess pattern standard
import subprocess, os

def _transcode_to_h264(tmp_path: str, output_path: str) -> None:
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tmp_path,
        "-vcodec", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",   # required for Safari/Chrome compatibility
        output_path
    ], check=True, capture_output=True)
    os.unlink(tmp_path)
```

### Filename Sanitization

```python
# Source: standard security practice; pathlib strips traversal
import re
from pathlib import Path

def _sanitize_filename(raw: str | None) -> str:
    if not raw:
        return "upload"
    name = Path(raw).name          # strips ../ and absolute paths
    name = re.sub(r"[^\w.\-]", "_", name)  # allow only safe chars
    name = name.lstrip(".")        # no hidden files
    return name or "upload"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mediapipe.solutions.pose` (legacy) | `mediapipe.tasks.python.vision.pose_landmarker` (Tasks API) | mediapipe 0.9+ | `solutions` not available in this install — must use Tasks API |
| `mp4v` fourcc for web output | H.264 via `avc1` or FFmpeg transcode | Always been the case | `avc1` not working here; FFmpeg transcode required |

**Deprecated/outdated:**
- `mediapipe.solutions.pose.Pose()`: Dropped from PyPI distribution in 0.10.x. All
  FEATURES.md examples using this API are wrong for the installed version.
- `cv2.VideoWriter_fourcc(*"avc1")`: Nominally available as a fourcc constant (value
  `828601953`) but the writer fails to open in `opencv-python-headless` without FFmpeg
  headers. Confirmed non-functional in this environment.

---

## Open Questions

1. **FFmpeg install approach**
   - What we know: ffmpeg is not present; `avc1` does not work without it; `mp4v` plays
     in some desktop players but not browsers
   - What's unclear: Should the plan use system `apt install ffmpeg` (simple, path
     dependency) or `uv add imageio-ffmpeg` (self-contained, adds ~50MB)?
   - Recommendation: System ffmpeg is simpler for a Linux server deployment. Add
     `imageio-ffmpeg` as fallback. The plan should include a Wave 0 task to install ffmpeg.

2. **Pose model file location and management**
   - What we know: `pose_landmarker_full.task` (~28 MB) must exist on disk; no download
     script exists; the model URL is known
   - What's unclear: Should the model be committed to git (too large), added to
     `.gitignore` + downloaded by a setup script, or managed via an env var?
   - Recommendation: Add `backend/pose_landmarker_full.task` to `.gitignore`, create a
     `scripts/download_models.sh` script, and read path from `POSE_MODEL_PATH` env var
     with a fallback default.

3. **REST upload size limit**
   - What we know: `await file.read()` loads the entire file into memory — no streaming.
     TUS has a 10 GB limit. The REST endpoint has no limit.
   - What's unclear: Is the REST upload endpoint still used by any frontend path, or has
     TUS replaced it entirely?
   - Recommendation: Add 4 GB limit to the REST endpoint (check `Content-Length` header
     for early reject before reading body). Keep TUS as the recommended path for large files.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.0 + pytest-asyncio 0.24.0 |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| Quick run command | `cd backend && .venv/bin/python -m pytest tests/ -q` |
| Full suite command | `cd backend && .venv/bin/python -m pytest tests/ -v` |

**Current state:** 38 tests, all passing.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | `estimate_pose()` returns list of 33 landmark dicts (not None) for a valid frame | unit | `pytest tests/test_pose.py -x` | Wave 0 |
| PIPE-01 | `estimate_pose()` returns None when bbox is empty/zero-size crop | unit | `pytest tests/test_pose.py::test_estimate_pose_empty_bbox -x` | Wave 0 |
| PIPE-02 | `_draw_skeleton()` draws ≥1 line when visibility > 0.5 landmarks present | unit | `pytest tests/test_skeleton.py -x` | Wave 0 |
| PIPE-02 | landmark dict with `"index"` key is consumed correctly by `_draw_skeleton` | unit | `pytest tests/test_skeleton.py::test_draw_skeleton_uses_index -x` | Wave 0 |
| PIPE-03 | `render_annotated_video()` produces a non-zero-byte output file | unit | `pytest tests/test_analysis_render.py -x` | Wave 0 |
| PIPE-04 | Analysis loop opens VideoCapture once (not per-frame) | unit | `pytest tests/test_analyze_lifecycle.py -x` | Wave 0 |
| PIPE-05 | `_sanitize_filename("../../etc/passwd")` returns `"etc_passwd"` or similar | unit | `pytest tests/test_sanitize.py -x` | Wave 0 |
| PIPE-05 | TUS POST with traversal filename stores sanitized name in meta.json | integration | `pytest tests/test_tus.py::test_tus_filename_sanitization -x` | Wave 0 |
| PIPE-06 | REST upload of `.exe` file returns 415 | integration | `pytest tests/test_upload.py::test_upload_rejects_non_video -x` | Wave 0 |
| PIPE-06 | TUS POST with `.exe` filename returns 415 | integration | `pytest tests/test_tus.py::test_tus_rejects_non_video -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && .venv/bin/python -m pytest tests/ -q`
- **Per wave merge:** `cd backend && .venv/bin/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_pose.py` — covers PIPE-01 (estimate_pose unit tests)
- [ ] `tests/test_skeleton.py` — covers PIPE-02 (_draw_skeleton with index-keyed landmarks)
- [ ] `tests/test_analysis_render.py` — covers PIPE-03 (render produces non-empty file)
- [ ] `tests/test_analyze_lifecycle.py` — covers PIPE-04 (VideoCapture open count)
- [ ] `tests/test_sanitize.py` — covers PIPE-05 (sanitize_filename unit tests)
- [ ] Add `test_tus_filename_sanitization` to `tests/test_tus.py` — covers PIPE-05 TUS path
- [ ] Add `test_upload_rejects_non_video` to `tests/test_upload.py` — covers PIPE-06 REST
- [ ] Add `test_tus_rejects_non_video` to `tests/test_tus.py` — covers PIPE-06 TUS

**Note on PIPE-03 testability:** A full render test requires either a real video file
or mocking `cv2.VideoCapture`. For Wave 0, test that `render_annotated_video` calls
`writer.isOpened()` and falls back to FFmpeg when `avc1` fails. The FFmpeg transcode
itself can be mocked with `unittest.mock.patch("subprocess.run")`.

---

## Sources

### Primary (HIGH confidence)

- `backend/services/pose.py` — confirmed stub returning None unconditionally
- `backend/services/analysis.py:165–191` — confirmed skeleton bug (name-keyed map vs. LANDMARK_N lookup)
- `backend/services/analysis.py:127` — confirmed `mp4v` fourcc
- `backend/routers/analyze.py:_run_analysis` — confirmed per-frame VideoCapture via `detect_persons(video_path, frame_idx)`
- `backend/routers/upload.py:16` — confirmed unsanitized `file.filename` in path join
- `backend/routers/tus.py:55–63` — confirmed unsanitized base64-decoded filename
- `backend/.venv` mediapipe 0.10.33 — confirmed `solutions` module absent; Tasks API importable
- `backend/.venv` opencv 4.13.0 — confirmed `avc1` `isOpened()` returns `False`
- System `which ffmpeg` — confirmed ffmpeg not installed
- `backend/pyproject.toml` — confirmed no `python-magic` or `filetype` dependency
- `.planning/research/DOMAIN.md` — landmark map, connection list, Tasks API usage, codec fix pattern
- `.planning/research/FEATURES.md` — codec fix, skeleton fix, VideoCapture fix patterns

### Secondary (MEDIUM confidence)

- DOMAIN.md §6.2 FFmpeg subprocess pattern — well-established; cross-referenced with FEATURES.md §4
- DOMAIN.md §2.2 connection list — claimed to be copied from `PoseLandmarksConnections.POSE_LANDMARKS`; not re-verified in this research session but consistent with MediaPipe documentation

### Tertiary (LOW confidence)

- `-pix_fmt yuv420p` requirement for browser compatibility — widely cited; not verified against current browser specs in this session but consistent across multiple sources in domain research

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions confirmed from installed packages
- Architecture: HIGH — all bugs confirmed from direct source inspection
- Pitfalls: HIGH — all pitfalls derived from verified code behavior (avc1 tested live, solutions API tested live)
- Test map: MEDIUM — test file contents are Wave 0 stubs; exact implementation details will vary

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (stable libraries; codec behavior unlikely to change)
