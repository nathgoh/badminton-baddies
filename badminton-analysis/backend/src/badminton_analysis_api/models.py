from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class MatchType(StrEnum):
    MENS_SINGLES = "mens_singles"
    WOMENS_SINGLES = "womens_singles"
    MENS_DOUBLES = "mens_doubles"
    WOMENS_DOUBLES = "womens_doubles"
    MIXED_DOUBLES = "mixed_doubles"


class AnalysisStage(StrEnum):
    SETUP_REQUIRED = "setup_required"
    READY_TO_RUN = "ready_to_run"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class CourtPoint(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class CourtModel(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    points: list[CourtPoint]
    adjustment_hint: str


class PlayerCandidate(BaseModel):
    player_id: str
    label: str
    side: Literal["near", "far"]
    focus_hint: str


class AnalysisCreateInput(BaseModel):
    youtube_url: HttpUrl
    match_type: MatchType


class AnalysisCreateResponse(BaseModel):
    analysis_id: str
    youtube_url: HttpUrl
    match_type: MatchType
    selection_required: bool
    stage: AnalysisStage
    created_at: datetime


class AnalysisListItem(BaseModel):
    analysis_id: str
    youtube_url: HttpUrl
    match_type: MatchType
    stage: AnalysisStage
    created_at: datetime
    owner_id: str | None = None


class AnalysisListResponse(BaseModel):
    items: list[AnalysisListItem]
    total: int
    page: int
    page_size: int


class AnalysisSetupResponse(BaseModel):
    analysis_id: str
    setup_frame_url: str
    players: list[PlayerCandidate]
    court: CourtModel


class AnalysisSelectionInput(BaseModel):
    player_id: str
    court_points: list[CourtPoint]


class AnalysisActionResponse(BaseModel):
    analysis_id: str
    stage: AnalysisStage
    message: str


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    stage: AnalysisStage
    progress_percent: int = Field(ge=0, le=100)
    message: str
    warnings: list[str]
    error_details: str | None = None


class CoachView(BaseModel):
    summary: str
    strengths: list[str]
    priority_issues: list[str]
    shot_selection_notes: str
    footwork_notes: str
    positioning_notes: str
    confidence_notes: str
    recommended_drills: list[str]


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


class ShotSelectionMetrics(BaseModel):
    overview: str
    events: list[ShotSelectionEvent]


class AnalyticsView(BaseModel):
    mechanics: MechanicsMetrics
    movement: MovementMetrics
    positioning: PositioningMetrics
    shot_selection: ShotSelectionMetrics


class ConfidenceAnnotation(BaseModel):
    field: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class AnalysisReport(BaseModel):
    analysis_id: str
    match_type: MatchType
    tracked_player_label: str
    coach_view: CoachView
    analytics_view: AnalyticsView
    confidence_annotations: list[ConfidenceAnnotation]
    generated_at: datetime


class AnalysisRecord(BaseModel):
    analysis_id: str = Field(default_factory=lambda: uuid4().hex)
    youtube_url: HttpUrl
    match_type: MatchType
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    owner_id: str | None = None
    selected_player_id: str | None = None
    players: list[PlayerCandidate]
    court: CourtModel
    stage: AnalysisStage = AnalysisStage.SETUP_REQUIRED
    warnings: list[str] = Field(default_factory=list)
    error_details: str | None = None
    progress_step: int = 0
    report: AnalysisReport | None = None
