from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import PositionAnalysis
from app.services.stockfish import EngineResult, analyze_fen, position_hash


def _serialize_candidates(results: list[EngineResult]) -> str:
    return json.dumps([
        {
            "score_cp": item.score_cp,
            "mate_in": item.mate_in,
            "best_move_uci": item.best_move_uci,
            "pv_uci": item.pv_uci,
            "depth": item.depth,
        }
        for item in results
    ])


def _deserialize_candidates(raw: str | None) -> list[EngineResult]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
        return [
            EngineResult(
                item.get("score_cp"),
                item.get("mate_in"),
                item.get("best_move_uci"),
                item.get("pv_uci") or "",
                int(item.get("depth") or 0),
            )
            for item in payload
        ]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def analyze_cached_multi(
    db: Session,
    fen: str,
    depth: int,
    multipv: int = 1,
) -> tuple[EngineResult, list[EngineResult]]:
    requested_multipv = max(1, multipv)
    key = position_hash(fen)
    cached = db.scalar(
        select(PositionAnalysis).where(
            PositionAnalysis.position_hash == key,
            PositionAnalysis.engine_key == "stockfish",
            PositionAnalysis.depth == depth,
            PositionAnalysis.multipv == requested_multipv,
        )
    )
    if cached:
        candidates = _deserialize_candidates(cached.candidates_json)
        primary = EngineResult(
            cached.score_cp,
            cached.mate_in,
            cached.best_move_uci,
            cached.pv_uci or "",
            cached.depth,
        )
        if not candidates:
            candidates = [primary]
        return primary, candidates

    results = analyze_fen(fen, depth=depth, multipv=requested_multipv)
    primary = results[0]
    db.add(
        PositionAnalysis(
            position_hash=key,
            fen=fen,
            engine_key="stockfish",
            depth=depth,
            multipv=requested_multipv,
            candidates_json=_serialize_candidates(results),
            score_cp=primary.score_cp,
            mate_in=primary.mate_in,
            best_move_uci=primary.best_move_uci,
            pv_uci=primary.pv_uci,
        )
    )
    db.flush()
    return primary, results


def analyze_cached(db: Session, fen: str, depth: int) -> EngineResult:
    primary, _ = analyze_cached_multi(db, fen, depth=depth, multipv=1)
    return primary
