from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import (
    AIExplanation,
    Game,
    Mistake,
    MistakeCategory,
    MistakeCategoryLink,
    PlayerWeakness,
    Puzzle,
    PuzzleAttempt,
    ReviewState,
)
from app.services.spaced_repetition import schedule_review

router = APIRouter(tags=["coaching"])
Grade = Literal["Again", "Hard", "Good", "Easy"]


class PuzzleAttemptRequest(BaseModel):
    move_uci: str = Field(min_length=4, max_length=5)
    grade: Grade | None = None
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)


class PuzzleGradeRequest(BaseModel):
    attempt_id: str
    grade: Literal["Hard", "Good", "Easy"]


def _apply_review_grade(
    db: Session,
    *,
    user_id: str,
    puzzle_id: str,
    grade: Grade,
) -> ReviewState:
    review = db.scalar(select(ReviewState).where(
        ReviewState.user_id == user_id,
        ReviewState.puzzle_id == puzzle_id,
    ))
    if review is None:
        review = ReviewState(user_id=user_id, puzzle_id=puzzle_id)
        db.add(review)
        db.flush()
    now = datetime.utcnow()
    scheduled = schedule_review(
        grade,
        repetitions=review.repetitions,
        interval_days=review.interval_days,
        ease_factor=review.ease_factor,
        lapses=review.lapses,
        now=now,
    )
    review.repetitions = scheduled.repetitions
    review.interval_days = scheduled.interval_days
    review.ease_factor = scheduled.ease_factor
    review.lapses = scheduled.lapses
    review.due_at = scheduled.due_at
    review.last_reviewed_at = now
    return review


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
    result = []
    for mistake in mistakes:
        ai = db.scalar(
            select(AIExplanation)
            .where(AIExplanation.move_id == mistake.move_id)
            .order_by(AIExplanation.created_at.desc())
        )
        categories = db.execute(
            select(MistakeCategory.slug, MistakeCategory.title, MistakeCategory.group, MistakeCategoryLink.confidence)
            .join(MistakeCategoryLink, MistakeCategoryLink.category_id == MistakeCategory.id)
            .where(MistakeCategoryLink.mistake_id == mistake.id)
            .order_by(MistakeCategoryLink.confidence.desc())
        ).all()
        result.append({
            "id": mistake.id,
            "move_id": mistake.move_id,
            "category": mistake.category,
            "severity": mistake.severity,
            "confidence": mistake.confidence,
            "categories": [
                {"slug": slug, "title": title, "group": group, "confidence": confidence}
                for slug, title, group, confidence in categories
            ],
            "explanation": mistake.explanation,
            "ai_coach": None if ai is None else {
                "provider": ai.provider,
                "model": ai.model,
                "skill_band": ai.skill_band,
                "explanation": ai.explanation,
                "coaching_tip": ai.coaching_tip,
            },
        })
    return result


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
            "id": puzzle.id,
            "fen": puzzle.fen,
            "theme": puzzle.theme,
            "difficulty": puzzle.difficulty,
            "source": puzzle.source,
            "source_game_id": puzzle.source_game_id,
        }
        for puzzle in rows
    ]


@router.get("/puzzles/queue")
def puzzle_queue(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    theme: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    now = datetime.utcnow()
    query = (
        select(Puzzle, ReviewState)
        .outerjoin(
            ReviewState,
            (ReviewState.puzzle_id == Puzzle.id) & (ReviewState.user_id == user_id),
        )
        .where(
            Puzzle.user_id == user_id,
            or_(ReviewState.id.is_(None), ReviewState.due_at <= now),
        )
    )
    if theme:
        query = query.where(Puzzle.theme == theme)
    rows = db.execute(
        query.order_by(ReviewState.due_at.asc().nullsfirst(), Puzzle.difficulty.asc()).limit(limit)
    ).all()
    return [
        {
            "id": puzzle.id,
            "fen": puzzle.fen,
            "theme": puzzle.theme,
            "difficulty": puzzle.difficulty,
            "source": puzzle.source,
            "source_game_id": puzzle.source_game_id,
            "due_at": review.due_at.isoformat() if review else None,
            "repetitions": review.repetitions if review else 0,
            "lapses": review.lapses if review else 0,
        }
        for puzzle, review in rows
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
    actual_grade: str = payload.grade if correct and payload.grade else ("Pending" if correct else "Again")
    attempt = PuzzleAttempt(
        user_id=user_id,
        puzzle_id=puzzle.id,
        correct=correct,
        grade=actual_grade,
        duration_seconds=payload.duration_seconds,
    )
    db.add(attempt)
    db.flush()

    review = None
    if not correct:
        review = _apply_review_grade(db, user_id=user_id, puzzle_id=puzzle.id, grade="Again")
    elif payload.grade:
        review = _apply_review_grade(db, user_id=user_id, puzzle_id=puzzle.id, grade=payload.grade)

    db.commit()
    return {
        "attempt_id": attempt.id,
        "correct": correct,
        "expected_move": expected if not correct else None,
        "solution_line": puzzle.solution_uci,
        "grade": attempt.grade,
        "theme": puzzle.theme,
        "requires_grade": correct and payload.grade is None,
        "next_due_at": review.due_at.isoformat() if review else None,
        "interval_days": review.interval_days if review else None,
    }


@router.post("/puzzles/{puzzle_id}/grade")
def grade_puzzle(
    puzzle_id: str,
    payload: PuzzleGradeRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    puzzle = db.scalar(select(Puzzle).where(Puzzle.id == puzzle_id, Puzzle.user_id == user_id))
    if not puzzle:
        raise HTTPException(404, "Puzzle not found")
    attempt = db.scalar(select(PuzzleAttempt).where(
        PuzzleAttempt.id == payload.attempt_id,
        PuzzleAttempt.user_id == user_id,
        PuzzleAttempt.puzzle_id == puzzle_id,
    ))
    if not attempt:
        raise HTTPException(404, "Puzzle attempt not found")
    if not attempt.correct:
        raise HTTPException(409, "Incorrect attempts are automatically graded Again")
    if attempt.grade != "Pending":
        raise HTTPException(409, "This attempt has already been graded")

    attempt.grade = payload.grade
    review = _apply_review_grade(db, user_id=user_id, puzzle_id=puzzle.id, grade=payload.grade)
    db.commit()
    return {
        "attempt_id": attempt.id,
        "grade": attempt.grade,
        "next_due_at": review.due_at.isoformat(),
        "interval_days": review.interval_days,
        "ease_factor": review.ease_factor,
    }
