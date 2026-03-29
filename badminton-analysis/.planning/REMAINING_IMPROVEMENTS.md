# Remaining Improvements & Implementation Gaps

**Date:** 2026-03-29
**Context:** Based on cross-referencing `.planning` documents (`ROADMAP.md`, `STATE.md`) and the `docs/superpowers/specs/2026-03-29-large-video-upload-design.md` with the current source code.

The current implementation is still incomplete and has several critical areas of improvement (mostly outstanding items from **Phase 1: Pipeline Foundation** and the **Large Video Upload** design).

## 1. Missing Pose Estimation (Phase 1, Plan 1)
* **Requirement:** Wire MediaPipe Pose into `services/pose.py` using `VisionTaskRunningMode.VIDEO` to return real per-frame landmark lists.
* **Current State:** `backend/services/pose.py` is still just a stub. The `estimate_pose` function returns `None` and contains a `TODO: Implement proper MediaPipe pose estimation`.

## 2. Broken Skeleton Rendering (Phase 1, Plan 2)
* **Requirement:** Update `_draw_skeleton` in `services/analysis.py` to key connections by integer landmark indices rather than `"LANDMARK_N"` strings. 
* **Current State:** `_draw_skeleton` still constructs string keys (`start_name = f"LANDMARK_{start_idx}"`) to match against the `lm_map`, meaning even if pose estimation worked, it would fail to draw the skeleton properly.

## 3. Video Output Codec Not Browser-Playable (Phase 1, Plan 3)
* **Requirement:** Change `cv2.VideoWriter_fourcc` from `mp4v` to `avc1` (H.264) in `services/analysis.py` so the annotated output can be played in web browsers. Add an FFmpeg fallback if needed.
* **Current State:** The `render_annotated_video` function still explicitly defines `fourcc = cv2.VideoWriter_fourcc(*"mp4v")`, which results in video files that browsers cannot natively play. There is no FFmpeg fallback logic.

## 4. Highly Inefficient `VideoCapture` Lifecycle (Phase 1, Plan 4)
* **Requirement:** Open `cv2.VideoCapture` once per analysis, and seek to the requested frame to avoid the overhead of reopening the file for every frame.
* **Current State:** `backend/services/detection.py` contains `extract_frame()`, which is called by the main analysis loop. It opens the video file, seeks, reads a single frame, and closes it (`cap.release()`) on *every single frame call*. This causes massive I/O overhead.

## 5. Incomplete Large Video Upload Migration (Large Video Upload Spec & Phase 1, Plan 5)
* **Requirement:** Delete the legacy in-memory upload endpoint (`routers/upload.py`), fully migrate to the TUS protocol, sanitize filenames to prevent path traversal, and validate MIME types.
* **Current State:**
  * **Legacy Code Remaining:** `backend/routers/upload.py` still exists, and `backend/main.py` is still registering `upload.router`.
  * **Frontend Not Migrated:** `frontend/src/api/client.ts` still contains and exports `uploadVideo()`, indicating the frontend `VideoUploader.tsx` likely hasn't been migrated to `tus-js-client`.
  * **Security Missing:** In `backend/routers/tus.py`, the `Upload-Metadata` filename is blindly base64-decoded (`filename = base64.b64decode(...).decode("utf-8")`) and passed directly to the storage backend. There is no path traversal sanitization (e.g., stripping `../`) and no enforcement of video MIME types. 

---

### Action Plan / Next Steps
To get the pipeline foundational logic working end-to-end as intended:

1. **Complete CV Pipeline Improvements:**
   - Integrate MediaPipe into `services/pose.py`.
   - Fix `_draw_skeleton` indexing in `services/analysis.py`.
   - Update `cv2.VideoWriter_fourcc` to `avc1` (with FFmpeg fallback).
   - Refactor `detect_persons` and `extract_frame` to share a single `cv2.VideoCapture` lifecycle.
2. **Complete TUS Upload Migration:**
   - Finish securing `routers/tus.py` against path traversal.
   - Delete `routers/upload.py` and remove references in `main.py`.
   - Update frontend `VideoUploader.tsx` and `api/client.ts` to use `tus-js-client`.
