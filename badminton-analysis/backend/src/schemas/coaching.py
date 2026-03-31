from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CoachView(BaseModel):
    summary: str
    strengths: list[str]
    priority_issues: list[str]
    shot_selection_notes: str
    footwork_notes: str
    positioning_notes: str
    confidence_notes: str
    recommended_drills: list[str]


class AIRationale(BaseModel):
    summary: str
    evidence_highlights: list[str]


class CoachFeedbackResult(BaseModel):
    coach_view: CoachView
    llm_provider: str | None = None
    llm_model: str | None = None
    generation_mode: Literal["ai", "fallback"]
    ai_rationale: AIRationale | None = None
