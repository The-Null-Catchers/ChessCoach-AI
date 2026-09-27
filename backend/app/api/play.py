from __future__ import annotations

from typing import Literal

import chess
import chess.engine
import chess.pgn
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import AnalysisJob, Game, GamePlayer, Move
from app.services.pgn import parse_pgn_many
from app.tasks.analysis import analyze_game

router = APIRouter(prefix="/play", tags=["play"])

Opponent = Literal["engine", "local"]
Color = Literal["white", "black"]


class PlayStartRequest(BaseModel):
    opponent: Opponent = "engine"
    player_color: Color = "white"
    level: int = Field(default=8, ge=1, le=20)
    initial_fen: str | None = None


class PlayMoveRequest(BaseModel):
    fen: str
    move_uci: str
    opponent: Opponent = "engine"
    player_color: Color = "white"
    level: int = Field(default=8, ge=1, le=20)


class PlayCompleteRequest(BaseModel):
    moves: list[str] = Field(min_length=1, max_length=600)
    initial_fen: str | None = None
    player_color: Color = "white"
    opponent: Opponent = "engine"
    level: int = Field(default=8, ge=1, le=20)
    time_control: str | None = Field(default=None, max_length=64)


def _board_from_fen(fen: str | None) -> chess.Board:
    try:
        board = chess.Board(fen) if fen else chess.Board()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid FEN") from exc
    if not board.is_valid():
        raise HTTPException(status_code=422, detail="Invalid chess position")
    return board


def _state(board: chess.Board, *, engine_move: str | None = None) -> dict:
    outcome = board.outcome(claim_draw=True)
    return {
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "legal_moves": [move.uci() for move in board.legal_moves],
        "check": board.is_check(),
        "game_over": outcome is not None,
        "result": outcome.result() if outcome else None,
        "termination": outcome.termination.name.lower() if outcome else None,
        "engine_move": engine_move,
    }


def _apply_uci(board: chess.Board, move_uci: str) -> chess.Move:
    try:
        move = chess.Move.from_uci(move_uci.strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid UCI move") from exc
    if move not in board.legal_moves:
        raise HTTPException(status_code=422, detail="Illegal move")
    board.push(move)
    return move


def _engine_move(board: chess.Board, level: int) -> str:
    if board.is_game_over(claim_draw=True):
        raise HTTPException(status_code=409, detail="Game is already over")
    engine = chess.engine.SimpleEngine.popen_uci(settings.stockfish_path)
    try:
        if "Skill Level" in engine.options:
            engine.configure({"Skill Level": level})
        # Keep interactive play responsive while still scaling effort with level.
        limit = chess.engine.Limit(time=0.04 + level * 0.018, depth=min(6 + level, 22))
        result = engine.play(board, limit)
        if result.move is None:
            raise HTTPException(status_code=503, detail="Engine did not return a move")
        uci = result.move.uci()
        board.push(result.move)
        return uci
    finally:
        engine.quit()


def _build_pgn(payload: PlayCompleteRequest) -> str:
    board = _board_from_fen(payload.initial_fen)
    game = chess.pgn.Game()
    game.headers["Event"] = "ChessCoach Play & Learn"
    game.headers["Site"] = "ChessCoach AI"
    game.headers["White"] = "You" if payload.player_color == "white" else (
        "ChessCoach Engine" if payload.opponent == "engine" else "Local player"
    )
    game.headers["Black"] = "You" if payload.player_color == "black" else (
        "ChessCoach Engine" if payload.opponent == "engine" else "Local player"
    )
    if payload.time_control:
        game.headers["TimeControl"] = payload.time_control
    if payload.initial_fen:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = payload.initial_fen

    node = game
    for raw in payload.moves:
        before = board.copy(stack=False)
        move = _apply_uci(board, raw)
        node = node.add_variation(move)
        # SAN is intentionally computed from the position before the move.
        _ = before.san(move)

    game.headers["Result"] = board.result(claim_draw=True) if board.is_game_over(claim_draw=True) else "*"
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    return game.accept(exporter)


@router.post("/start")
def start_game(
    payload: PlayStartRequest,
    user_id: str = Depends(current_user_id),
):
    del user_id
    board = _board_from_fen(payload.initial_fen)
    engine_move = None
    player_turn = chess.WHITE if payload.player_color == "white" else chess.BLACK
    if payload.opponent == "engine" and board.turn != player_turn and not board.is_game_over(claim_draw=True):
        engine_move = _engine_move(board, payload.level)
    return _state(board, engine_move=engine_move)


@router.post("/move")
def play_move(
    payload: PlayMoveRequest,
    user_id: str = Depends(current_user_id),
):
    del user_id
    board = _board_from_fen(payload.fen)
    player_turn = chess.WHITE if payload.player_color == "white" else chess.BLACK
    if payload.opponent == "engine" and board.turn != player_turn:
        raise HTTPException(status_code=409, detail="It is not the player's turn")

    player_move = _apply_uci(board, payload.move_uci).uci()
    engine_move = None
    if payload.opponent == "engine" and not board.is_game_over(claim_draw=True):
        engine_move = _engine_move(board, payload.level)

    return {**_state(board, engine_move=engine_move), "player_move": player_move}


@router.post("/complete", status_code=202)
def complete_game(
    payload: PlayCompleteRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    pgn_text = _build_pgn(payload)
    parsed = parse_pgn_many(pgn_text)
    if not parsed:
        raise HTTPException(status_code=422, detail="Could not build completed game")
    item = parsed[0]

    existing = db.scalar(
        select(Game).where(Game.user_id == user_id, Game.fingerprint == item.fingerprint)
    )
    if existing:
        return {"game_id": existing.id, "duplicate": True, "job_id": None}

    headers = item.headers
    game = Game(
        user_id=user_id,
        fingerprint=item.fingerprint,
        pgn=item.pgn,
        source="play",
        event=headers.get("Event"),
        site=headers.get("Site"),
        white_name=headers.get("White"),
        black_name=headers.get("Black"),
        result=headers.get("Result"),
        time_control=headers.get("TimeControl"),
        played_at=item.played_at,
    )
    db.add(game)
    db.flush()

    for color, name in (("white", game.white_name), ("black", game.black_name)):
        db.add(
            GamePlayer(
                game_id=game.id,
                user_id=user_id if color == payload.player_color else None,
                color=color,
                name=name,
            )
        )

    for move in item.moves:
        db.add(
            Move(
                game_id=game.id,
                ply=move.ply,
                san=move.san,
                uci=move.uci,
                fen_before=move.fen_before,
                fen_after=move.fen_after,
                clock_seconds=move.clock_seconds,
            )
        )

    job = AnalysisJob(user_id=user_id, game_id=game.id, status="queued", progress=0)
    db.add(job)
    db.commit()
    analyze_game.delay(game.id, job.id)
    return {"game_id": game.id, "job_id": job.id, "duplicate": False}
