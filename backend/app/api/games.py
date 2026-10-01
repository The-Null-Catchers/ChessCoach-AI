from __future__ import annotations
import json
import jwt
from typing import Literal
from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.rate_limit import GAME_IMPORT_LIMIT, REANALYSIS_LIMIT, enforce_rate_limit
from app.db.session import get_db
from app.models.entities import AnalysisJob, ConnectedAccount, EngineAnalysis, Game, GamePlayer, Move, User
from app.services.player_identity import link_game_players
from app.services.pgn import parse_pgn_many
from app.services.provider_imports import ProviderImportError, fetch_provider_games, normalize_username
from app.tasks.analysis import analyze_game
from app.services.stockfish import analysis_profile
from app.services.player_analytics import accuracy_from_cpl, classify_endgame

router = APIRouter(prefix='/games', tags=['games'])

class IdentifyPlayerRequest(BaseModel):
    color: Literal["white", "black"]


class AccountImportRequest(BaseModel):
    provider: Literal["lichess", "chesscom"]
    username: str
    max_games: int = 20
    analysis_strength: Literal["quick", "normal", "deep"] = "normal"

def current_user_id(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> str:
    try:
        scheme, token = authorization.split(' ', 1)
        if scheme.lower() != 'bearer':
            raise ValueError
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get('type') != 'access':
            raise ValueError
        user_id = str(payload['sub'])
    except Exception as exc:
        raise HTTPException(status_code=401, detail='Invalid access token') from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail='Account not found')
    if user.is_suspended:
        raise HTTPException(status_code=403, detail='Account suspended')
    return user_id

