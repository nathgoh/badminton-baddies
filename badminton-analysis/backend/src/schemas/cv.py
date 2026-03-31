from __future__ import annotations

from pydantic import BaseModel, Field

from .report import HeatmapCell
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
    warnings: list[str] = Field(default_factory=list)


class PoseSummary(BaseModel):
    sample_count: int
    warnings: list[str] = Field(default_factory=list)
    stance_note: str
    preparation_note: str
    balance_note: str
    recovery_note: str
    stroke_execution_note: str
