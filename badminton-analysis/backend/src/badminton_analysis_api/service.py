from __future__ import annotations

from base64 import b64encode
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, status

from .coach_feedback import CoachFeedbackEngine, PlaceholderCoachFeedbackEngine
from .models import (
    AnalysisActionResponse,
    AnalysisCreateInput,
    AnalysisCreateResponse,
    AnalysisListItem,
    AnalysisListResponse,
    AnalysisRecord,
    AnalysisReport,
    AnalysisSelectionInput,
    AnalysisSetupResponse,
    AnalysisStage,
    AnalysisStatusResponse,
    AnalyticsView,
    ConfidenceAnnotation,
    CourtModel,
    CourtPoint,
    HeatmapCell,
    MatchType,
    MechanicsMetrics,
    MovementMetrics,
    PlayerCandidate,
    PositioningMetrics,
    ShotSelectionEvent,
    ShotSelectionMetrics,
)
from .store import AnalysisStore

ANALYZING_PROGRESS_STEPS: list[tuple[int, str]] = [
    (34, "Normalizing the video and extracting the setup frame."),
    (62, "Tracking the selected player and scoring movement patterns."),
    (88, "Assembling the coach report and evidence-backed analytics."),
]


def _player_count(match_type: MatchType) -> int:
    return 2 if match_type in {MatchType.MENS_SINGLES, MatchType.WOMENS_SINGLES} else 4


def _build_players(match_type: MatchType) -> list[PlayerCandidate]:
    candidates: list[PlayerCandidate] = []
    for index in range(_player_count(match_type)):
        candidates.append(
            PlayerCandidate(
                player_id=f"player-{index + 1}",
                label=f"Player {index + 1}",
                side="near" if index < 2 else "far",
                focus_hint="Recommended tracking candidate"
                if index == 0
                else "Detected court player",
            )
        )
    return candidates


def _build_court() -> CourtModel:
    return CourtModel(
        confidence=0.78,
        adjustment_hint=(
            "Auto-detection looks usable, but you can drag points if the tramlines are off."
        ),
        points=[
            CourtPoint(x=0.14, y=0.12),
            CourtPoint(x=0.86, y=0.12),
            CourtPoint(x=0.92, y=0.9),
            CourtPoint(x=0.08, y=0.9),
        ],
    )


