from __future__ import annotations

from datetime import datetime, timedelta

import chess
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import EndgameAttempt, EndgameExercise, EndgameReviewState, EndgameStat


DEFAULT_EXERCISES = (
    {
        "slug": "rook-activity-check",
        "category": "rook_endgame",
        "title": "Activate the rook with tempo",
        "objective": "Find the forcing rook move that becomes active with check.",
        "fen": "6k1/8/8/8/8/8/8/R5K1 w - - 0 1",
        "solution_uci": "a1a8",
        "explanation": "Active rooks belong behind or beside the enemy king. A forcing check gains time while improving rook placement.",
        "difficulty": 900,
    },
    {
        "slug": "passed-pawn-advance",
        "category": "king_pawn",
        "title": "Use the two-square pawn advance",
        "objective": "Create maximum space for the passed pawn while the path is clear.",
        "fen": "8/8/8/8/8/3K4/4P3/6k1 w - - 0 1",
        "solution_uci": "e2e4",
        "explanation": "When the pawn is still on its starting square and both squares are clear, the two-square advance can gain useful space immediately.",
        "difficulty": 700,
    },
    {
        "slug": "promote-the-pawn",
        "category": "king_pawn",
        "title": "Convert the passed pawn",
        "objective": "Finish the promotion cleanly.",
        "fen": "8/P6k/8/8/8/8/8/6K1 w - - 0 1",
        "solution_uci": "a7a8q",
        "explanation": "A protected promotion square is not required here because the enemy king cannot reach a8. Promote immediately and convert the material advantage.",
        "difficulty": 650,
    },
)


def ensure_default_exercises(db: Session) -> None:
    for payload in DEFAULT_EXERCISES:
        existing = db.scalar(select(EndgameExercise).where(EndgameExercise.slug == payload["slug"]))
        if existing is None:
            exercise = EndgameExercise(**payload)
            board = chess.Board(exercise.fen)
            move = chess.Move.from_uci(exercise.solution_uci)
            if move not in board.legal_moves:
                raise ValueError(f"Invalid default endgame exercise: {exercise.slug}")
            db.add(exercise)
    db.flush()


def ensure_review_states(db: Session, user_id: str) -> None:
    ensure_default_exercises(db)
    exercises = db.scalars(select(EndgameExercise)).all()
    existing_ids = {
        row.exercise_id
        for row in db.scalars(select(EndgameReviewState).where(EndgameReviewState.user_id == user_id)).all()
    }
    for exercise in exercises:
        if exercise.id not in existing_ids:
            db.add(EndgameReviewState(user_id=user_id, exercise_id=exercise.id))
    db.flush()


def due_endgames(db: Session, user_id: str, limit: int = 20):
    ensure_review_states(db, user_id)
    now = datetime.utcnow()
    rows = db.execute(
        select(EndgameExercise, EndgameReviewState)
        .join(EndgameReviewState, EndgameReviewState.exercise_id == EndgameExercise.id)
        .where(
            EndgameReviewState.user_id == user_id,
            EndgameReviewState.due_at <= now,
        )
    ).all()

    stats = {
        stat.category: stat
        for stat in db.scalars(
            select(EndgameStat).where(
                EndgameStat.user_id == user_id,
                EndgameStat.games_count >= 3,
            )
        ).all()
    }

    def priority(row):
        exercise, state = row
        stat = stats.get(exercise.category)
        game_accuracy = stat.avg_accuracy if stat is not None else 101.0
        return (
            game_accuracy,
            state.mastery,
            state.due_at,
            exercise.difficulty,
        )

    return sorted(rows, key=priority)[:limit]


def record_endgame_attempt(
    db: Session,
    *,
    user_id: str,
    exercise: EndgameExercise,
    state: EndgameReviewState,
    move_uci: str,
    grade: str,
) -> tuple[bool, EndgameAttempt]:
    correct = move_uci.lower() == exercise.solution_uci.lower()
    now = datetime.utcnow()
    effective_grade = grade if correct else "again"

    if effective_grade == "again":
        state.repetitions = 0
        state.interval_days = 0
        state.ease_factor = max(1.3, state.ease_factor - 0.2)
        state.lapses += 1
        state.mastery = max(0.0, state.mastery - 0.2)
        state.due_at = now + timedelta(minutes=10)
    else:
        state.repetitions += 1
        base = {"hard": 1, "good": 3, "easy": 7}[effective_grade]
        if state.repetitions > 1:
            base = max(base, round(max(1, state.interval_days) * state.ease_factor))
        if effective_grade == "hard":
            state.ease_factor = max(1.3, state.ease_factor - 0.08)
            state.mastery = min(1.0, state.mastery + 0.08)
        elif effective_grade == "good":
            state.mastery = min(1.0, state.mastery + 0.15)
        else:
            state.ease_factor += 0.1
            state.mastery = min(1.0, state.mastery + 0.25)
        state.interval_days = base
        state.due_at = now + timedelta(days=base)

    state.last_reviewed_at = now
    attempt = EndgameAttempt(
        user_id=user_id,
        exercise_id=exercise.id,
        move_uci=move_uci.lower(),
        correct=correct,
        grade=effective_grade,
    )
    db.add(attempt)
    db.flush()
    return correct, attempt
