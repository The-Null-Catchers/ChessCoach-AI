from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import CoachingContext
from app.ai.provider_factory import get_ai_provider
from app.ai.template_provider import TemplateCoachProvider
from app.models.entities import AIExplanation, EngineAnalysis, Mistake, Move, Profile
from app.services.ai_usage import record_ai_usage

PROMPT_VERSION = "coach-v1"


def skill_band_for_rating(rating: int | None) -> str:
    if rating is None or rating < 1200:
        return "beginner"
    if rating < 1800:
        return "intermediate"
    return "advanced"


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def ensure_ai_explanation(
    db: Session,
    *,
    user_id: str,
    move: Move,
    analysis: EngineAnalysis,
    mistake: Mistake,
) -> AIExplanation:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    skill_band = skill_band_for_rating(profile.rating if profile else None)
    existing = db.scalar(select(AIExplanation).where(
        AIExplanation.move_id == move.id,
        AIExplanation.prompt_version == PROMPT_VERSION,
        AIExplanation.skill_band == skill_band,
    ))
    if existing:
        return existing

    context = CoachingContext(
        skill_band=skill_band,
        fen=move.fen_before,
        played_move=move.uci,
        best_move=analysis.best_move_uci or move.uci,
        classification=analysis.classification,
        centipawn_loss=analysis.centipawn_loss,
        semantic_theme=mistake.category,
        engine_line=analysis.pv_uci,
    )

    provider = get_ai_provider()
    started = time.perf_counter()
    try:
        result = provider.explain(context)
        record_ai_usage(
            db,
            user_id=user_id,
            move_id=move.id,
            provider=provider,
            status="success",
            latency_ms=_elapsed_ms(started),
        )
    except Exception as exc:
        record_ai_usage(
            db,
            user_id=user_id,
            move_id=move.id,
            provider=provider,
            status="failed",
            latency_ms=_elapsed_ms(started),
            error=exc,
        )
        provider = TemplateCoachProvider()
        started = time.perf_counter()
        result = provider.explain(context)
        record_ai_usage(
            db,
            user_id=user_id,
            move_id=move.id,
            provider=provider,
            status="fallback",
            latency_ms=_elapsed_ms(started),
        )

    explanation = AIExplanation(
        move_id=move.id,
        provider=provider.name,
        model=provider.model,
        prompt_version=PROMPT_VERSION,
        skill_band=skill_band,
        explanation=result.explanation,
        coaching_tip=result.coaching_tip,
        structured_json=json.dumps(result.model_dump()),
    )
    db.add(explanation)
    db.flush()
    return explanation
