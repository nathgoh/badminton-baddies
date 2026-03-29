# Roadmap: Badminton Analysis

**Milestone:** v1 — Working coaching tool for club use
**Granularity:** Coarse (3 phases)
**Created:** 2026-03-29

---

## Phase 1: Pipeline Foundation

**Goal:** The analysis pipeline works end-to-end. Pose estimation is real, skeleton renders correctly, video output plays in the browser, uploads are safe.

**Why first:** Nothing downstream produces usable output until these three blockers are resolved: pose stub returns `None`, skeleton lookup uses wrong key type, video codec is incompatible with browsers.

### Plans

1. **Implement pose estimation** — Wire MediaPipe Pose into `services/pose.py` using `VisionTaskRunningMode.VIDEO`; return per-frame landmark list with index, name, x, y, z, confidence
2. **Fix skeleton rendering** — Update `_draw_skeleton` in `services/analysis.py` to key connections by integer landmark index (not `"LANDMARK_N"` strings); validate against the 35-connection list from MediaPipe
3. **Fix video output codec** — Change `cv2.VideoWriter_fourcc` from `mp4v` to `avc1`; add FFmpeg subprocess fallback if `avc1` writer fails to open
4. **Fix VideoCapture lifecycle** — Open `VideoCapture` once per analysis, seek to frame using `cap.set(cv2.CAP_PROP_POS_FRAMES, i)` instead of per-frame open/close
5. **Security: upload hardening** — Sanitize filenames on TUS and REST upload (strip `../`, restrict to safe chars); add MIME type + extension validation; add server-side size limit to legacy endpoint

**Requirements covered:** PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06

**Verification:** Upload a test video → analysis completes → annotated video plays in browser with skeleton visible

---

## Phase 2: Analysis Engine

**Goal:** Player selection works via click, and the system produces real movement and shot mechanics data with per-metric scores.

**Why second:** Requires Phase 1's working pose output as input. All scoring and coaching output depends on this data layer existing.

### Plans

1. **Click-to-select player** — Backend: detect persons in first frame, return bounding boxes; Frontend: replace bounding-box-draw UI with clickable person highlights; fix SelectPage coordinate calculation to use actual video dimensions
2. **Player tracking** — Use selected bounding box as crop region; pass cropped frame to pose estimator to avoid multi-person ambiguity; propagate tracking across frames
3. **Movement analysis** — Track ankle/hip midpoint position per frame; map to normalized court grid (6×4 zones); compute coverage %, speed estimates, footwork event detection (lunge, split step)
4. **Shot mechanics analysis** — Use `pose_world_landmarks` for scale-invariant angles; compute elbow angle at overhead contact (150–180° ideal), shoulder rotation, knee bend, wrist height
5. **Scoring engine** — Create `services/scoring.py`; implement threshold-based 1–10 scoring for each metric; expose `CoachingReport` schema from analysis endpoint

**Requirements covered:** SEL-01, SEL-02, SEL-03, SEL-04, MOV-01, MOV-02, MOV-03, MOV-04, SHOT-01, SHOT-02, SHOT-03, SHOT-04, SCORE-01, SCORE-02, SCORE-03, SCORE-04

**Verification:** Upload video → click player → analysis returns scores for movement and mechanics categories

---

## Phase 3: Coaching Dashboard

**Goal:** Players see a full coaching report — annotated video, heatmap, scored metric cards, and rule-based coaching notes — on a shareable results page.

**Why last:** Consumer of everything Phase 1 and 2 produce. Pure presentation layer with no new data computation.

### Plans

1. **Annotated video with skeleton** — Render pose skeleton on each frame of output video; ensure skeleton uses corrected index-keyed connections; confirm H.264 playable in browser
2. **Court coverage heatmap** — Render normalized court grid as a visual overlay/image; colour zones by visit frequency; include in analysis result payload
3. **Scoring + coaching notes UI** — Build `CoachingReport` component: scored metric cards with visual indicators; rule-based coaching notes panel (e.g. "Elbow extension at contact: 6/10 — try to extend arm more fully on overhead shots")
4. **Results dashboard** — Single-page results view with annotated video player + stats + heatmap + coaching report; stable shareable URL per analysis ID
5. **Progress indicator** — Surface `AnalysisStatus.progress` in frontend during processing; replace current static "processing..." with live progress bar

**Requirements covered:** COACH-01, COACH-02, COACH-03, COACH-04, COACH-05, DASH-01, DASH-02, DASH-03, DASH-04

**Verification:** Full end-to-end: upload video → click player → wait → results page shows annotated video, heatmap, scores, and actionable coaching notes

---

## Coverage Check

| Phase | Requirements | Count |
|-------|-------------|-------|
| Phase 1 | PIPE-01 – PIPE-06 | 6 |
| Phase 2 | SEL-01–04, MOV-01–04, SHOT-01–04, SCORE-01–04 | 16 |
| Phase 3 | COACH-01–05, DASH-01–04 | 9 |
| **Total** | | **31** |

v1 requirements: 30 ✓ (DASH-04 shareable URL is a bonus from Phase 3)

---

## Open Questions (from research)

- Is `ffmpeg` available as a system binary? Affects Phase 1 H.264 fallback strategy.
- What threshold values for scoring functions? Coach input needed to author `IDEAL_RANGES` dict — tackle in Phase 2 planning.
- Should `Pose` object be instantiated per-analysis or use `threading.local()`? Per-analysis is safe for 2-worker setup; address in Phase 1.

---
*Roadmap created: 2026-03-29*
