# Badminton Analysis

## What This Is

An AI-powered badminton coaching tool for club players. Upload a match video, click to select the player you want to focus on, and receive a full coaching report: an annotated video with pose overlay, movement and footwork analysis, shot mechanics scoring, and AI-written technique feedback — all presented in a single results dashboard.

## Core Value

A player uploads a match video and gets actionable coaching feedback on their movement and technique — without needing a human coach in the room.

## Requirements

### Validated

<!-- Existing capabilities confirmed in codebase -->

- ✓ Video upload via REST API (`POST /api/upload`) — existing
- ✓ Video upload via TUS resumable protocol — existing
- ✓ Video storage, retrieval, and serving — existing
- ✓ Basic analysis job lifecycle (create, poll status) — existing
- ✓ Player selection UI (bounding box, frontend) — existing (to be replaced)
- ✓ React frontend with upload and selection flow — existing

### Active

<!-- What we're building toward -->

- [ ] Pose estimation implemented — extract joint positions per frame (currently a stub)
- [ ] Skeleton overlay rendering fixed and working on annotated video
- [ ] Click-to-select player — detected persons highlighted, user clicks to focus
- [ ] Movement & positioning analysis — court coverage heatmap, footwork pattern tracking
- [ ] Shot mechanics analysis — swing arc, body posture, joint angles per shot
- [ ] Annotated video output — pose skeleton drawn on original video, playable in browser
- [ ] Results dashboard — annotated video + stats + AI coaching notes + scored metrics
- [ ] AI-generated coaching notes — text feedback derived from pose and movement data
- [ ] Scored metrics — footwork, posture, court coverage scored (e.g. 7/10 per category)
- [ ] Side-by-side comparison — vs. ideal form or previous sessions

### Out of Scope

- Real-time live analysis — processing latency makes this impractical for v1
- Multi-player simultaneous analysis — focus one player per analysis run
- Mobile app — web-first
- Public sign-up / SaaS — club/team use only, no public auth needed for v1
- Automated shot detection / labelling — too complex for v1; manual tagging deferred

## Context

- **Existing codebase**: FastAPI backend + React frontend. Upload pipeline (both legacy and TUS) is working. Analysis pipeline scaffolding exists but is broken in two key places: pose estimation is a stub returning `None`, and skeleton rendering uses wrong landmark key names (`"LANDMARK_N"` vs `"RIGHT_WRIST"` etc).
- **Known issues to resolve**: Path traversal vulnerabilities in both upload paths (filenames not sanitized), in-memory job state (won't survive restarts), no file type validation.
- **Pose model**: MediaPipe Pose is the likely choice (already in project dependencies); needs to be wired in.
- **For**: A badminton club/team — small group of known users, not a public product.

## Constraints

- **Tech stack**: Python/FastAPI backend, React frontend — do not introduce new languages
- **Pose model**: Use MediaPipe Pose (already available in env) — avoid heavy GPU-only models
- **Output format**: Annotated video must be playable in browser (H.264/MP4)
- **Deployment**: Single-machine deployment assumed — no distributed job queue for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Click-to-select over bounding box draw | More intuitive UX; existing bounding-box UI is fragile at 640×480 hardcode | — Pending |
| MediaPipe Pose for estimation | Already in dependencies, CPU-capable, good accuracy for single-person | — Pending |
| Single player per analysis run | Simplifies tracking, avoids multi-person occlusion complexity | — Pending |
| Results dashboard (video + stats + AI notes) | User wants full coaching report, not just overlay | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-29 after initialization*
