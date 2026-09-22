from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import Game, Mistake, PlayerWeakness, Puzzle, PuzzleAttempt

router = APIRouter(tags=["coaching"])


class PuzzleAttemptRequest(BaseModel):
    move_uci: str = Field(min_length=4, max_length=5)
    grade: Literal["Again", "Hard", "Good", "Easy"] = "Good"
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)


@router.get("/profile/weaknesses")
def weaknesses(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(PlayerWeakness)
        .where(PlayerWeakness.user_id == user_id)
        .order_by(PlayerWeakness.score.desc())
    ).all()
    return [
        {
            "category": row.category,
            "score": row.score,
            "confidence": row.confidence,
            "sample_size": row.sample_size,
            "trend": row.trend,
        }
        for row in rows
    ]


@router.get("/games/{game_id}/mistakes")
def game_mistakes(
    game_id: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    game = db.scalar(select(Game).where(Game.id == game_id, Game.user_id == user_id))
    if not game:
        raise HTTPException(404, "Game not found")

    mistakes = db.scalars(
        select(Mistake).where(Mistake.game_id == game_id).order_by(Mistake.severity.desc())
    ).all()
    return [
        {
            "id": m.id,
            "move_id": m.move_id,
            "category": m.category,
            "severity": m.severity,
            "confidence": m.confidence,
            "explanation": m.explanation,
        }
        for m in mistakes
    ]


@router.get("/puzzles")
def puzzles(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    theme: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    query = select(Puzzle).where(Puzzle.user_id == user_id)
    if theme:
        query = query.where(Puzzle.theme == theme)
    rows = db.scalars(query.order_by(Puzzle.difficulty.asc()).limit(limit)).all()
    return [
        {
            "id": p.id,
            "fen": p.fen,
            "theme": p.theme,
            "difficulty": p.difficulty,
            "source": p.source,
            "source_game_id": p.source_game_id,
        }
        for p in rows
    ]


@router.post("/puzzles/{puzzle_id}/attempt")
def attempt_puzzle(
    puzzle_id: str,
    payload: PuzzleAttemptRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    puzzle = db.scalar(select(Puzzle).where(Puzzle.id == puzzle_id, Puzzle.user_id == user_id))
    if not puzzle:
        raise HTTPException(404, "Puzzle not found")

    expected = puzzle.solution_uci.split()[0]
    correct = payload.move_uci == expected
    attempt = PuzzleAttempt(
        user_id=user_id,
        puzzle_id=puzzle.id,
        correct=correct,
        grade=payload.grade if correct else "Again",
        duration_seconds=payload.duration_seconds,
    )
    db.add(attempt)
    db.commit()
    return {
        "correct": correct,
        "expected_move": expected if not correct else None,
        "grade": attempt.grade,
        "theme": puzzle.theme,
    }
