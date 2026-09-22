from __future__ import annotations

from typing import Protocol
from pydantic import BaseModel, Field


class CoachingContext(BaseModel):
    skill_band: str
    fen: str
    played_move: str
    best_move: str
    classification: str
    centipawn_loss: int | None = None
    semantic_theme: str
    engine_line: str | None = None


class CoachingExplanation(BaseModel):
    explanation: str = Field(min_length=1, max_length=1200)
    coaching_tip: str = Field(min_length=1, max_length=600)
    concept: str = Field(min_length=1, max_length=120)
    avoid_next_time: str = Field(min_length=1, max_length=400)


class AIProvider(Protocol):
    name: str
    model: str

    def explain(self, context: CoachingContext) -> CoachingExplanation:
        ...
