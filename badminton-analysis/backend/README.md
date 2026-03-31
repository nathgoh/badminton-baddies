# Backend

FastAPI service for the badminton analysis MVP.

## Commands

```bash
uv sync --group dev
uv run uvicorn badminton_analysis_api.api.app:app --reload --port 8000
uv run pytest
uv run ruff check .
uv run ty check src
```

## Optional AI Path

- Leave `COACH_FEEDBACK_ENGINE` unset to use the deterministic placeholder coach engine.
- Set `COACH_FEEDBACK_ENGINE=llm` to use the provider-configurable AI adapter.
- Set `LLM_PROVIDER=gemini` and `LLM_MODEL=gemini-3-flash-preview` for the default Gemini path.
- Set `LLM_MODEL=gemini-3-pro-preview` to trade latency and cost for stronger synthesis.
- Set `GEMINI_API_KEY` for Gemini requests.
- Set `LLM_PROVIDER=openai` or `LLM_PROVIDER=anthropic` to route through the generic typed adapter.
- Set `LLM_MODEL` to the provider model name, for example `gpt-5.2` or `claude-sonnet-4`.
- Set the corresponding provider API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and so on).
- `COACH_FEEDBACK_ENGINE=pydanticai` remains available for older model-string configs such as
  `PYDANTIC_AI_MODEL=openai:gpt-5.2`.
- The service falls back to `PlaceholderCoachFeedbackEngine` and emits a warning if the AI path
  raises during report generation.

## Media Pipeline

- `MEDIA_PIPELINE=mock` is the default and creates placeholder setup artifacts under `/tmp`.
- `MEDIA_PIPELINE=shell` enables real YouTube ingestion and setup-frame extraction.
- `MEDIA_PIPELINE=none` skips artifact preparation and falls back to the inline placeholder frame.
- `MEDIA_ARTIFACT_ROOT` overrides the artifact directory.
- `shell` mode requires `yt-dlp` and `ffmpeg` to be installed on the host.

## CV Pipeline

- `CV_PIPELINE=mock` is the default and keeps deterministic setup detection, tracking, and pose
  outputs for local development and tests.
- `CV_PIPELINE=hybrid` enables the first real CV foundation slice:
  setup-frame court detection with OpenCV, person detection and sampled tracking with YOLO, and
  selected-player pose extraction with MediaPipe Pose.
- `CV_PIPELINE=none` disables CV augmentation and falls back to the older placeholder analysis
  behavior.
- `YOLO_MODEL` overrides the YOLO weights path or model name. The default is `yolov8n.pt`.
- `TRACKING_SAMPLE_FPS` controls how densely the video is sampled during tracking. The default is
  `2.0`.
- `hybrid` mode requires `opencv-python-headless`, `ultralytics`, and `mediapipe` to be available
  in the Python environment.

## Owner Context

- Pass `X-Owner-Id` on requests to create owner-scoped analyses and hide other owners' records.
