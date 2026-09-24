from __future__ import annotations

from datetime import datetime, timedelta
import io

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import OpeningLine, OpeningLineAttempt, OpeningRepertoire

GRADE_INTERVALS = {
    "again": 0,
    "hard": 1,
    "good": 3,
    "easy": 7,
}


def import_repertoire_pgn(db: Session, repertoire: OpeningRepertoire, pgn_text: str) -> int:
    handle = io.StringIO(pgn_text)
    imported = 0

    while True:
        game = chess.pgn.read_game(handle)
        if game is None:
            break
        board = game.board()
        imported += _walk_variations(db, repertoire, board, game, parent_id=None)
    repertoire.updated_at = datetime.utcnow()
    db.flush()
    return imported


def _walk_variations(
    db: Session,
    repertoire: OpeningRepertoire,
    board: chess.Board,
    node: chess.pgn.GameNode,
    *,
    parent_id: str | None,
) -> int:
    created = 0
    for child in node.variations:
        move = child.move
        if move is None or move not in board.legal_moves:
            continue

        mover = "white" if board.turn == chess.WHITE else "black"
        san = board.san(move)
        fen_before = board.fen()
        existing = db.scalar(
            select(OpeningLine).where(
                OpeningLine.repertoire_id == repertoire.id,
                OpeningLine.parent_id == parent_id,
                OpeningLine.move_uci == move.uci(),
            )
        )
        if existing is None:
            existing = OpeningLine(
                repertoire_id=repertoire.id,
                parent_id=parent_id,
                ply=board.ply() + 1,
                fen_before=fen_before,
                move_uci=move.uci(),
                move_san=san,
                trainable=mover == repertoire.color,
                source="pgn",
            )
            db.add(existing)
            db.flush()
            created += 1

        board.push(move)
        created += _walk_variations(
            db,
            repertoire,
            board,
            child,
            parent_id=existing.id,
        )
        board.pop()
    return created


def due_training_lines(db: Session, repertoire_id: str, limit: int = 20) -> list[OpeningLine]:
    now = datetime.utcnow()
    return db.scalars(
        select(OpeningLine)
        .where(
            OpeningLine.repertoire_id == repertoire_id,
            OpeningLine.trainable.is_(True),
            OpeningLine.due_at <= now,
        )
        .order_by(OpeningLine.due_at.asc(), OpeningLine.mastery.asc(), OpeningLine.ply.asc())
        .limit(limit)
    ).all()


def record_opening_attempt(
    db: Session,
    *,
    user_id: str,
    line: OpeningLine,
    move_uci: str,
    grade: str,
) -> tuple[bool, OpeningLineAttempt]:
    correct = move_uci.lower() == line.move_uci.lower()
    now = datetime.utcnow()

    effective_grade = grade if correct else "again"
    if effective_grade == "again":
        line.repetitions = 0
        line.interval_days = 0
        line.ease_factor = max(1.3, line.ease_factor - 0.2)
        line.lapses += 1
        line.mastery = max(0.0, line.mastery - 0.2)
        line.due_at = now + timedelta(minutes=10)
    else:
        line.repetitions += 1
        base_days = GRADE_INTERVALS[effective_grade]
        if line.repetitions > 1:
            base_days = max(base_days, round(max(1, line.interval_days) * line.ease_factor))
        if effective_grade == "hard":
            line.ease_factor = max(1.3, line.ease_factor - 0.08)
            line.mastery = min(1.0, line.mastery + 0.08)
        elif effective_grade == "good":
            line.mastery = min(1.0, line.mastery + 0.15)
        elif effective_grade == "easy":
            line.ease_factor += 0.1
            line.mastery = min(1.0, line.mastery + 0.25)
        line.interval_days = base_days
        line.due_at = now + timedelta(days=base_days)

    line.last_reviewed_at = now
    attempt = OpeningLineAttempt(
        user_id=user_id,
        line_id=line.id,
        move_uci=move_uci.lower(),
        correct=correct,
        grade=effective_grade,
    )
    db.add(attempt)
    db.flush()
    return correct, attempt