@router.post('/import', status_code=202)
async def import_games(request: Request, pgn_text: str | None = Form(default=None), file: UploadFile | None = File(default=None),
                       player_name: str | None = Form(default=None),
                       analysis_strength: str = Form(default="normal"),
                       user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    enforce_rate_limit(request, GAME_IMPORT_LIMIT, subject=user_id)
    if not pgn_text and not file:
        raise HTTPException(400, 'Provide PGN text or file')
    if file:
        raw = await file.read(settings.max_pgn_bytes + 1)
        if len(raw) > settings.max_pgn_bytes: raise HTTPException(413, 'PGN too large')
        pgn_text = raw.decode('utf-8', errors='strict')
    try:
        selected_profile = analysis_profile(analysis_strength)
    except ValueError as exc:
        raise HTTPException(422, 'analysis_strength must be quick, normal, or deep') from exc
    parsed = parse_pgn_many(pgn_text or '')
    if not parsed: raise HTTPException(422, 'No valid games found')
    imported = []
    for item in parsed:
        existing = db.scalar(select(Game).where(Game.user_id == user_id, Game.fingerprint == item.fingerprint))
        if existing:
            link_game_players(db, game=existing, user_id=user_id, explicit_name=player_name,
                              white_rating=item.headers.get('WhiteElo'), black_rating=item.headers.get('BlackElo'))
            db.commit()
            imported.append({'game_id': existing.id, 'duplicate': True}); continue
        h = item.headers
        game = Game(user_id=user_id, fingerprint=item.fingerprint, pgn=item.pgn,
                    event=h.get('Event'), site=h.get('Site'), white_name=h.get('White'), black_name=h.get('Black'),
                    result=h.get('Result'), eco=h.get('ECO'), opening=h.get('Opening'), variation=h.get('Variation'),
                    time_control=h.get('TimeControl'), played_at=item.played_at)
        db.add(game); db.flush()
        link_game_players(db, game=game, user_id=user_id, explicit_name=player_name,
                          white_rating=h.get('WhiteElo'), black_rating=h.get('BlackElo'))
        for m in item.moves:
            db.add(Move(game_id=game.id, ply=m.ply, san=m.san, uci=m.uci, fen_before=m.fen_before,
                        fen_after=m.fen_after, clock_seconds=m.clock_seconds))
        job = AnalysisJob(user_id=user_id, game_id=game.id, status='queued', progress=0)
        db.add(job); db.commit()
        analyze_game.delay(game.id, job.id, selected_profile.name)
        imported.append({'game_id': game.id, 'job_id': job.id, 'duplicate': False})
    return {'count': len(imported), 'games': imported}

@router.post('/import/account', status_code=202)
async def import_account_games(
    payload: AccountImportRequest,
    request: Request,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, GAME_IMPORT_LIMIT, subject=user_id)
    if not 1 <= payload.max_games <= 50:
        raise HTTPException(422, 'max_games must be between 1 and 50')
    try:
        username = normalize_username(payload.username)
        selected_profile = analysis_profile(payload.analysis_strength)
        pgn_text = await fetch_provider_games(
            payload.provider,
            username,
            max_games=payload.max_games,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProviderImportError as exc:
        raise HTTPException(502, str(exc)) from exc

    parsed = parse_pgn_many(pgn_text)
    if not parsed:
        raise HTTPException(422, 'No importable games were returned by the provider')

    account = db.scalar(
        select(ConnectedAccount).where(
            ConnectedAccount.provider == payload.provider,
            ConnectedAccount.provider_user_id == username.lower(),
        )
    )
    if account is not None and account.user_id != user_id:
        raise HTTPException(409, 'This chess account is already connected to another user')
    if account is None:
        account = ConnectedAccount(
            user_id=user_id,
            provider=payload.provider,
            provider_user_id=username.lower(),
            handle=username,
        )
        db.add(account)
    else:
        account.handle = username

    imported = []
    for item in parsed:
        existing = db.scalar(
            select(Game).where(
                Game.user_id == user_id,
                Game.fingerprint == item.fingerprint,
            )
        )
        if existing:
            link_game_players(
                db,
                game=existing,
                user_id=user_id,
                explicit_name=username,
                white_rating=item.headers.get('WhiteElo'),
                black_rating=item.headers.get('BlackElo'),
            )
            db.commit()
            imported.append({'game_id': existing.id, 'duplicate': True})
            continue

        h = item.headers
        game = Game(
            user_id=user_id,
            fingerprint=item.fingerprint,
            pgn=item.pgn,
            source=payload.provider,
            event=h.get('Event'),
            site=h.get('Site'),
            white_name=h.get('White'),
            black_name=h.get('Black'),
            result=h.get('Result'),
            eco=h.get('ECO'),
            opening=h.get('Opening'),
            variation=h.get('Variation'),
            time_control=h.get('TimeControl'),
            played_at=item.played_at,
        )
        db.add(game)
        db.flush()
        link_game_players(
            db,
            game=game,
            user_id=user_id,
            explicit_name=username,
            white_rating=h.get('WhiteElo'),
            black_rating=h.get('BlackElo'),
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
        job = AnalysisJob(user_id=user_id, game_id=game.id, status='queued', progress=0)
        db.add(job)
        db.commit()
        analyze_game.delay(game.id, job.id, selected_profile.name)
        imported.append({'game_id': game.id, 'job_id': job.id, 'duplicate': False})

    return {
        'provider': payload.provider,
        'username': username,
        'count': len(imported),
        'games': imported,
    }


@router.get('')
def list_games(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
    source: str | None = None,
):
    query = select(Game).where(Game.user_id == user_id)
    if source:
        query = query.where(Game.source == source)
    rows = db.scalars(
        query.order_by(Game.created_at.desc()).offset(offset).limit(min(limit, 100))
    ).all()
    result = []
    for g in rows:
        player = db.scalar(select(GamePlayer).where(GamePlayer.game_id == g.id, GamePlayer.user_id == user_id))
        result.append({
            'id': g.id,
            'white': g.white_name,
            'black': g.black_name,
            'result': g.result,
            'eco': g.eco,
            'opening': g.opening,
            'variation': g.variation,
            'time_control': g.time_control,
            'analyzed': g.analyzed,
            'player_color': player.color if player else None,
            'source': g.source,
        })
    return result

@router.get('/{game_id}/analysis')
def game_analysis(game_id: str, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    game = db.scalar(select(Game).where(Game.id == game_id, Game.user_id == user_id))
    if not game: raise HTTPException(404, 'Game not found')
    moves = db.scalars(select(Move).where(Move.game_id == game_id).order_by(Move.ply)).all()
    out = []
    for m in moves:
        a = db.scalar(select(EngineAnalysis).where(EngineAnalysis.move_id == m.id))
        out.append({'move_id': m.id, 'ply': m.ply, 'san': m.san, 'uci': m.uci, 'fen_before': m.fen_before, 'fen_after': m.fen_after,
                    'analysis': None if not a else {'before_cp': a.eval_before_cp, 'after_cp': a.eval_after_cp,
                    'cpl': a.centipawn_loss, 'classification': a.classification, 'best_move': a.best_move_uci, 'pv': a.pv_uci,
                    'depth': a.depth, 'profile': a.analysis_profile,
                    'candidates': json.loads(a.candidate_moves_json) if a.candidate_moves_json else []}})
    player = db.scalar(select(GamePlayer).where(
        GamePlayer.game_id == game.id,
        GamePlayer.user_id == user_id,
    ))
    player_color = player.color if player else None

    endgame_start = None
    for move in moves:
        if classify_endgame(move.fen_after):
            endgame_start = move.ply + 1
            break

    phase_cpl = {"opening": [], "middlegame": [], "endgame": []}
    critical_moments = []
    strongest_moves = []
    missed_wins = 0
    defensive_mistakes = 0

    for move in moves:
        analysis = db.scalar(select(EngineAnalysis).where(EngineAnalysis.move_id == move.id))
        if analysis is None or player_color is None:
            continue
        is_player_move = (
            (move.ply % 2 == 1 and player_color == "white")
            or (move.ply % 2 == 0 and player_color == "black")
        )
        if not is_player_move:
            continue

        cpl = analysis.centipawn_loss or 0
        if move.ply <= 20:
            phase = "opening"
        elif endgame_start is not None and move.ply >= endgame_start:
            phase = "endgame"
        else:
            phase = "middlegame"
        phase_cpl[phase].append(cpl)

        if analysis.classification in {"inaccuracy", "mistake", "blunder"}:
            critical_moments.append({
                "move_id": move.id,
                "ply": move.ply,
                "san": move.san,
                "classification": analysis.classification,
                "cpl": cpl,
            })
        if analysis.classification in {"best", "excellent"}:
            strongest_moves.append({
                "move_id": move.id,
                "ply": move.ply,
                "san": move.san,
                "classification": analysis.classification,
                "cpl": cpl,
            })
        if (
            analysis.eval_before_cp is not None
            and analysis.eval_after_cp is not None
            and analysis.eval_before_cp >= 180
            and analysis.eval_after_cp <= 0
        ):
            missed_wins += 1
        if (
            analysis.eval_before_cp is not None
            and analysis.eval_before_cp <= -120
            and cpl >= 80
        ):
            defensive_mistakes += 1

    critical_moments.sort(key=lambda item: item["cpl"], reverse=True)
    strongest_moves.sort(key=lambda item: (item["cpl"], item["ply"]))

    summary = {
        "phase_accuracy": {
            phase: accuracy_from_cpl(values) if values else None
            for phase, values in phase_cpl.items()
        },
        "critical_moments": critical_moments[:6],
        "biggest_mistake": critical_moments[0] if critical_moments else None,
        "strongest_moves": strongest_moves[:6],
        "missed_wins": missed_wins,
        "defensive_mistakes": defensive_mistakes,
    }

    return {
        'game_id': game.id,
        'analyzed': game.analyzed,
        'game': {
            'white': game.white_name,
            'black': game.black_name,
            'result': game.result,
            'eco': game.eco,
            'opening': game.opening,
            'variation': game.variation,
            'time_control': game.time_control,
            'player_color': player_color,
        },
        'summary': summary,
        'moves': out,
    }


@router.post('/{game_id}/player', status_code=202)
def identify_player(
    game_id: str,
    payload: IdentifyPlayerRequest,
    request: Request,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, REANALYSIS_LIMIT, subject=user_id)
    game = db.scalar(select(Game).where(Game.id == game_id, Game.user_id == user_id))
    if not game:
        raise HTTPException(404, 'Game not found')

    players = {
        player.color: player
        for player in db.scalars(select(GamePlayer).where(GamePlayer.game_id == game.id)).all()
    }
    for color, name in [('white', game.white_name), ('black', game.black_name)]:
        if color not in players:
            players[color] = GamePlayer(game_id=game.id, color=color, name=name)
            db.add(players[color])
    selected = players[payload.color]
    selected.user_id = user_id
    other_color = 'black' if payload.color == 'white' else 'white'
    if players[other_color].user_id == user_id:
        players[other_color].user_id = None

    job = AnalysisJob(user_id=user_id, game_id=game.id, status='queued', progress=0)
    db.add(job)
    db.commit()
    analyze_game.delay(game.id, job.id)
    return {'game_id': game.id, 'player_color': payload.color, 'job_id': job.id}
