from __future__ import annotations

import math
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import (
    EngineAnalysis,
    Game,
    GamePlayer,
    Mistake,
    MistakeCategory,
    MistakeCategoryLink,
    Move,
    PlayerWeakness,
    Puzzle,
)
from app.models.weakness_history import WeaknessSnapshot
from app.services.mistake_taxonomy import ensure_primary_link


def create_puzzle_from_mistake(
    db: Session,
    user_id: str,
    game: Game,
    move: Move,
    analysis: EngineAnalysis,
    theme: str,
) -> Puzzle | None:
    if not analysis.best_move_uci or not analysis.pv_uci:
        return None
    existing = db.scalar(select(Puzzle).where(
        Puzzle.user_id == user_id,
        Puzzle.source_game_id == game.id,
        Puzzle.fen == move.fen_before,
    ))
    if existing:
        return existing
    solution = analysis.pv_uci
    difficulty = 1200
    if analysis.centipawn_loss:
        difficulty += min(600, analysis.centipawn_loss)
    puzzle = Puzzle(
        user_id=user_id,
        source_game_id=game.id,
        fen=move.fen_before,
        solution_uci=solution,
        theme=theme,
        difficulty=difficulty,
        source="user_game",
    )
    db.add(puzzle)
    return puzzle


def _is_player_ply(ply: int, color: str) -> bool:
    return (ply % 2 == 1 and color == "white") or (ply % 2 == 0 and color == "black")


def weakness_trend_delta(previous_score: float | None, current_score: float) -> float:
    if previous_score is None:
        return 0.0
    return round(current_score - previous_score, 4)


def recompute_weaknesses(db: Session, user_id: str) -> list[PlayerWeakness]:
    rows = db.execute(
        select(Mistake, Move, GamePlayer)
        .join(Move, Move.id == Mistake.move_id)
        .join(GamePlayer, GamePlayer.game_id == Mistake.game_id)
        .where(GamePlayer.user_id == user_id)
    ).all()

    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for mistake, move, player in rows:
        if not _is_player_ply(move.ply, player.color):
            continue
        ensure_primary_link(db, mistake)
        categories = db.execute(
            select(MistakeCategory.slug, MistakeCategoryLink.confidence)
            .join(MistakeCategoryLink, MistakeCategoryLink.category_id == MistakeCategory.id)
            .where(MistakeCategoryLink.mistake_id == mistake.id)
        ).all()
        for slug, confidence in categories:
            grouped[slug].append((float(mistake.severity), float(confidence)))

    db.execute(delete(PlayerWeakness).where(PlayerWeakness.user_id == user_id))
    weaknesses: list[PlayerWeakness] = []
    for category, samples in grouped.items():
        n = len(samples)
        avg_severity = sum(severity for severity, _ in samples) / n
        avg_detection_confidence = sum(confidence for _, confidence in samples) / n
        sample_confidence = 1.0 - math.exp(-n / 6.0)
        confidence = round(min(0.99, avg_detection_confidence * sample_confidence), 4)
        score = round(avg_severity * (0.6 + 0.4 * confidence), 4)

        latest_snapshot = db.scalar(
            select(WeaknessSnapshot)
            .where(
                WeaknessSnapshot.user_id == user_id,
                WeaknessSnapshot.category == category,
            )
            .order_by(WeaknessSnapshot.captured_at.desc())
            .limit(1)
        )
        previous_score = latest_snapshot.score if latest_snapshot is not None else None
        trend = weakness_trend_delta(previous_score, score)

        weakness = PlayerWeakness(
            user_id=user_id,
            category=category,
            score=score,
            confidence=confidence,
            sample_size=n,
            trend=trend,
        )
        db.add(weakness)
        weaknesses.append(weakness)

        changed = (
            latest_snapshot is None
            or latest_snapshot.score != score
            or latest_snapshot.confidence != confidence
            or latest_snapshot.sample_size != n
        )
        if changed:
            db.add(WeaknessSnapshot(
                user_id=user_id,
                category=category,
                score=score,
                confidence=confidence,
                sample_size=n,
            ))
    return weaknesses
