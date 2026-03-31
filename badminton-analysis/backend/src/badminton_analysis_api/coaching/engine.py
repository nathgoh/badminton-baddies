from __future__ import annotations

import json
from collections.abc import Callable
from importlib import import_module
from typing import Protocol

from pydantic import BaseModel

from ..analyses.evidence import build_default_ai_rationale
from ..schemas import (
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


class StructuredLLMClient(Protocol):
    def generate(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
    ) -> dict[str, object]: ...


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


class GeminiStructuredClient:
    def generate(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
    ) -> dict[str, object]:
        if provider != "gemini":
            raise RuntimeError(f"Gemini client cannot serve provider '{provider}'.")

        try:
            genai = import_module("google.genai")
            types = import_module("google.genai.types")
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed.") from exc

        with genai.Client() as client:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LLMCoachOutput,
                    temperature=0.2,
                ),
            )
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, BaseModel):
            return parsed.model_dump(mode="json")
        if parsed is not None:
            return parsed
        response_text = getattr(response, "text", None)
        if not response_text:
            raise RuntimeError("Gemini did not return a structured response.")
        return json.loads(response_text)


class PydanticAIStructuredClient:
    def generate(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
    ) -> dict[str, object]:
        try:
            agent_module = import_module("pydantic_ai")
        except ImportError as exc:
            raise RuntimeError("pydantic_ai is not installed.") from exc

        resolved_model = model if ":" in model else f"{provider}:{model}"
        agent = agent_module.Agent(
            resolved_model,
            output_type=LLMCoachOutput,
        )
        result = agent.run_sync(prompt)
        output = getattr(result, "output", result)
        if isinstance(output, BaseModel):
            return output.model_dump(mode="json")
        if isinstance(output, dict):
            return output
        return LLMCoachOutput.model_validate(output).model_dump(mode="json")


def _build_llm_client(provider: str) -> StructuredLLMClient:
    if provider == "gemini":
        return GeminiStructuredClient()
    return PydanticAIStructuredClient()


class LLMCoachFeedbackEngine:
    def __init__(
        self,
        *,
        provider: str = "gemini",
        model: str = "gemini-3-flash-preview",
        instructions: str | None = None,
        client_factory: Callable[[str], StructuredLLMClient] = _build_llm_client,
    ) -> None:
        self._provider = provider
        self._model = model
        self._instructions = instructions or DEFAULT_INSTRUCTIONS
        self._client_factory = client_factory

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
        client = self._client_factory(self._provider)
        prompt = self._build_prompt(
            analytics=analytics,
            analysis_evidence=analysis_evidence,
            match_type=match_type,
            tracked_player=tracked_player,
            confidence_annotations=confidence_annotations,
        )
        output = LLMCoachOutput.model_validate(
            client.generate(
                provider=self._provider,
                model=self._model,
                prompt=prompt,
            )
        )
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
            "instructions": self._instructions,
            "match_type": match_type.value,
            "tracked_player": tracked_player.model_dump(mode="json"),
            "analytics": analytics.model_dump(mode="json"),
            "analysis_evidence": analysis_evidence.model_dump(mode="json"),
            "confidence_annotations": [
                annotation.model_dump(mode="json") for annotation in confidence_annotations
            ],
        }
        return json.dumps(payload, indent=2)


class PydanticAICoachFeedbackEngine(LLMCoachFeedbackEngine):
    """Compatibility wrapper for older tests and env configs."""

    def __init__(
        self,
        *,
        model: str = "openai:gpt-5.2",
        instructions: str | None = None,
    ) -> None:
        if ":" in model:
            provider, resolved_model = model.split(":", 1)
        else:
            provider, resolved_model = "openai", model
        super().__init__(
            provider=provider,
            model=resolved_model,
            instructions=instructions,
            client_factory=lambda _provider: PydanticAIStructuredClient(),
        )


def build_coach_feedback_engine_from_env(
    *,
    engine_name: str | None,
    provider: str | None = None,
    model: str | None,
) -> CoachFeedbackEngine:
    if engine_name == "pydanticai":
        return PydanticAICoachFeedbackEngine(model=model or "openai:gpt-5.2")
    if engine_name == "llm":
        return LLMCoachFeedbackEngine(
            provider=provider or "gemini",
            model=model or "gemini-3-flash-preview",
        )
    return PlaceholderCoachFeedbackEngine()
