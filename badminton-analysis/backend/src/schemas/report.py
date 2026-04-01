from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .coaching import AIRationale, CoachView
from .shared import MatchType


class MechanicsMetrics(BaseModel):
    stance_note: str
    preparation_note: str
    balance_note: str
    recovery_note: str
    stroke_execution_note: str


class MovementMetrics(BaseModel):
    total_distance_meters: float
    recovery_score: int
    court_coverage_percent: int
    change_of_direction_count: int
    burst_count: int
    directional_balance: dict[str, float]


class HeatmapCell(BaseModel):
    zone: str
    weight: float = Field(ge=0.0, le=1.0)


class PositioningMetrics(BaseModel):
    base_position_note: str
    zone_occupancy: dict[str, int]
    heatmap: list[HeatmapCell]
    spacing_note: str


class ShotSelectionEvent(BaseModel):
    timestamp: str
    shot_type: str
    execution_score: int
    decision_score: int
    decision_quality: Literal["strong", "neutral", "poor"]
    recommendation: str
    evidence: str
    clip_start_seconds: int
    clip_end_seconds: int
    rendered_clip_url: str | None = None
    rendered_clip_media_type: str | None = None


class ShotSelectionMetrics(BaseModel):
    overview: str
    events: list[ShotSelectionEvent]


class ShuttleSample(BaseModel):
    timestamp_seconds: float
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["inferred", "observed"] = "inferred"


class PressureWindow(BaseModel):
    label: str
    start_timestamp: str
    end_timestamp: str
    summary: str
    clip_start_seconds: int | None = None
    clip_end_seconds: int | None = None
    rendered_clip_url: str | None = None
    rendered_clip_media_type: str | None = None


class ShuttleMetrics(BaseModel):
    summary: str
    uncertainty_note: str
    samples: list[ShuttleSample]
    pressure_windows: list[PressureWindow]
    heatmap: list[HeatmapCell]


class AnalyticsView(BaseModel):
    mechanics: MechanicsMetrics
    movement: MovementMetrics
    positioning: PositioningMetrics
    shot_selection: ShotSelectionMetrics
    shuttle: ShuttleMetrics


class ConfidenceAnnotation(BaseModel):
    field: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class AnalysisEvidence(BaseModel):
    shuttle: ShuttleMetrics
    movement_summary: str
    mechanics_summary: str
    shot_selection_summary: str


class AnalysisReport(BaseModel):
    analysis_id: str
    match_type: MatchType
    tracked_player_label: str
    coach_view: CoachView
    analytics_view: AnalyticsView
    confidence_annotations: list[ConfidenceAnnotation]
    llm_provider: str | None = None
    llm_model: str | None = None
    generation_mode: Literal["ai", "fallback"]
    analysis_evidence: AnalysisEvidence
    ai_rationale: AIRationale | None = None
    generated_at: datetime
