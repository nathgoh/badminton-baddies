# Requirements: Badminton Analysis

**Defined:** 2026-03-29
**Core Value:** A player uploads a match video and gets actionable coaching feedback on their movement and technique — without needing a human coach in the room.

## v1 Requirements

### Pipeline Foundation

- [ ] **PIPE-01**: Pose estimation is implemented — MediaPipe Pose extracts joint landmarks per frame in VIDEO mode
- [ ] **PIPE-02**: Skeleton overlay renders correctly on annotated video — landmark connections drawn using integer index keys
- [ ] **PIPE-03**: Annotated video is browser-playable — output encoded as H.264 (not MPEG-4 Part 2)
- [ ] **PIPE-04**: Video processing uses a single VideoCapture instance across all frames (not per-frame open/close)
- [ ] **PIPE-05**: Upload filenames are sanitized against path traversal on both REST and TUS endpoints
- [ ] **PIPE-06**: File type validation enforced on upload (video files only)

### Player Selection

- [ ] **SEL-01**: Detected persons are highlighted in the first frame as clickable regions
- [ ] **SEL-02**: User clicks a highlighted person to select the player to analyze
- [ ] **SEL-03**: Bounding box overlay coordinates are calculated from actual video dimensions (not hardcoded 640×480)
- [ ] **SEL-04**: Selected player is tracked throughout the video using their bounding box as an anchor for pose estimation

### Movement Analysis

- [ ] **MOV-01**: Player court position is tracked frame-by-frame and mapped to a normalized court grid
- [ ] **MOV-02**: Court coverage heatmap is computed (% of zones visited)
- [ ] **MOV-03**: Footwork patterns are identified (lunge, split step, recovery)
- [ ] **MOV-04**: Movement speed is estimated from position deltas between frames

### Shot Mechanics Analysis

- [ ] **SHOT-01**: Overhead contact elbow angle is measured (ideal: 150–180°) using world landmarks
- [ ] **SHOT-02**: Shoulder rotation is measured at point of contact
- [ ] **SHOT-03**: Knee bend depth during lunge is measured
- [ ] **SHOT-04**: Wrist height relative to shoulder at contact is tracked

### Scoring Engine

- [ ] **SCORE-01**: Each mechanics metric produces a 1–10 score using threshold-based scoring functions
- [ ] **SCORE-02**: Movement score computed from court coverage and footwork quality
- [ ] **SCORE-03**: Overall technique score aggregated from mechanics subscores
- [ ] **SCORE-04**: Scoring thresholds are configurable (not hardcoded magic numbers)

### Coaching Output

- [ ] **COACH-01**: AI coaching notes generated from scoring data — rule-based text describing what needs improvement
- [ ] **COACH-02**: Annotated video playable in browser with pose skeleton overlay
- [ ] **COACH-03**: Court coverage heatmap rendered as a visual grid overlay
- [ ] **COACH-04**: Scored metric cards shown per category (footwork, mechanics, coverage)
- [ ] **COACH-05**: Analysis progress is surfaced in the UI during processing

### Results Dashboard

- [ ] **DASH-01**: Single results page shows annotated video + stats + coaching notes
- [ ] **DASH-02**: Scored metrics displayed with visual indicators (e.g. progress bars or score rings)
- [ ] **DASH-03**: Coaching notes panel with specific, actionable text per category
- [ ] **DASH-04**: Dashboard is shareable (stable URL per analysis run)

## v2 Requirements

### Advanced Coaching

- **ADV-01**: LLM-enriched coaching notes (GPT/Claude pass over rule-based output for more natural language)
- **ADV-02**: Side-by-side comparison against ideal form reference or previous session
- **ADV-03**: Session history — player can view past analyses and track improvement over time

### Platform

- **PLAT-01**: User accounts / authentication for club members
- **PLAT-02**: Coach dashboard — view and comment on multiple players' analyses
- **PLAT-03**: Multi-match aggregate stats across sessions

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time live video analysis | Processing latency incompatible with real-time; v1 is upload-and-wait |
| Simultaneous multi-player analysis | Complicates tracking; one player per run is sufficient for v1 |
| Mobile native app | Web-first; browser video player is adequate |
| Public SaaS / open sign-up | Club/team tool only; no public auth for v1 |
| Automated shot labelling | Requires separate shot-detection model; out of scope for v1 |
| GPU-dependent pose models | Club deployment assumed CPU-only; MediaPipe handles this |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 1 | Pending |
| PIPE-02 | Phase 1 | Pending |
| PIPE-03 | Phase 1 | Pending |
| PIPE-04 | Phase 1 | Pending |
| PIPE-05 | Phase 1 | Pending |
| PIPE-06 | Phase 1 | Pending |
| SEL-01 | Phase 2 | Pending |
| SEL-02 | Phase 2 | Pending |
| SEL-03 | Phase 2 | Pending |
| SEL-04 | Phase 2 | Pending |
| MOV-01 | Phase 2 | Pending |
| MOV-02 | Phase 2 | Pending |
| MOV-03 | Phase 2 | Pending |
| MOV-04 | Phase 2 | Pending |
| SHOT-01 | Phase 2 | Pending |
| SHOT-02 | Phase 2 | Pending |
| SHOT-03 | Phase 2 | Pending |
| SHOT-04 | Phase 2 | Pending |
| SCORE-01 | Phase 2 | Pending |
| SCORE-02 | Phase 2 | Pending |
| SCORE-03 | Phase 2 | Pending |
| SCORE-04 | Phase 2 | Pending |
| COACH-01 | Phase 3 | Pending |
| COACH-02 | Phase 3 | Pending |
| COACH-03 | Phase 3 | Pending |
| COACH-04 | Phase 3 | Pending |
| COACH-05 | Phase 3 | Pending |
| DASH-01 | Phase 3 | Pending |
| DASH-02 | Phase 3 | Pending |
| DASH-03 | Phase 3 | Pending |
| DASH-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after initial definition*
