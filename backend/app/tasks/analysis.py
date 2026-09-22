from __future__ import annotations

import json
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import AnalysisJob, EngineAnalysis, Game, Mistake, Move
from app.services.classification import MoveContext, classify_move
from app.services.coach_explanations import ensure_ai_explanation
from app.services.engine_cache import analyze_cached
from app.services.semantic_mistakes import detect_semantic_mistakes
from app.services.training import create_puzzle_from_mistake, recompute_weaknesses
from app.tasks.celery_app import celery


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def analyze_game(self, game_id: str, job_id: str, depth: int = 16):
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        game = db.get(Game, game_id)
        if not job or not game:
            return

        job.status = "analyzing"
        job.progress = 5
        db.commit()

        moves = db.scalars(select(Move).where(Move.game_id == game_id).order_by(Move.ply)).all()
        total = max(1, len(moves))

        for i, move in enumerate(moves):
            analysis = db.scalar(select(EngineAnalysis).where(EngineAnalysis.move_id == move.id))
            if analysis is None:
                before = analyze_cached(db, move.fen_before, depth)
                after_raw = analyze_cached(db, move.fen_after, depth)
                after_cp = None if after_raw.score_cp is None else -after_raw.score_cp
                after_mate = None if after_raw.mate_in is None else -after_raw.mate_in
                classification, cpl = classify_move(
                    MoveContext(
                        before.score_cp,
                        after_cp,
                        mate_before=before.mate_in,
                        mate_after=after_mate,
                    )
                )
                analysis = EngineAnalysis(
                    move_id=move.id,
                    eval_before_cp=before.score_cp,
                    eval_after_cp=after_cp,
                    mate_before=before.mate_in,
                    mate_after=after_mate,
                    centipawn_loss=cpl,
                    classification=classification,
                    best_move_uci=before.best_move_uci,
                    pv_uci=before.pv_uci,
                    depth=depth,
                )
                db.add(analysis)
                db.flush()

            existing_mistake = db.scalar(select(Mistake).where(Mistake.move_id == move.id))
            if existing_mistake is None:
                semantic = detect_semantic_mistakes(
                    move.fen_before,
                    move.uci,
                    analysis.best_move_uci,
                    analysis.classification,
                    analysis.centipawn_loss,
                )
                if semantic:
                    primary = semantic[0]
                    severity = min(1.0, max(0.1, (analysis.centipawn_loss or 80) / 350.0))
                    existing_mistake = Mistake(
                        game_id=game.id,
                        move_id=move.id,
                        category=primary.category,
                        severity=severity,
                        confidence=primary.confidence,
                        explanation=primary.explanation,
                        evidence_json=json.dumps(primary.evidence),
                    )
                    db.add(existing_mistake)
                    db.flush()
                    create_puzzle_from_mistake(
                        db,
                        game.user_id,
                        game,
                        move,
                        analysis,
                        primary.category,
                    )

            job.progress = 5 + int((i + 1) / total * 82)
            db.commit()

        job.status = "explaining"
        job.progress = 88
        important = db.scalars(
            select(Mistake)
            .where(Mistake.game_id == game.id)
            .order_by(Mistake.severity.desc())
            .limit(5)
        ).all()
        for index, mistake in enumerate(important):
            move = db.get(Move, mistake.move_id)
            analysis = db.scalar(select(EngineAnalysis).where(EngineAnalysis.move_id == mistake.move_id))
            if move and analysis:
                ensure_ai_explanation(
                    db,
                    user_id=game.user_id,
                    move=move,
                    analysis=analysis,
                    mistake=mistake,
                )
                job.progress = 88 + int(((index + 1) / max(1, len(important))) * 4)
                db.commit()

        job.status = "insights"
        job.progress = 94
        recompute_weaknesses(db, game.user_id)
        db.commit()

        game.analyzed = True
        job.status = "complete"
        job.progress = 100
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(AnalysisJob, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)[:1000]
            db.commit()
        raise
    finally:
        db.close()
