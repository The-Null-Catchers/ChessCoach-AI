from __future__ import annotations
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Game, Move, EngineAnalysis, AnalysisJob
from app.services.engine_cache import analyze_cached
from app.services.classification import MoveContext, classify_move
from app.tasks.celery_app import celery

@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def analyze_game(self, game_id: str, job_id: str, depth: int = 16):
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        game = db.get(Game, game_id)
        if not job or not game:
            return
        job.status = 'analyzing'; job.progress = 5; db.commit()
        moves = db.scalars(select(Move).where(Move.game_id == game_id).order_by(Move.ply)).all()
        total = max(1, len(moves))
        for i, move in enumerate(moves):
            before = analyze_cached(db, move.fen_before, depth)
            after_raw = analyze_cached(db, move.fen_after, depth)
            after_cp = None if after_raw.score_cp is None else -after_raw.score_cp
            after_mate = None if after_raw.mate_in is None else -after_raw.mate_in
            classification, cpl = classify_move(MoveContext(before.score_cp, after_cp, mate_before=before.mate_in, mate_after=after_mate))
            db.add(EngineAnalysis(move_id=move.id, eval_before_cp=before.score_cp, eval_after_cp=after_cp,
                                  mate_before=before.mate_in, mate_after=after_mate, centipawn_loss=cpl,
                                  classification=classification, best_move_uci=before.best_move_uci,
                                  pv_uci=before.pv_uci, depth=depth))
            job.progress = 5 + int((i + 1) / total * 85)
            db.commit()
        game.analyzed = True
        job.status = 'complete'; job.progress = 100
        db.commit()
    except Exception as exc:
        if 'job' in locals() and job:
            job.status = 'failed'; job.error = str(exc)[:1000]; db.commit()
        raise
    finally:
        db.close()
