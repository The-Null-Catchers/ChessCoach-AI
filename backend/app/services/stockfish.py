from __future__ import annotations
import hashlib
import chess
import chess.engine
from dataclasses import dataclass
from app.core.config import settings

@dataclass
class EngineResult:
    score_cp: int | None
    mate_in: int | None
    best_move_uci: str | None
    pv_uci: str
    depth: int


def position_hash(fen: str) -> str:
    normalized = ' '.join(fen.split(' ')[:4])
    return hashlib.sha256(normalized.encode()).hexdigest()


def analyze_fen(fen: str, depth: int | None = None, multipv: int = 1) -> list[EngineResult]:
    depth = depth or settings.analysis_default_depth
    board = chess.Board(fen)
    engine = chess.engine.SimpleEngine.popen_uci(settings.stockfish_path)
    try:
        infos = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
        if not isinstance(infos, list):
            infos = [infos]
        out: list[EngineResult] = []
        for info in infos:
            pov = info['score'].pov(board.turn)
            mate = pov.mate()
            cp = None if mate is not None else pov.score(mate_score=100000)
            pv = info.get('pv', [])
            out.append(EngineResult(cp, mate, pv[0].uci() if pv else None, ' '.join(m.uci() for m in pv), int(info.get('depth', depth))))
        return out
    finally:
        engine.quit()
