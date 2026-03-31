from __future__ import annotations

from base64 import b64encode
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, status

from .coach_feedback import CoachFeedbackEngine, PlaceholderCoachFeedbackEngine
from .cv import CVPipeline, _default_court, _default_players, _player_count
from .media import MediaArtifactPipeline, MediaPreparationError
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
    HeatmapCell,
    MatchType,
    MechanicsMetrics,
    MovementMetrics,
    PlayerCandidate,
    PlayerTrackSummary,
    PoseSummary,
    PositioningMetrics,
    SetupDetectionResult,
    ShotSelectionEvent,
    ShotSelectionMetrics,
    TrackingResult,
)
from .store import AnalysisStore

ANALYZING_PROGRESS_STEPS: list[tuple[int, str]] = [
    (12, "Ingesting the YouTube match and normalizing the video."),
    (24, "Extracting the setup frame from the opening rally window."),
    (36, "Detecting court geometry and applying any saved manual overrides."),
    (48, "Detecting players and building multi-person tracks."),
    (58, "Assigning the selected player to the tracked movement sequence."),
    (69, "Extracting pose landmarks and movement signals."),
    (80, "Inferring shot events from the tracked rally sequence."),
    (91, "Scoring tactical shot quality and decision outcomes."),
    (98, "Assembling the coach report and analytics evidence."),
]



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
        media_artifact_pipeline: MediaArtifactPipeline | None = None,
        cv_pipeline: CVPipeline | None = None,
    ) -> None:
        self._store = store or AnalysisStore()
        self._coach_feedback_engine = coach_feedback_engine or PlaceholderCoachFeedbackEngine()
        self._fallback_coach_feedback_engine = PlaceholderCoachFeedbackEngine()
        self._media_artifact_pipeline = media_artifact_pipeline
        self._cv_pipeline = cv_pipeline

    def create_analysis(
        self,
        payload: AnalysisCreateInput,
        *,
        owner_id: str | None = None,
    ) -> AnalysisCreateResponse:
        record = AnalysisRecord(
            youtube_url=payload.youtube_url,
            match_type=payload.match_type,
            owner_id=owner_id,
            players=_default_players(payload.match_type),
            court=_default_court(),
        )
        self._prepare_media(record)
        self._apply_setup_detection(record)
        self._store.save(record)
        return AnalysisCreateResponse(
            analysis_id=record.analysis_id,
            youtube_url=record.youtube_url,
            match_type=record.match_type,
            selection_required=True,
            stage=record.stage,
            created_at=record.created_at,
        )

    def list_analyses(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        owner_id: str | None = None,
    ) -> AnalysisListResponse:
        records = self._visible_records(owner_id)
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

    def get_setup(self, analysis_id: str, *, owner_id: str | None = None) -> AnalysisSetupResponse:
        record = self._get_record(analysis_id, owner_id=owner_id)
        setup_frame_url = _build_setup_frame_url(record.match_type, record.analysis_id)
        if record.setup_frame_path is not None:
            setup_frame_url = f"/api/analyses/{record.analysis_id}/setup-frame"
        return AnalysisSetupResponse(
            analysis_id=record.analysis_id,
            setup_frame_url=setup_frame_url,
            players=record.players,
            court=record.court,
        )

    def apply_selection(
        self,
        analysis_id: str,
        payload: AnalysisSelectionInput,
        *,
        owner_id: str | None = None,
    ) -> AnalysisActionResponse:
        record = self._get_record(analysis_id, owner_id=owner_id)
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
        record.selected_track_id = None
        record.tracking_result = None
        record.pose_summary = None
        self._store.save(record)
        return AnalysisActionResponse(
            analysis_id=record.analysis_id,
            stage=record.stage,
            message="Player selection saved. Analysis is ready to run.",
        )

    def run_analysis(
        self,
        analysis_id: str,
        *,
        owner_id: str | None = None,
    ) -> AnalysisActionResponse:
        record = self._get_record(analysis_id, owner_id=owner_id)
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

    def get_status(
        self,
        analysis_id: str,
        *,
        owner_id: str | None = None,
    ) -> AnalysisStatusResponse:
        record = self._get_record(analysis_id, owner_id=owner_id)
        if record.stage == AnalysisStage.ANALYZING:
            return self._advance_analysis(record)
        return self._build_status_response(record)

    def get_report(self, analysis_id: str, *, owner_id: str | None = None) -> AnalysisReport:
        record = self._get_record(analysis_id, owner_id=owner_id)
        if record.report is None or record.stage != AnalysisStage.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not ready yet.",
            )
        return record.report

    def get_setup_frame_file(
        self,
        analysis_id: str,
        *,
        owner_id: str | None = None,
    ) -> tuple[Path, str]:
        record = self._get_record(analysis_id, owner_id=owner_id)
        if record.setup_frame_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Setup frame not available.",
            )

        path = Path(record.setup_frame_path)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Setup frame not available.",
            )
        return path, record.setup_frame_content_type or "application/octet-stream"

    def delete_analysis(self, analysis_id: str, *, owner_id: str | None = None) -> None:
        record = self._get_record(analysis_id, owner_id=owner_id)
        self._cleanup_media(record)
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
        tracking_summary: PlayerTrackSummary | None = None
        pose_summary: PoseSummary | None = None

        if self._cv_pipeline is not None and record.source_video_path is not None:
            tracking_result = self._run_tracking(record)
            record.tracking_result = tracking_result
            record.warnings = [*record.warnings, *tracking_result.warnings]

            tracking_summary = self._select_track_for_player(record, tracking_result)
            if tracking_summary is None:
                raise RuntimeError("Unable to map the selected player to a tracked sequence.")

            record.selected_track_id = tracking_summary.track_id
            pose_summary = self._extract_pose_summary(record, tracking_summary)
            record.pose_summary = pose_summary
            record.warnings = [*record.warnings, *pose_summary.warnings]

        analytics = self._build_analytics(record.match_type)
        analytics = self._apply_cv_analytics(
            analytics,
            tracking_summary=tracking_summary,
            pose_summary=pose_summary,
        )
        confidence_annotations = self._build_confidence_annotations(
            analytics,
            tracking_summary=tracking_summary,
            pose_summary=pose_summary,
        )
        coach_view = self._create_coach_view(
            analytics=analytics,
            confidence_annotations=confidence_annotations,
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
        confidence_annotations: list[ConfidenceAnnotation],
        match_type: MatchType,
        tracked_player: PlayerCandidate,
        record: AnalysisRecord,
    ):
        try:
            return self._coach_feedback_engine.create_feedback(
                analytics=analytics,
                confidence_annotations=confidence_annotations,
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
                confidence_annotations=confidence_annotations,
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

    def _get_record(self, analysis_id: str, *, owner_id: str | None = None) -> AnalysisRecord:
        try:
            record = self._store.get(analysis_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found.",
            ) from exc
        if record.owner_id is not None and record.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found.",
            )
        return record

    def _visible_records(self, owner_id: str | None) -> list[AnalysisRecord]:
        records = self._store.list_records()
        if owner_id is None:
            return records
        return [record for record in records if record.owner_id == owner_id]

    def _prepare_media(self, record: AnalysisRecord) -> None:
        if self._media_artifact_pipeline is None:
            return

        try:
            artifacts = self._media_artifact_pipeline.prepare_analysis(
                record.analysis_id,
                str(record.youtube_url),
            )
        except MediaPreparationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to prepare media for analysis: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to prepare media for analysis: {exc}",
            ) from exc

        record.source_video_path = artifacts.source_video_path
        record.setup_frame_path = artifacts.setup_frame_path
        record.setup_frame_content_type = artifacts.setup_frame_content_type

    def _apply_setup_detection(self, record: AnalysisRecord) -> None:
        if self._cv_pipeline is None or record.setup_frame_path is None:
            return

        try:
            raw_result = self._cv_pipeline.detect_setup(record.setup_frame_path, record.match_type)
            result = SetupDetectionResult.model_validate(raw_result, from_attributes=True)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to detect setup from media: {exc}",
            ) from exc

        detected_players = result.players[: _player_count(record.match_type)]
        if len(detected_players) < _player_count(record.match_type):
            existing_player_ids = {player.player_id for player in detected_players}
            for fallback_player in _default_players(record.match_type):
                if fallback_player.player_id in existing_player_ids:
                    continue
                detected_players.append(fallback_player)
                if len(detected_players) >= _player_count(record.match_type):
                    break
        if detected_players:
            record.players = detected_players
        record.court = result.court
        record.warnings = [*record.warnings, *result.warnings]

    def _cleanup_media(self, record: AnalysisRecord) -> None:
        if self._media_artifact_pipeline is None:
            return

        cleanup = getattr(self._media_artifact_pipeline, "cleanup_analysis", None)
        if callable(cleanup):
            cleanup(record.analysis_id)

    def _find_player(self, record: AnalysisRecord, player_id: str) -> PlayerCandidate:
        for player in record.players:
            if player.player_id == player_id:
                return player
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected player not found.",
        )

    def _run_tracking(self, record: AnalysisRecord) -> TrackingResult:
        if self._cv_pipeline is None or record.source_video_path is None:
            return TrackingResult(tracks=[], warnings=[])

        raw_result = self._cv_pipeline.track_players(
            record.source_video_path,
            record.court,
            record.match_type,
        )
        raw_tracks = getattr(raw_result, "tracks", [])
        if isinstance(raw_tracks, dict):
            raw_tracks = list(raw_tracks.values())
        warnings = list(getattr(raw_result, "warnings", []))
        tracks = [
            PlayerTrackSummary.model_validate(track, from_attributes=True) for track in raw_tracks
        ]
        return TrackingResult(tracks=tracks, warnings=warnings)

    def _select_track_for_player(
        self,
        record: AnalysisRecord,
        tracking_result: TrackingResult,
    ) -> PlayerTrackSummary | None:
        for track in tracking_result.tracks:
            if track.source_player_id == record.selected_player_id:
                return track
            if track.track_id == record.selected_player_id:
                return track

        if record.selected_track_id is not None:
            for track in tracking_result.tracks:
                if track.track_id == record.selected_track_id:
                    return track

        if len(tracking_result.tracks) == 1:
            return tracking_result.tracks[0]

        return None

    def _extract_pose_summary(
        self,
        record: AnalysisRecord,
        selected_track: PlayerTrackSummary,
    ) -> PoseSummary:
        if self._cv_pipeline is None or record.source_video_path is None:
            return PoseSummary(
                sample_count=0,
                warnings=[],
                stance_note="Pose samples were unavailable for the selected player.",
                preparation_note="Pose samples were unavailable for the selected player.",
                balance_note="Pose samples were unavailable for the selected player.",
                recovery_note="Pose samples were unavailable for the selected player.",
                stroke_execution_note="Pose samples were unavailable for the selected player.",
            )

        raw_summary = self._cv_pipeline.extract_pose(record.source_video_path, selected_track)
        return PoseSummary.model_validate(raw_summary, from_attributes=True)

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

    def _apply_cv_analytics(
        self,
        analytics: AnalyticsView,
        *,
        tracking_summary: PlayerTrackSummary | None,
        pose_summary: PoseSummary | None,
    ) -> AnalyticsView:
        mechanics = analytics.mechanics
        movement = analytics.movement
        positioning = analytics.positioning

        if pose_summary is not None:
            mechanics = MechanicsMetrics(
                stance_note=pose_summary.stance_note,
                preparation_note=pose_summary.preparation_note,
                balance_note=pose_summary.balance_note,
                recovery_note=pose_summary.recovery_note,
                stroke_execution_note=pose_summary.stroke_execution_note,
            )

        if tracking_summary is not None:
            movement = MovementMetrics(
                total_distance_meters=tracking_summary.total_distance_meters,
                recovery_score=tracking_summary.recovery_score,
                court_coverage_percent=tracking_summary.court_coverage_percent,
                change_of_direction_count=tracking_summary.change_of_direction_count,
                burst_count=tracking_summary.burst_count,
                directional_balance=tracking_summary.directional_balance,
            )
            positioning = PositioningMetrics(
                base_position_note=positioning.base_position_note,
                zone_occupancy=tracking_summary.zone_occupancy,
                heatmap=tracking_summary.heatmap,
                spacing_note=positioning.spacing_note,
            )

        return AnalyticsView(
            mechanics=mechanics,
            movement=movement,
            positioning=positioning,
            shot_selection=analytics.shot_selection,
        )

    def _build_confidence_annotations(
        self,
        analytics: AnalyticsView,
        *,
        tracking_summary: PlayerTrackSummary | None = None,
        pose_summary: PoseSummary | None = None,
    ) -> list[ConfidenceAnnotation]:
        movement_reason = (
            "Mocked movement analysis uses a limited rally sample rather than real CV."
        )
        movement_confidence = 0.74
        if tracking_summary is not None:
            movement_reason = (
                "Movement metrics were derived from sampled player tracks rather than full rally "
                "coverage."
            )
            movement_confidence = 0.81

        heatmap_reason = (
            f"Zone occupancy is normalized from {len(analytics.positioning.heatmap)} mocked "
            "heatmap cells."
        )
        heatmap_confidence = 0.68
        if tracking_summary is not None:
            heatmap_reason = (
                f"Zone occupancy is normalized from {len(analytics.positioning.heatmap)} "
                "tracked heatmap cells."
            )
            heatmap_confidence = 0.76

        stance_confidence = (
            0.72 if pose_summary is not None and pose_summary.sample_count > 0 else 0.58
        )
        return [
            ConfidenceAnnotation(
                field="analytics.movement.recovery_score",
                confidence=movement_confidence,
                reason=movement_reason,
            ),
            ConfidenceAnnotation(
                field="analytics.mechanics.stance_note",
                confidence=stance_confidence,
                reason=(
                    "Mechanics notes are derived from selected-player pose sampling and still rely "
                    "on heuristic interpretation."
                    if pose_summary is not None and pose_summary.sample_count > 0
                    else "Mechanics notes are still driven by placeholder heuristics."
                ),
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
                confidence=heatmap_confidence,
                reason=heatmap_reason,
            ),
        ]
