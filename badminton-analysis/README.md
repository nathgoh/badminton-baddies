# Badminton Analysis

Mobile-friendly web app for badminton video analysis from public YouTube links.

## Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, uv, ruff, ty
- AI placeholder: typed coach feedback boundary designed for a single-prompt workflow

## MVP Flow

1. Paste a public YouTube URL.
2. Select the match type.
3. Review the setup frame, choose the player to track, and adjust court lines if needed.
4. Run the analysis.
5. Review the coach-first report and supporting analytics tab.

## Backend Options

- `COACH_FEEDBACK_ENGINE=pydanticai` switches the coach layer from the deterministic placeholder
  to `PydanticAICoachFeedbackEngine`.
- `PYDANTIC_AI_MODEL` sets the PydanticAI model string. The default is `openai:gpt-5.2`.
- `MEDIA_PIPELINE=mock|shell|none` controls setup-media preparation.
- `MEDIA_ARTIFACT_ROOT` overrides where downloaded videos and extracted setup frames are stored.
- `CV_PIPELINE=mock|hybrid|none` controls whether setup detection, player tracking, and
  selected-player pose extraction use placeholder outputs or the OpenCV + YOLO + MediaPipe path.
- `YOLO_MODEL` overrides the YOLO weights used by the hybrid CV pipeline. The default is
  `yolov8n.pt`.
- `TRACKING_SAMPLE_FPS` sets the sampled frame rate for tracking. The default is `2.0`.
- `X-Owner-Id` scopes records to an owner-aware view of the API while keeping anonymous MVP usage
  working for existing clients.

### Media pipeline modes

- `mock` is the default. It creates local placeholder media artifacts and serves setup frames
  through the backend file route.
- `shell` uses `yt-dlp` plus `ffmpeg` to download the public YouTube source and extract a real
  setup frame from the opening seconds of the clip.
- `none` disables artifact preparation and falls back to the older inline placeholder frame.

### CV pipeline modes

- `mock` is the default. It returns deterministic court, player, tracking, and pose outputs so the
  MVP flow stays runnable in development and tests.
- `hybrid` uses OpenCV for court geometry and video sampling, YOLO for person detection and
  tracking, and MediaPipe Pose for selected-player landmarks.
- `none` disables CV augmentation and leaves the older placeholder setup and analysis behavior in
  place.

## Workspace

```text
badminton-analysis/
├── backend/
├── docs/
└── frontend/
```
