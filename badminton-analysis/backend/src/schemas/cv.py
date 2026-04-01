from __future__ import annotations

from pydantic import BaseModel, Field

from .report import HeatmapCell, ShuttleSample
from .shared import CourtModel, DetectionBox, PlayerCandidate


class SetupDetectionResult(BaseModel):
    players: list[PlayerCandidate]
    court: CourtModel
    warnings: list[str] = Field(default_factory=list)


class TrackSample(BaseModel):
    frame_index: int
    timestamp_seconds: float
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    bounding_box: DetectionBox | None = None


class PlayerTrackSummary(BaseModel):
    track_id: str
    source_player_id: str | None = None
    total_distance_meters: float
    recovery_score: int
    court_coverage_percent: int
    change_of_direction_count: int
    burst_count: int
    directional_balance: dict[str, float]
    zone_occupancy: dict[str, int]
    heatmap: list[HeatmapCell]
    samples: list[TrackSample] = Field(default_factory=list)


class TrackingResult(BaseModel):
    tracks: list[PlayerTrackSummary]
    focused_track_id: str | None = None
    observed_shuttle_samples: list[ShuttleSample] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PoseLandmarkPoint(BaseModel):
    x: float
    y: float
    z: float = 0.0
    visibility: float | None = None


class PoseFrame(BaseModel):
    frame_index: int
    timestamp_seconds: float
    landmarks: list[PoseLandmarkPoint] = Field(default_factory=list)


class PoseMechanicsMetrics(BaseModel):
    stance_width_ratio: float | None = None
    knee_flexion_degrees: float | None = None
    trunk_lean_degrees: float | None = None
    balance_offset_ratio: float | None = None
    preparation_rate: float | None = None


class PoseSummary(BaseModel):
    sample_count: int
    warnings: list[str] = Field(default_factory=list)
    stance_note: str
    preparation_note: str
    balance_note: str
    recovery_note: str
    stroke_execution_note: str
    pose_frames: list[PoseFrame] = Field(default_factory=list)
    mechanics: PoseMechanicsMetrics = Field(default_factory=PoseMechanicsMetrics)
