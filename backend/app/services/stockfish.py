from __future__ import annotations

import atexit
import hashlib
import threading
from dataclasses import dataclass

import chess
import chess.engine

from app.core.config import settings


@dataclass(frozen=True)
class EngineResult:
    score_cp: int | None
    mate_in: int | None
    best_move_uci: str | None
    pv_uci: str
    depth: int


@dataclass(frozen=True)
class AnalysisProfile:
    name: str
    depth: int
    multipv: int


_ENGINE_LOCK = threading.RLock()
_ENGINE: chess.engine.SimpleEngine | None = None


def position_hash(fen: str) -> str:
    normalized = " ".join(fen.split(" ")[:4])
    return hashlib.sha256(normalized.encode()).hexdigest()


def analysis_profile(name: str | None) -> AnalysisProfile:
    normalized = (name or "normal").strip().lower()
    profiles = {
        "quick": AnalysisProfile("quick", settings.analysis_quick_depth, settings.analysis_quick_multipv),
        "normal": AnalysisProfile("normal", settings.analysis_default_depth, settings.analysis_normal_multipv),
        "deep": AnalysisProfile("deep", settings.analysis_deep_depth, settings.analysis_deep_multipv),
    }
    if normalized not in profiles:
        raise ValueError(f"Unknown analysis profile: {name}")
    return profiles[normalized]


def _open_engine() -> chess.engine.SimpleEngine:
    return chess.engine.SimpleEngine.popen_uci(settings.stockfish_path)


def _get_engine_unlocked() -> chess.engine.SimpleEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _open_engine()
    return _ENGINE


def _close_engine_unlocked() -> None:
    global _ENGINE
    engine, _ENGINE = _ENGINE, None
    if engine is None:
        return
    try:
        engine.quit()
    except Exception:
        # The process may already be gone. There is nothing useful to recover
        # during shutdown/restart cleanup.
        pass


def close_engine() -> None:
    with _ENGINE_LOCK:
        _close_engine_unlocked()


atexit.register(close_engine)


def _analyse_once(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    *,
    depth: int,
    multipv: int,
):
    return engine.analyse(
        board,
        chess.engine.Limit(depth=depth),
        multipv=max(1, multipv),
    )


def analyze_fen(fen: str, depth: int | None = None, multipv: int = 1) -> list[EngineResult]:
    depth = depth or settings.analysis_default_depth
    board = chess.Board(fen)

    with _ENGINE_LOCK:
        engine = _get_engine_unlocked()
        try:
            infos = _analyse_once(engine, board, depth=depth, multipv=multipv)
        except (chess.engine.EngineTerminatedError, BrokenPipeError):
            # Workers are long-lived. If Stockfish dies unexpectedly, restart it
            # once inside this worker process instead of failing every later job.
            _close_engine_unlocked()
            engine = _get_engine_unlocked()
            infos = _analyse_once(engine, board, depth=depth, multipv=multipv)

    if not isinstance(infos, list):
        infos = [infos]

    out: list[EngineResult] = []
    for info in infos:
        pov = info["score"].pov(board.turn)
        mate = pov.mate()
        cp = None if mate is not None else pov.score(mate_score=100000)
        pv = info.get("pv", [])
        out.append(
            EngineResult(
                cp,
                mate,
                pv[0].uci() if pv else None,
                " ".join(move.uci() for move in pv),
                int(info.get("depth", depth)),
            )
        )
    return out
