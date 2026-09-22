from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Mistake, MistakeCategory, MistakeCategoryLink
from app.services.semantic_mistakes import SemanticMistake

TACTICAL = {
    "hanging_piece", "missed_fork", "missed_pin", "missed_check", "missed_forcing_move",
    "back_rank_weakness", "mating_pattern", "trapped_piece", "overloaded_defender",
}
OPENING = {"early_queen_activity", "delayed_castling", "poor_piece_development", "opening_theory_mistake"}
POSITIONAL = {"king_safety", "weak_square", "pawn_structure", "inactive_rook", "bad_bishop", "critical_decision"}
ENDGAME = {"king_activity", "opposition", "rook_endgame", "pawn_race", "passed_pawn"}
TIME = {"time_trouble", "critical_move_too_fast", "easy_move_too_slow"}


def category_group(slug: str) -> str:
    if slug in TACTICAL:
        return "tactical"
    if slug in OPENING:
        return "opening"
    if slug in ENDGAME:
        return "endgame"
    if slug in TIME:
        return "time_management"
    if slug in POSITIONAL:
        return "positional"
    return "strategic"


def ensure_category(db: Session, slug: str) -> MistakeCategory:
    category = db.scalar(select(MistakeCategory).where(MistakeCategory.slug == slug))
    if category:
        return category
    category = MistakeCategory(
        slug=slug,
        title=slug.replace("_", " ").title(),
        group=category_group(slug),
    )
    db.add(category)
    db.flush()
    return category


def attach_semantic_categories(
    db: Session,
    mistake: Mistake,
    semantic: list[SemanticMistake],
) -> None:
    for item in semantic:
        category = ensure_category(db, item.category)
        existing = db.scalar(select(MistakeCategoryLink).where(
            MistakeCategoryLink.mistake_id == mistake.id,
            MistakeCategoryLink.category_id == category.id,
        ))
        if existing:
            existing.confidence = max(existing.confidence, item.confidence)
            existing.evidence_json = json.dumps(item.evidence)
            continue
        db.add(MistakeCategoryLink(
            mistake_id=mistake.id,
            category_id=category.id,
            confidence=item.confidence,
            evidence_json=json.dumps(item.evidence),
        ))
    db.flush()


def ensure_primary_link(db: Session, mistake: Mistake) -> None:
    category = ensure_category(db, mistake.category)
    existing = db.scalar(select(MistakeCategoryLink).where(
        MistakeCategoryLink.mistake_id == mistake.id,
        MistakeCategoryLink.category_id == category.id,
    ))
    if existing is None:
        db.add(MistakeCategoryLink(
            mistake_id=mistake.id,
            category_id=category.id,
            confidence=mistake.confidence,
            evidence_json=mistake.evidence_json,
        ))
        db.flush()
