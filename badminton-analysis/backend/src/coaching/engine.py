from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model

from analyses.evidence import build_default_ai_rationale
from schemas import (
    AIRationale,
    AnalysisEvidence,
    AnalyticsView,
    CoachFeedbackResult,
    CoachView,
    ConfidenceAnnotation,
    MatchType,
    PlayerCandidate,
)

DEFAULT_INSTRUCTIONS = (
    "You are an elite badminton coach. Produce concise, evidence-backed coaching feedback. "
    "Only describe observations supported by the analytics, structured evidence, and confidence "
    "annotations. When evidence is inferred, say so rather than pretending it is frame-accurate."
)

# PydanticAI model string prefix for Gemini via google-gla provider.
_GEMINI_PREFIX = "google-gla"


class LLMCoachOutput(BaseModel):
    coach_view: CoachView
    ai_rationale: AIRationale | None = None


class CoachFeedbackEngine(Protocol):
    def create_feedback(
        self,
        *,
        analytics: AnalyticsView,
        analysis_evidence: AnalysisEvidence,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
        confidence_annotations: list[ConfidenceAnnotation],
    ) -> CoachFeedbackResult: ...


class PlaceholderCoachFeedbackEngine:
    """Deterministic fallback that preserves the typed report contract."""

    def create_feedback(
        self,
        *,
        analytics: AnalyticsView,
        analysis_evidence: AnalysisEvidence,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
        confidence_annotations: list[ConfidenceAnnotation],
    ) -> CoachFeedbackResult:
        movement = analytics.movement
        positioning = analytics.positioning
        shot_selection = analytics.shot_selection
        match_label = match_type.value.replace("_", " ")
        summary = (
            f"{tracked_player.label} shows solid base movement for {match_label} with "
            f"{movement.total_distance_meters:.1f}m covered, but the current clip suggests "
            "more disciplined recovery and shot selection would improve rally control."
        )

        coach_view = CoachView(
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
        return CoachFeedbackResult(
            coach_view=coach_view,
            generation_mode="fallback",
        )


def _resolve_model_string(*, provider: str, model: str) -> str:
    """Build a PydanticAI model string like 'google-gla:gemini-3.1-flash-lite-preview'."""
    if ":" in model:
        return model
    if provider == "gemini":
        return f"{_GEMINI_PREFIX}:{model}"
    return f"{provider}:{model}"


class LLMCoachFeedbackEngine:
    def __init__(
        self,
        *,
        provider: str = "gemini",
        model: str = "gemini-3.1-flash-lite-preview",
        instructions: str | None = None,
        model_override: Model | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._instructions = instructions or DEFAULT_INSTRUCTIONS
        self._model_string = _resolve_model_string(provider=provider, model=model)
        self._model_override = model_override

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    def create_feedback(
        self,
        *,
        analytics: AnalyticsView,
        analysis_evidence: AnalysisEvidence,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
        confidence_annotations: list[ConfidenceAnnotation],
    ) -> CoachFeedbackResult:
        prompt = self._build_prompt(
            analytics=analytics,
            analysis_evidence=analysis_evidence,
            match_type=match_type,
            tracked_player=tracked_player,
            confidence_annotations=confidence_annotations,
        )
        agent: Agent[Any, LLMCoachOutput] = Agent(
            self._model_override or self._model_string,
            output_type=LLMCoachOutput,
            system_prompt=self._instructions,
        )
        result = agent.run_sync(prompt)
        output = result.output
        ai_rationale = output.ai_rationale or build_default_ai_rationale(analytics)
        return CoachFeedbackResult(
            coach_view=output.coach_view,
            llm_provider=self._provider,
            llm_model=self._model,
            generation_mode="ai",
            ai_rationale=ai_rationale,
        )

    def _build_prompt(
        self,
        *,
        analytics: AnalyticsView,
        analysis_evidence: AnalysisEvidence,
        match_type: MatchType,
        tracked_player: PlayerCandidate,
        confidence_annotations: list[ConfidenceAnnotation],
    ) -> str:
        payload = {
            "match_type": match_type.value,
            "tracked_player": tracked_player.model_dump(mode="json"),
            "analytics": analytics.model_dump(mode="json"),
            "analysis_evidence": analysis_evidence.model_dump(mode="json"),
            "confidence_annotations": [
                annotation.model_dump(mode="json") for annotation in confidence_annotations
            ],
        }
        return json.dumps(payload, indent=2)


def build_coach_feedback_engine_from_env(
    *,
    engine_name: str | None,
    provider: str | None = None,
    model: str | None,
) -> CoachFeedbackEngine:
    if engine_name in ("llm", "pydanticai"):
        return LLMCoachFeedbackEngine(
            provider=provider or "gemini",
            model=model or "gemini-3.1-flash-lite-preview",
        )
    return PlaceholderCoachFeedbackEngine()
