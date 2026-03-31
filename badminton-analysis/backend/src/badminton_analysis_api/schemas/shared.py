from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class MatchType(StrEnum):
    MENS_SINGLES = "mens_singles"
    WOMENS_SINGLES = "womens_singles"
    MENS_DOUBLES = "mens_doubles"
    WOMENS_DOUBLES = "womens_doubles"
    MIXED_DOUBLES = "mixed_doubles"


class CourtPoint(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class DetectionBox(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


class CourtModel(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    points: list[CourtPoint]
    adjustment_hint: str


class PlayerCandidate(BaseModel):
    player_id: str
    label: str
    side: Literal["near", "far"]
    focus_hint: str
    detection_id: str | None = None
    bounding_box: DetectionBox | None = None
