from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import PositionAnalysis
from app.services.stockfish import analyze_fen, position_hash, EngineResult

def analyze_cached(db: Session, fen: str, depth: int) -> EngineResult:
    key = position_hash(fen)
    cached = db.scalar(select(PositionAnalysis).where(
        PositionAnalysis.position_hash == key,
        PositionAnalysis.engine_key == 'stockfish',
        PositionAnalysis.depth == depth,
    ))
    if cached:
        return EngineResult(cached.score_cp, cached.mate_in, cached.best_move_uci, cached.pv_uci or '', cached.depth)
    result = analyze_fen(fen, depth=depth, multipv=1)[0]
    db.add(PositionAnalysis(position_hash=key, fen=fen, engine_key='stockfish', depth=depth,
                            score_cp=result.score_cp, mate_in=result.mate_in,
                            best_move_uci=result.best_move_uci, pv_uci=result.pv_uci))
    db.flush()
    return result
