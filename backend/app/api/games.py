from __future__ import annotations
import jwt
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import Game, Move, AnalysisJob, EngineAnalysis
from app.services.pgn import parse_pgn_many
from app.tasks.analysis import analyze_game

router = APIRouter(prefix='/games', tags=['games'])

def current_user_id(authorization: str = Header(...)) -> str:
    try:
        scheme, token = authorization.split(' ', 1)
        if scheme.lower() != 'bearer': raise ValueError
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get('type') != 'access': raise ValueError
        return str(payload['sub'])
    except Exception as exc:
        raise HTTPException(status_code=401, detail='Invalid access token') from exc

@router.post('/import', status_code=202)
async def import_games(pgn_text: str | None = Form(default=None), file: UploadFile | None = File(default=None),
                       user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    if not pgn_text and not file:
        raise HTTPException(400, 'Provide PGN text or file')
    if file:
        raw = await file.read(settings.max_pgn_bytes + 1)
        if len(raw) > settings.max_pgn_bytes: raise HTTPException(413, 'PGN too large')
        pgn_text = raw.decode('utf-8', errors='strict')
    parsed = parse_pgn_many(pgn_text or '')
    if not parsed: raise HTTPException(422, 'No valid games found')
    imported = []
    for item in parsed:
        existing = db.scalar(select(Game).where(Game.user_id == user_id, Game.fingerprint == item.fingerprint))
        if existing:
            imported.append({'game_id': existing.id, 'duplicate': True}); continue
        h = item.headers
        game = Game(user_id=user_id, fingerprint=item.fingerprint, pgn=item.pgn,
                    event=h.get('Event'), site=h.get('Site'), white_name=h.get('White'), black_name=h.get('Black'),
                    result=h.get('Result'), eco=h.get('ECO'), opening=h.get('Opening'), played_at=item.played_at)
        db.add(game); db.flush()
        for m in item.moves:
            db.add(Move(game_id=game.id, ply=m.ply, san=m.san, uci=m.uci, fen_before=m.fen_before, fen_after=m.fen_after))
        job = AnalysisJob(user_id=user_id, game_id=game.id, status='queued', progress=0)
        db.add(job); db.commit()
        analyze_game.delay(game.id, job.id)
        imported.append({'game_id': game.id, 'job_id': job.id, 'duplicate': False})
    return {'count': len(imported), 'games': imported}

@router.get('')
def list_games(user_id: str = Depends(current_user_id), db: Session = Depends(get_db), limit: int = 20, offset: int = 0):
    rows = db.scalars(select(Game).where(Game.user_id == user_id).order_by(Game.created_at.desc()).offset(offset).limit(min(limit, 100))).all()
    return [{'id': g.id, 'white': g.white_name, 'black': g.black_name, 'result': g.result, 'eco': g.eco, 'opening': g.opening, 'analyzed': g.analyzed} for g in rows]

@router.get('/{game_id}/analysis')
def game_analysis(game_id: str, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    game = db.scalar(select(Game).where(Game.id == game_id, Game.user_id == user_id))
    if not game: raise HTTPException(404, 'Game not found')
    moves = db.scalars(select(Move).where(Move.game_id == game_id).order_by(Move.ply)).all()
    out = []
    for m in moves:
        a = db.scalar(select(EngineAnalysis).where(EngineAnalysis.move_id == m.id))
        out.append({'ply': m.ply, 'san': m.san, 'uci': m.uci, 'fen_before': m.fen_before, 'fen_after': m.fen_after,
                    'analysis': None if not a else {'before_cp': a.eval_before_cp, 'after_cp': a.eval_after_cp,
                    'cpl': a.centipawn_loss, 'classification': a.classification, 'best_move': a.best_move_uci, 'pv': a.pv_uci}})
    return {'game_id': game.id, 'analyzed': game.analyzed, 'moves': out}
