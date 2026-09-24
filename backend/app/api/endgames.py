from __future__ import annotations

import chess
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import EndgameExercise, EndgameReviewState
from app.schemas.endgames import EndgameAttemptRequest
from app.services.endgame_trainer import (
    due_endgames,
    ensure_review_states,
    record_endgame_attempt,
)

router = APIRouter(prefix="/endgames/trainer", tags=["endgame-trainer"])


@router.get("/overview")
def overview(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    ensure_review_states(db, user_id)
    db.commit()
    due = db.scalar(
        select(func.count(EndgameReviewState.id)).where(
            EndgameReviewState.user_id == user_id,
            EndgameReviewState.due_at <= func.now(),
        )
    ) or 0
    mastery = db.scalar(
        select(func.avg(EndgameReviewState.mastery)).where(
            EndgameReviewState.user_id == user_id
        )
    )
    categories = db.execute(
        select(
            EndgameExercise.category,
            func.count(EndgameExercise.id),
            func.avg(EndgameReviewState.mastery),
        )
        .join(EndgameReviewState, EndgameReviewState.exercise_id == EndgameExercise.id)
        .where(EndgameReviewState.user_id == user_id)
        .group_by(EndgameExercise.category)
        .order_by(func.avg(EndgameReviewState.mastery).asc())
    ).all()
    return {
        "due": due,
        "mastery": round(float(mastery or 0) * 100, 1),
        "categories": [
            {
                "category": category,
                "exercises": count,
                "mastery": round(float(category_mastery or 0) * 100, 1),
            }
            for category, count, category_mastery in categories
        ],
    }


@router.get("/queue")
def queue(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    rows = due_endgames(db, user_id, limit)
    db.commit()
    return [
        {
            "exercise_id": exercise.id,
            "category": exercise.category,
            "title": exercise.title,
            "objective": exercise.objective,
            "fen": exercise.fen,
            "difficulty": exercise.difficulty,
            "mastery": round(state.mastery * 100, 1),
            "repetitions": state.repetitions,
            "lapses": state.lapses,
        }
        for exercise, state in rows
    ]


@router.post("/{exercise_id}/attempt")
def attempt(
    exercise_id: str,
    payload: EndgameAttemptRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    ensure_review_states(db, user_id)
    exercise = db.get(EndgameExercise, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Endgame exercise not found")
    state = db.scalar(
        select(EndgameReviewState).where(
            EndgameReviewState.user_id == user_id,
            EndgameReviewState.exercise_id == exercise.id,
        )
    )
    if state is None:
        raise HTTPException(status_code=404, detail="Endgame review state not found")

    try:
        board = chess.Board(exercise.fen)
        move = chess.Move.from_uci(payload.move_uci.lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid UCI move") from exc
    if move not in board.legal_moves:
        raise HTTPException(status_code=422, detail="Move is not legal in this position")

    correct, attempt_row = record_endgame_attempt(
        db,
        user_id=user_id,
        exercise=exercise,
        state=state,
        move_uci=payload.move_uci,
        grade=payload.grade,
    )
    db.commit()
    return {
        "correct": correct,
        "expected_move_uci": exercise.solution_uci,
        "explanation": exercise.explanation,
        "grade": attempt_row.grade,
        "next_due_at": state.due_at.isoformat(),
        "mastery": round(state.mastery * 100, 1),
    }
