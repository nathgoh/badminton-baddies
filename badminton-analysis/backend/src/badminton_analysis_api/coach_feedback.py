from __future__ import annotations

from typing import Protocol

from .models import AnalyticsView, CoachView, MatchType, PlayerCandidate


class CoachFeedbackEngine(Protocol):
    def create_feedback(
        self,
        *,
        analytics: AnalyticsView,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
    ) -> CoachView: ...


class PlaceholderCoachFeedbackEngine:
    """Deterministic placeholder that preserves the interface for a future typed LLM flow."""

    def create_feedback(
        self,
        *,
        analytics: AnalyticsView,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
    ) -> CoachView:
        movement = analytics.movement
        positioning = analytics.positioning
        shot_selection = analytics.shot_selection
        match_label = match_type.value.replace("_", " ")
        summary = (
            f"{tracked_player.label} shows solid base movement for {match_label} with "
            f"{movement.total_distance_meters:.1f}m covered, but the current clip suggests "
            "more disciplined recovery and shot selection would improve rally control."
        )

        return CoachView(
            summary=summary,
            strengths=[
                "Recovers into playable positions after most attacking movements.",
                "Maintains enough court coverage to keep pressure on the next ball.",
            ],
            priority_issues=[
                positioning.base_position_note,
                shot_selection.overview,
            ],
            shot_selection_notes=(
                "Decision quality drops most when the recovery step is late, so the highest-value "
                "change is arriving balanced before attacking the next shuttle."
            ),
            footwork_notes=(
                f"Recovery score is {movement.recovery_score}, with the biggest leak "
                "appearing after deep forehand movement patterns."
            ),
            positioning_notes=positioning.spacing_note,
            confidence_notes=(
                "These notes come from a mocked MVP pipeline. Treat them as structured coaching "
                "prompts rather than frame-accurate video truth."
            ),
            recommended_drills=[
                "Four-corner recovery with split-step resets.",
                "Shadow rotation sequence focused on staying balanced before the next stroke.",
                "Decision-making feeds alternating high clear, steep drop, and hold-and-push cues.",
            ],
        )
