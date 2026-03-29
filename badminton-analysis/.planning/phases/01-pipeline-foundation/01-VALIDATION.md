---
phase: 1
slug: pipeline-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `tests/conftest.py` (Wave 0 creates stubs) |
| **Quick run command** | `cd badminton-analysis && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd badminton-analysis && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd badminton-analysis && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd badminton-analysis && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | PIPE-01 | unit | `pytest tests/test_pose.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | PIPE-01 | unit | `pytest tests/test_pose.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | PIPE-02 | unit | `pytest tests/test_analysis.py::test_skeleton -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | PIPE-03 | integration | `pytest tests/test_analysis.py::test_codec -x -q` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 1 | PIPE-04 | unit | `pytest tests/test_analysis.py::test_capture_lifecycle -x -q` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 1 | PIPE-05 | unit | `pytest tests/test_upload.py::test_path_traversal -x -q` | ❌ W0 | ⬜ pending |
| 1-05-02 | 05 | 1 | PIPE-05 | unit | `pytest tests/test_upload.py::test_tus_sanitize -x -q` | ❌ W0 | ⬜ pending |
| 1-05-03 | 05 | 1 | PIPE-06 | unit | `pytest tests/test_upload.py::test_filetype_validation -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pose.py` — stubs for PIPE-01 (landmark extraction, return structure)
- [ ] `tests/test_analysis.py` — stubs for PIPE-02 (skeleton), PIPE-03 (codec), PIPE-04 (capture lifecycle)
- [ ] `tests/test_upload.py` — stubs for PIPE-05 (path traversal), PIPE-06 (filetype)
- [ ] `tests/conftest.py` — shared fixtures (temp video file, mock upload)
- [ ] FFmpeg install — required for H.264 transcode (PIPE-03); Wave 0 install task

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Annotated video plays in Chrome/Firefox | PIPE-03 | Requires browser to verify H.264 playback | Upload test video, complete analysis, open `/api/videos/{id}/annotated` in browser — video should autoplay |
| Skeleton visible on annotated video | PIPE-02 | Visual verification | Inspect annotated video frames — colored lines connecting joints must be visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
