from __future__ import annotations

import chess
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import OpeningLine, OpeningRepertoire
from app.schemas.openings import OpeningAttemptRequest, RepertoireCreate, RepertoireImport
from app.services.opening_repertoire import due_training_lines, import_repertoire_pgn, record_opening_attempt

router = APIRouter(prefix="/repertoires", tags=["opening-repertoires"])


def _owned_repertoire(db: Session, repertoire_id: str, user_id: str) -> OpeningRepertoire:
    repertoire = db.scalar(
        select(OpeningRepertoire).where(
            OpeningRepertoire.id == repertoire_id,
            OpeningRepertoire.user_id == user_id,
        )
    )
    if repertoire is None:
        raise HTTPException(status_code=404, detail="Repertoire not found")
    return repertoire


@router.post("", status_code=201)
def create_repertoire(
    payload: RepertoireCreate,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(OpeningRepertoire).where(
            OpeningRepertoire.user_id == user_id,
            OpeningRepertoire.name == payload.name.strip(),
            OpeningRepertoire.color == payload.color,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="A repertoire with this name and color already exists")

    repertoire = OpeningRepertoire(
        user_id=user_id,
        name=payload.name.strip(),
        color=payload.color,
        description=payload.description,
    )
    db.add(repertoire)
    db.commit()
    db.refresh(repertoire)
    return {
        "id": repertoire.id,
        "name": repertoire.name,
        "color": repertoire.color,
        "description": repertoire.description,
        "lines": 0,
        "trainable": 0,
        "due": 0,
    }


@router.get("")
def list_repertoires(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    repertoires = db.scalars(
        select(OpeningRepertoire)
        .where(OpeningRepertoire.user_id == user_id)
        .order_by(OpeningRepertoire.updated_at.desc())
    ).all()
    now = func.now()
    result = []
    for repertoire in repertoires:
        total = db.scalar(
            select(func.count(OpeningLine.id)).where(OpeningLine.repertoire_id == repertoire.id)
        ) or 0
        trainable = db.scalar(
            select(func.count(OpeningLine.id)).where(
                OpeningLine.repertoire_id == repertoire.id,
                OpeningLine.trainable.is_(True),
            )
        ) or 0
        due = db.scalar(
            select(func.count(OpeningLine.id)).where(
                OpeningLine.repertoire_id == repertoire.id,
                OpeningLine.trainable.is_(True),
                OpeningLine.due_at <= now,
            )
        ) or 0
        mastery = db.scalar(
            select(func.avg(OpeningLine.mastery)).where(
                OpeningLine.repertoire_id == repertoire.id,
                OpeningLine.trainable.is_(True),
            )
        )
        result.append({
            "id": repertoire.id,
            "name": repertoire.name,
            "color": repertoire.color,
            "description": repertoire.description,
            "lines": total,
            "trainable": trainable,
            "due": due,
            "mastery": round(float(mastery or 0) * 100, 1),
            "updated_at": repertoire.updated_at.isoformat(),
        })
    return result


@router.get("/{repertoire_id}")
def repertoire_tree(
    repertoire_id: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    repertoire = _owned_repertoire(db, repertoire_id, user_id)
    lines = db.scalars(
        select(OpeningLine)
        .where(OpeningLine.repertoire_id == repertoire.id)
        .order_by(OpeningLine.ply.asc(), OpeningLine.move_san.asc())
    ).all()
    return {
        "id": repertoire.id,
        "name": repertoire.name,
        "color": repertoire.color,
        "description": repertoire.description,
        "lines": [
            {
                "id": line.id,
                "parent_id": line.parent_id,
                "ply": line.ply,
                "fen_before": line.fen_before,
                "move_uci": line.move_uci,
                "move_san": line.move_san,
                "trainable": line.trainable,
                "mastery": round(line.mastery * 100, 1),
                "due_at": line.due_at.isoformat(),
            }
            for line in lines
        ],
    }


@router.post("/{repertoire_id}/import-pgn")
def import_pgn(
    repertoire_id: str,
    payload: RepertoireImport,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    repertoire = _owned_repertoire(db, repertoire_id, user_id)
    try:
        imported = import_repertoire_pgn(db, repertoire, payload.pgn)
    except (ValueError, chess.InvalidMoveError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="Invalid repertoire PGN") from exc
    db.commit()
    return {"imported_nodes": imported}


@router.get("/{repertoire_id}/training")
def training_queue(
    repertoire_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    repertoire = _owned_repertoire(db, repertoire_id, user_id)
    return [
        {
            "line_id": line.id,
            "fen": line.fen_before,
            "ply": line.ply,
            "mastery": round(line.mastery * 100, 1),
            "repetitions": line.repetitions,
            "lapses": line.lapses,
        }
        for line in due_training_lines(db, repertoire.id, limit)
    ]


@router.post("/{repertoire_id}/lines/{line_id}/attempt")
def attempt_line(
    repertoire_id: str,
    line_id: str,
    payload: OpeningAttemptRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    repertoire = _owned_repertoire(db, repertoire_id, user_id)
    line = db.scalar(
        select(OpeningLine).where(
            OpeningLine.id == line_id,
            OpeningLine.repertoire_id == repertoire.id,
            OpeningLine.trainable.is_(True),
        )
    )
    if line is None:
        raise HTTPException(status_code=404, detail="Training line not found")

    try:
        move = chess.Move.from_uci(payload.move_uci.lower())
        board = chess.Board(line.fen_before)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid UCI move") from exc
    if move not in board.legal_moves:
        raise HTTPException(status_code=422, detail="Move is not legal in this position")

    correct, attempt = record_opening_attempt(
        db,
        user_id=user_id,
        line=line,
        move_uci=payload.move_uci,
        grade=payload.grade,
    )
    db.commit()
    return {
        "correct": correct,
        "expected_move_uci": line.move_uci,
        "expected_move_san": line.move_san,
        "grade": attempt.grade,
        "next_due_at": line.due_at.isoformat(),
        "mastery": round(line.mastery * 100, 1),
    }