def _build_setup_frame_url(match_type: MatchType, analysis_id: str) -> str:
    match_label = match_type.value.replace("_", " ").title()
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
      <defs>
        <linearGradient id="court" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#183221"/>
          <stop offset="100%" stop-color="#2f6a44"/>
        </linearGradient>
        <linearGradient id="frame" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#f7eee4"/>
          <stop offset="100%" stop-color="#ecd4bb"/>
        </linearGradient>
      </defs>
      <rect width="1280" height="720" rx="44" fill="url(#frame)" />
      <rect x="160" y="110" width="960" height="500" rx="32" fill="url(#court)" />
      <rect
        x="220"
        y="150"
        width="840"
        height="420"
        rx="18"
        fill="none"
        stroke="#fef7ef"
        stroke-width="8"
      />
      <line x1="640" y1="150" x2="640" y2="570" stroke="#fef7ef" stroke-width="6" />
      <line x1="220" y1="360" x2="1060" y2="360" stroke="#fef7ef" stroke-width="6" />
      <text
        x="96"
        y="92"
        fill="#183221"
        font-size="38"
        font-family="Avenir Next, sans-serif"
      >{match_label}</text>
      <text
        x="96"
        y="650"
        fill="#183221"
        font-size="26"
        font-family="Avenir Next, sans-serif"
      >Analysis {analysis_id[:8]}</text>
      <circle cx="430" cy="470" r="26" fill="#f26b3a" />
      <circle cx="840" cy="278" r="26" fill="#f9d8b8" stroke="#183221" stroke-width="6" />
    </svg>
    """.strip()
    encoded = b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _decision_quality(decision_score: int) -> Literal["strong", "neutral", "poor"]:
    if decision_score >= 70:
        return "strong"
    if decision_score >= 50:
        return "neutral"
    return "poor"


def _build_shot_event(
    *,
    timestamp: str,
    shot_type: str,
    execution_score: int,
    decision_score: int,
    recommendation: str,
    evidence: str,
) -> ShotSelectionEvent:
    return ShotSelectionEvent(
        timestamp=timestamp,
        shot_type=shot_type,
        execution_score=execution_score,
        decision_score=decision_score,
        decision_quality=_decision_quality(decision_score),
        recommendation=recommendation,
        evidence=evidence,
    )


class AnalysisService:
    def __init__(
        self,
        *,
        store: AnalysisStore | None = None,
        coach_feedback_engine: CoachFeedbackEngine | None = None,
    ) -> None:
        self._store = store or AnalysisStore()
        self._coach_feedback_engine = coach_feedback_engine or PlaceholderCoachFeedbackEngine()
        self._fallback_coach_feedback_engine = PlaceholderCoachFeedbackEngine()

    def create_analysis(self, payload: AnalysisCreateInput) -> AnalysisCreateResponse:
        record = AnalysisRecord(
            youtube_url=payload.youtube_url,
            match_type=payload.match_type,
            players=_build_players(payload.match_type),
            court=_build_court(),
        )
        self._store.save(record)
        return AnalysisCreateResponse(
            analysis_id=record.analysis_id,
            youtube_url=record.youtube_url,
            match_type=record.match_type,
            selection_required=True,
            stage=record.stage,
            created_at=record.created_at,
        )

    def list_analyses(self, *, page: int = 1, page_size: int = 20) -> AnalysisListResponse:
        records = self._store.list_records()
        start = (page - 1) * page_size
        end = start + page_size
        items = [
            AnalysisListItem(
                analysis_id=record.analysis_id,
                youtube_url=record.youtube_url,
                match_type=record.match_type,
                stage=record.stage,
                created_at=record.created_at,
                owner_id=record.owner_id,
            )
            for record in records[start:end]
        ]
        return AnalysisListResponse(
            items=items,
            total=len(records),
            page=page,
            page_size=page_size,
        )

    def get_setup(self, analysis_id: str) -> AnalysisSetupResponse:
        record = self._get_record(analysis_id)
        return AnalysisSetupResponse(
            analysis_id=record.analysis_id,
            setup_frame_url=_build_setup_frame_url(record.match_type, record.analysis_id),
            players=record.players,
            court=record.court,
        )

    def apply_selection(
        self,
        analysis_id: str,
        payload: AnalysisSelectionInput,
    ) -> AnalysisActionResponse:
        record = self._get_record(analysis_id)
        if record.stage == AnalysisStage.ANALYZING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis is already running.",
            )

        self._find_player(record, payload.player_id)
        record.selected_player_id = payload.player_id
        record.court = CourtModel(
            confidence=record.court.confidence,
            adjustment_hint=record.court.adjustment_hint,
            points=payload.court_points,
        )
        record.stage = AnalysisStage.READY_TO_RUN
        record.report = None
        record.progress_step = 0
        record.warnings = []
        record.error_details = None
        self._store.save(record)
        return AnalysisActionResponse(
            analysis_id=record.analysis_id,
            stage=record.stage,
            message="Player selection saved. Analysis is ready to run.",
        )

    def run_analysis(self, analysis_id: str) -> AnalysisActionResponse:
        record = self._get_record(analysis_id)
        if record.stage != AnalysisStage.READY_TO_RUN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis setup must be saved before running.",
            )

        record.stage = AnalysisStage.ANALYZING
        record.progress_step = 0
        record.report = None
        record.warnings = []
        record.error_details = None
        self._store.save(record)
        return AnalysisActionResponse(
            analysis_id=record.analysis_id,
            stage=record.stage,
            message="Analysis started. Poll status for progress updates.",
        )

    def get_status(self, analysis_id: str) -> AnalysisStatusResponse:
        record = self._get_record(analysis_id)
        if record.stage == AnalysisStage.ANALYZING:
            return self._advance_analysis(record)
        return self._build_status_response(record)

    def get_report(self, analysis_id: str) -> AnalysisReport:
        record = self._get_record(analysis_id)
        if record.report is None or record.stage != AnalysisStage.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not ready yet.",
            )
        return record.report

    def delete_analysis(self, analysis_id: str) -> None:
        try:
            self._store.delete(analysis_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found.",
            ) from exc

    def _advance_analysis(self, record: AnalysisRecord) -> AnalysisStatusResponse:
        if record.progress_step < len(ANALYZING_PROGRESS_STEPS):
            progress_percent, message = ANALYZING_PROGRESS_STEPS[record.progress_step]
            record.progress_step += 1
            self._store.save(record)
            return AnalysisStatusResponse(
                analysis_id=record.analysis_id,
                stage=record.stage,
                progress_percent=progress_percent,
                message=message,
                warnings=record.warnings,
                error_details=record.error_details,
            )

        try:
            self._complete_analysis(record)
        except Exception as exc:
            record.stage = AnalysisStage.FAILED
            record.error_details = str(exc)
            record.progress_step = len(ANALYZING_PROGRESS_STEPS)
            self._store.save(record)
        return self._build_status_response(record)

    def _complete_analysis(self, record: AnalysisRecord) -> None:
        if record.selected_player_id is None:
            raise RuntimeError("tracked player missing")

        tracked_player = self._find_player(record, record.selected_player_id)
        analytics = self._build_analytics(record.match_type)
        confidence_annotations = self._build_confidence_annotations(analytics)
        coach_view = self._create_coach_view(
            analytics=analytics,
            match_type=record.match_type,
            tracked_player=tracked_player,
            record=record,
        )
        record.report = AnalysisReport(
            analysis_id=record.analysis_id,
            match_type=record.match_type,
            tracked_player_label=tracked_player.label,
            coach_view=coach_view,
            analytics_view=analytics,
            confidence_annotations=confidence_annotations,
            generated_at=datetime.now(UTC),
        )
        record.stage = AnalysisStage.COMPLETED
        record.progress_step = len(ANALYZING_PROGRESS_STEPS)
        self._store.save(record)

    def _create_coach_view(
        self,
        *,
        analytics: AnalyticsView,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
        record: AnalysisRecord,
    ):
        try:
            return self._coach_feedback_engine.create_feedback(
                analytics=analytics,
                match_type=match_type,
                tracked_player=tracked_player,
            )
        except Exception as exc:
            record.warnings = [
                *record.warnings,
                f"Coach feedback fallback applied after {exc}.",
            ]
            return self._fallback_coach_feedback_engine.create_feedback(
                analytics=analytics,
                match_type=match_type,
                tracked_player=tracked_player,
            )

    def _build_status_response(self, record: AnalysisRecord) -> AnalysisStatusResponse:
        progress_percent: int
        message: str

        if record.stage == AnalysisStage.SETUP_REQUIRED:
            progress_percent = 10
            message = "Waiting for player selection and court confirmation."
        elif record.stage == AnalysisStage.READY_TO_RUN:
            progress_percent = 25
            message = "Setup confirmed and ready to run."
        elif record.stage == AnalysisStage.ANALYZING:
            progress_index = max(record.progress_step - 1, 0)
            progress_percent, message = ANALYZING_PROGRESS_STEPS[progress_index]
        elif record.stage == AnalysisStage.COMPLETED:
            progress_percent = 100
            message = "Report generated successfully."
        else:
            progress_percent = 100
            message = "Analysis failed. Review the error details and return to setup."

        return AnalysisStatusResponse(
            analysis_id=record.analysis_id,
            stage=record.stage,
            progress_percent=progress_percent,
            message=message,
            warnings=record.warnings,
            error_details=record.error_details,
        )

    def _get_record(self, analysis_id: str) -> AnalysisRecord:
        try:
            return self._store.get(analysis_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found.",
            ) from exc

    def _find_player(self, record: AnalysisRecord, player_id: str) -> PlayerCandidate:
        for player in record.players:
            if player.player_id == player_id:
                return player
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected player not found.",
        )

    def _build_analytics(self, match_type: MatchType) -> AnalyticsView:
        singles = match_type in {MatchType.MENS_SINGLES, MatchType.WOMENS_SINGLES}

        if singles:
            base_position_note = (
                "Base position stays a half-step too deep after attacking shots, which slows the "
                "next interception."
            )
            spacing_note = (
                "Base position depth is playable, but the recovery step lands slightly too far "
                "behind the shuttle."
            )
            zone_occupancy = {"front": 22, "mid": 41, "rear": 37}
            heatmap = [
                HeatmapCell(zone="front-left", weight=0.11),
                HeatmapCell(zone="front-centre", weight=0.07),
                HeatmapCell(zone="front-right", weight=0.04),
                HeatmapCell(zone="mid-left", weight=0.16),
                HeatmapCell(zone="mid-centre", weight=0.25),
                HeatmapCell(zone="mid-right", weight=0.13),
                HeatmapCell(zone="rear-left", weight=0.09),
                HeatmapCell(zone="rear-centre", weight=0.08),
                HeatmapCell(zone="rear-right", weight=0.07),
            ]
            total_distance_meters = 67.8
            burst_count = 6
            directional_balance = {"left": 0.48, "right": 0.52}
        else:
            base_position_note = (
                "Recovery rotation is a beat late after forehand pressure, so the next base "
                "position arrives too central."
            )
            spacing_note = (
                "Partner spacing holds shape well, but the rear-court recovery still drifts too "
                "central under pressure."
            )
            zone_occupancy = {"front": 29, "mid": 36, "rear": 35}
            heatmap = [
                HeatmapCell(zone="front-left", weight=0.12),
                HeatmapCell(zone="front-centre", weight=0.1),
                HeatmapCell(zone="front-right", weight=0.07),
                HeatmapCell(zone="mid-left", weight=0.14),
                HeatmapCell(zone="mid-centre", weight=0.22),
                HeatmapCell(zone="mid-right", weight=0.11),
                HeatmapCell(zone="rear-left", weight=0.09),
                HeatmapCell(zone="rear-centre", weight=0.09),
                HeatmapCell(zone="rear-right", weight=0.06),
            ]
            total_distance_meters = 54.2
            burst_count = 8
            directional_balance = {"left": 0.51, "right": 0.49}

        return AnalyticsView(
            mechanics=MechanicsMetrics(
                stance_note=(
                    "Split-step timing is consistent enough to stay neutral before contact."
                ),
                preparation_note=(
                    "Racket preparation is early on forehand interceptions, later on "
                    "backhand lifts."
                ),
                balance_note=(
                    "Balance is strongest when the recovery step lands outside the base footprint."
                ),
                recovery_note=(
                    "Recovery shape degrades after deep forehand movements more than "
                    "after backhand exits."
                ),
                stroke_execution_note=(
                    "Attacking strokes hold quality until balance drops late in the rally."
                ),
            ),
            movement=MovementMetrics(
                total_distance_meters=total_distance_meters,
                recovery_score=74,
                court_coverage_percent=81,
                change_of_direction_count=28,
                burst_count=burst_count,
                directional_balance=directional_balance,
            ),
            positioning=PositioningMetrics(
                base_position_note=base_position_note,
                zone_occupancy=zone_occupancy,
                heatmap=heatmap,
                spacing_note=spacing_note,
            ),
            shot_selection=ShotSelectionMetrics(
                overview=(
                    "Shot decisions are effective when the feet arrive early, but lower-percentage "
                    "choices appear after rushed recoveries."
                ),
                events=[
                    _build_shot_event(
                        timestamp="00:12",
                        shot_type="smash",
                        execution_score=82,
                        decision_score=61,
                        recommendation=(
                            "A steep drop would likely have been higher percentage here."
                        ),
                        evidence=(
                            "The stroke shape was strong, but balance and opponent depth favored a "
                            "softer attacking option."
                        ),
                    ),
                    _build_shot_event(
                        timestamp="00:27",
                        shot_type="net",
                        execution_score=77,
                        decision_score=84,
                        recommendation=(
                            "Keep this choice; the early racket preparation created pressure."
                        ),
                        evidence=(
                            "You were balanced and arrived on time, so the attacking net shot "
                            "matched the court position."
                        ),
                    ),
                    _build_shot_event(
                        timestamp="00:41",
                        shot_type="backhand clear",
                        execution_score=58,
                        decision_score=44,
                        recommendation="",
                        evidence=(
                            "The clip shows late balance recovery and stretched contact, so "
                            "there is not enough certainty to recommend a confident alternative."
                        ),
                    ),
                ],
            ),
        )

    def _build_confidence_annotations(
        self,
        analytics: AnalyticsView,
    ) -> list[ConfidenceAnnotation]:
        return [
            ConfidenceAnnotation(
                field="analytics.movement.recovery_score",
                confidence=0.74,
                reason="Mocked movement analysis uses a limited rally sample rather than real CV.",
            ),
            ConfidenceAnnotation(
                field="analytics.shot_selection.events.2",
                confidence=0.42,
                reason=(
                    "The final shot event occurs while balance is compromised, so the best "
                    "alternative option is less certain."
                ),
            ),
            ConfidenceAnnotation(
                field="analytics.positioning.heatmap",
                confidence=0.68,
                reason=(
                    f"Zone occupancy is normalized from "
                    f"{len(analytics.positioning.heatmap)} mocked heatmap cells."
                ),
            ),
        ]
