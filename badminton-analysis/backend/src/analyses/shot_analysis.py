"""Gemini-based visual shot analysis from key video frames."""

from __future__ import annotations

import logging
from importlib import import_module
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models import Model

from schemas import (
    MatchType,
    PlayerTrackSummary,
    ShotSelectionEvent,
    ShotSelectionMetrics,
    TrackSample,
)

logger = logging.getLogger(__name__)

_MAX_KEY_FRAMES = 10
_BURST_THRESHOLD = 0.08  # Same as CV pipeline's burst detection


class VisualShotEvent(BaseModel):
    """A single shot observed from a video frame."""

    timestamp_seconds: float = Field(description="Approximate time in the video (seconds)")
    shot_type: str = Field(
        description=(
            "Badminton shot type, e.g. smash, drop shot, clear, net shot, drive, lift, "
            "net kill, cross-court net, backhand clear, defensive clear"
        )
    )
    execution_score: int = Field(
        ge=0,
        le=100,
        description="How well the shot was executed technically (0-100)",
    )
    decision_score: int = Field(
        ge=0,
        le=100,
        description="How good the shot choice was tactically given the situation (0-100)",
    )
    recommendation: str = Field(
        description=(
            "Brief coaching recommendation. Leave empty if confidence is low."
        )
    )
    evidence: str = Field(
        description="What visual evidence supports this assessment",
    )


class VisualShotAnalysisOutput(BaseModel):
    """Structured output from Gemini visual shot analysis."""

    overview: str = Field(
        description=(
            "1-2 sentence summary of the player's shot selection patterns "
            "based on the observed frames"
        )
    )
    events: list[VisualShotEvent] = Field(
        description="Shot events identified from the key frames, in chronological order"
    )


_SYSTEM_PROMPT = """\
You are an expert badminton analyst reviewing key frames from a match video.

For each frame showing a shot being played, identify:
- The shot type (smash, drop, clear, net shot, drive, lift, net kill, etc.)
- Execution quality (0-100): body position, racket preparation, contact point, follow-through
- Decision quality (0-100): was this the right shot given court position and opponent placement?
- A brief coaching recommendation (leave empty if you're unsure)
- Visual evidence supporting your assessment

Focus on frames where a stroke is clearly being executed. Skip frames that show \
movement between shots or unclear action. It's better to report fewer high-confidence \
events than many uncertain ones.

If a frame is ambiguous or you cannot identify a clear shot, skip it entirely.
"""


def _decision_quality(score: int) -> str:
    if score >= 70:
        return "strong"
    if score >= 50:
        return "neutral"
    return "poor"


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _select_key_frame_indices(
    samples: list[TrackSample],
    max_frames: int = _MAX_KEY_FRAMES,
) -> list[int]:
    """Pick frame indices at burst moments (likely shot contact points).

    Falls back to evenly-spaced samples if not enough bursts are found.
    """
    burst_indices: list[int] = []
    for prev, curr in zip(samples, samples[1:], strict=False):
        dx = curr.x - prev.x
        dy = curr.y - prev.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist > _BURST_THRESHOLD:
            burst_indices.append(curr.frame_index)

    if len(burst_indices) >= 3:
        # Take evenly-spaced bursts up to max_frames
        if len(burst_indices) > max_frames:
            step = len(burst_indices) / max_frames
            burst_indices = [burst_indices[int(i * step)] for i in range(max_frames)]
        return burst_indices

    # Not enough bursts — fall back to evenly-spaced samples
    if len(samples) <= max_frames:
        return [s.frame_index for s in samples]
    step = len(samples) / max_frames
    return [samples[int(i * step)].frame_index for i in range(max_frames)]


def _extract_frames_from_video(
    video_path: str,
    frame_indices: list[int],
) -> list[tuple[int, float, bytes]]:
    """Read specific frames from video and return as (frame_index, timestamp, jpeg_bytes)."""
    cv2: Any = import_module("cv2")
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video at {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    frames: list[tuple[int, float, bytes]] = []

    for frame_index in sorted(frame_indices):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            continue
        # Resize to reduce token cost — 640px wide is enough for Gemini
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            frame = cv2.resize(frame, (640, int(height * scale)))
        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frames.append((frame_index, frame_index / fps, jpeg.tobytes()))

    capture.release()
    return frames


def analyze_shots_from_frames(
    *,
    video_path: str,
    tracking_summary: PlayerTrackSummary,
    match_type: MatchType,
    video_duration_seconds: float | None = None,
    model_override: Model | None = None,
) -> ShotSelectionMetrics:
    """Send key video frames to Gemini for shot type recognition.

    Returns a ShotSelectionMetrics with real observations instead of templates.
    """
    duration = video_duration_seconds or 120.0

    # 1. Select key frames from burst moments
    key_frame_indices = _select_key_frame_indices(tracking_summary.samples)
    if not key_frame_indices:
        logger.warning("No key frames selected for shot analysis")
        return _empty_shot_selection()

    # 2. Extract frames from video
    frames = _extract_frames_from_video(video_path, key_frame_indices)
    if not frames:
        logger.warning("Could not extract any frames for shot analysis")
        return _empty_shot_selection()

    # 3. Build multimodal prompt
    match_label = match_type.value.replace("_", " ")
    user_prompt = (
        f"Analyze these {len(frames)} key frames from a {match_label} badminton match. "
        f"The video is {duration:.0f} seconds long. "
        f"Each frame is labeled with its timestamp. "
        f"Identify shot events where a stroke is being played."
    )

    content: list[str | BinaryContent] = [user_prompt]
    for _frame_index, timestamp, jpeg_bytes in frames:
        content.append(f"\n--- Frame at {_format_timestamp(timestamp)} ({timestamp:.1f}s) ---")
        content.append(BinaryContent(data=jpeg_bytes, media_type="image/jpeg"))

    # 4. Call Gemini
    model = model_override or "google-gla:gemini-3.1-flash-lite-preview"
    agent: Agent[None, VisualShotAnalysisOutput] = Agent(
        model,
        output_type=VisualShotAnalysisOutput,
        system_prompt=_SYSTEM_PROMPT,
    )
    result = agent.run_sync(content)
    output = result.output

    # 5. Convert to ShotSelectionMetrics
    events: list[ShotSelectionEvent] = []
    for shot in output.events:
        event_seconds = int(shot.timestamp_seconds)
        events.append(
            ShotSelectionEvent(
                timestamp=_format_timestamp(shot.timestamp_seconds),
                shot_type=shot.shot_type,
                execution_score=shot.execution_score,
                decision_score=shot.decision_score,
                decision_quality=_decision_quality(shot.decision_score),
                recommendation=shot.recommendation,
                evidence=shot.evidence,
                clip_start_seconds=max(0, event_seconds - 3),
                clip_end_seconds=min(int(duration), event_seconds + 3),
            )
        )

    # Sort by timestamp
    events.sort(key=lambda e: e.clip_start_seconds)

    return ShotSelectionMetrics(
        overview=output.overview or (
            "Shot selection analysis based on visual review of key match frames."
        ),
        events=events,
    )


def _empty_shot_selection() -> ShotSelectionMetrics:
    return ShotSelectionMetrics(
        overview="No shot events could be identified from the available frames.",
        events=[],
    )
