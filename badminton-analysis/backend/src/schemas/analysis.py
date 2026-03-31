from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl

from .cv import PoseSummary, TrackingResult
from .report import AnalysisReport
from .shared import CourtModel, CourtPoint, MatchType, PlayerCandidate


class AnalysisStage(StrEnum):
    SETUP_REQUIRED = "setup_required"
    READY_TO_RUN = "ready_to_run"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    pipeline_stage: str | None = None
    frame_index: int | None = None
    total_frames: int | None = None


class FrameEvent(BaseModel):
    """A single frame update streamed during analysis."""
    analysis_id: str
    pipeline_stage: str  # "tracking" | "pose" | "analytics" | "coaching"
    frame_index: int
    total_frames: int
    progress_percent: int = Field(ge=0, le=100)
    message: str
    frame_jpeg_base64: str | None = None


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
    progress_percent: int = 0
    status_message: str | None = None
    pipeline_stage: str | None = None
    frame_index: int | None = None
    total_frames: int | None = None
    source_video_path: str | None = None
    video_duration_seconds: float | None = None
    setup_frame_path: str | None = None
    setup_frame_content_type: str | None = None
    selected_track_id: str | None = None
    tracking_result: TrackingResult | None = None
    pose_summary: PoseSummary | None = None
    report: AnalysisReport | None = None
