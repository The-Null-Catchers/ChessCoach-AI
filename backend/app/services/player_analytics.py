from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime
from statistics import median

import chess
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import (
    EndgameStat,
    EngineAnalysis,
    Game,
    GamePlayer,
    Mistake,
    Move,
    OpeningStat,
    PlayerInsight,
    PlayerWeakness,
)
from app.services.player_identity import backfill_owned_games


ERROR_CLASSES = {"inaccuracy", "mistake", "blunder"}


def accuracy_from_cpl(values: list[int]) -> float:
    if not values:
        return 0.0
    mean_cpl = sum(min(max(value, 0), 1000) for value in values) / len(values)
    return round(100.0 * math.exp(-mean_cpl / 350.0), 2)


def _is_player_ply(ply: int, color: str) -> bool:
    return (ply % 2 == 1 and color == "white") or (ply % 2 == 0 and color == "black")


def _analysis_rows(db: Session, game_id: str, color: str, start_ply: int = 1, end_ply: int | None = None):
    query = (
        select(Move, EngineAnalysis)
        .join(EngineAnalysis, EngineAnalysis.move_id == Move.id)
        .where(Move.game_id == game_id, Move.ply >= start_ply)
        .order_by(Move.ply)
    )
    if end_ply is not None:
        query = query.where(Move.ply <= end_ply)
    return [(move, analysis) for move, analysis in db.execute(query).all() if _is_player_ply(move.ply, color)]


def _score_for_result(result: str | None, color: str) -> float:
    if result == "1/2-1/2":
        return 0.5
    if result == "1-0":
        return 1.0 if color == "white" else 0.0
    if result == "0-1":
        return 1.0 if color == "black" else 0.0
    return 0.0


def classify_endgame(fen: str) -> str | None:
    board = chess.Board(fen)
    non_kings = [piece for piece in board.piece_map().values() if piece.piece_type != chess.KING]
    if len(non_kings) > 12:
        return None
    queens = sum(piece.piece_type == chess.QUEEN for piece in non_kings)
    rooks = sum(piece.piece_type == chess.ROOK for piece in non_kings)
    minors = sum(piece.piece_type in {chess.BISHOP, chess.KNIGHT} for piece in non_kings)
    pawns = sum(piece.piece_type == chess.PAWN for piece in non_kings)
    if pawns and queens == 0 and rooks == 0 and minors == 0:
        return "king_pawn"
    if rooks and queens == 0:
        return "rook_endgame"
    if queens:
        return "queen_endgame"
    if minors and rooks == 0:
        return "minor_piece_endgame"
    return "mixed_endgame"


def _endgame_entry(db: Session, game_id: str) -> tuple[str, int] | None:
    moves = db.scalars(select(Move).where(Move.game_id == game_id).order_by(Move.ply)).all()
    for move in moves:
        category = classify_endgame(move.fen_after)
        if category:
            return category, move.ply + 1
    return None


def recompute_player_analytics(db: Session, user_id: str) -> None:
    backfill_owned_games(db, user_id)
    db.flush()

    linked = db.execute(
        select(Game, GamePlayer)
        .join(GamePlayer, GamePlayer.game_id == Game.id)
        .where(GamePlayer.user_id == user_id, Game.analyzed.is_(True))
        .order_by(Game.played_at.asc().nulls_last(), Game.created_at.asc())
    ).all()

    db.execute(delete(OpeningStat).where(OpeningStat.user_id == user_id))
    db.execute(delete(EndgameStat).where(EndgameStat.user_id == user_id))
    db.execute(delete(PlayerInsight).where(PlayerInsight.user_id == user_id))

    opening_groups: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    endgame_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    color_scores: dict[str, list[float]] = defaultdict(list)

    for game, player in linked:
        color = player.color
        opening_rows = _analysis_rows(db, game.id, color, end_ply=20)
        opening_cpl = [a.centipawn_loss or 0 for _, a in opening_rows]
        first_error = next((m.ply for m, a in opening_rows if a.classification in ERROR_CLASSES), None)
        opening_key = (game.eco or "", game.opening or "Unknown opening", game.variation or "", color)
        opening_groups[opening_key].append({
            "accuracy": accuracy_from_cpl(opening_cpl),
            "score": _score_for_result(game.result, color),
            "first_error": first_error,
        })
        color_scores[color].append(_score_for_result(game.result, color))

        entry = _endgame_entry(db, game.id)
        if entry:
            category, start_ply = entry
            rows = _analysis_rows(db, game.id, color, start_ply=start_ply)
            if rows:
                cpl = [a.centipawn_loss or 0 for _, a in rows]
                errors = sum(a.classification in ERROR_CLASSES for _, a in rows)
                endgame_groups[category].append({
                    "accuracy": accuracy_from_cpl(cpl),
                    "mistakes": errors,
                })

    opening_stats: list[OpeningStat] = []
    for (eco, opening, variation, color), samples in opening_groups.items():
        scores = [float(sample["score"]) for sample in samples]
        errors = [int(sample["first_error"]) for sample in samples if sample["first_error"] is not None]
        wins = sum(score == 1.0 for score in scores)
        draws = sum(score == 0.5 for score in scores)
        stat = OpeningStat(
            user_id=user_id,
            eco=eco or None,
            opening=opening,
            variation=variation or None,
            color=color,
            games_count=len(samples),
            wins=wins,
            draws=draws,
            losses=len(samples) - wins - draws,
            avg_accuracy=round(sum(float(s["accuracy"]) for s in samples) / len(samples), 2),
            common_deviation_ply=round(median(errors)) if errors else None,
            updated_at=datetime.utcnow(),
        )
        db.add(stat)
        opening_stats.append(stat)

    endgame_stats: list[EndgameStat] = []
    for category, samples in endgame_groups.items():
        stat = EndgameStat(
            user_id=user_id,
            category=category,
            games_count=len(samples),
            avg_accuracy=round(sum(float(s["accuracy"]) for s in samples) / len(samples), 2),
            mistakes=sum(int(s["mistakes"]) for s in samples),
            updated_at=datetime.utcnow(),
        )
        db.add(stat)
        endgame_stats.append(stat)

    weaknesses = db.scalars(
        select(PlayerWeakness)
        .where(PlayerWeakness.user_id == user_id)
        .order_by(PlayerWeakness.score.desc())
    ).all()
    if weaknesses:
        top = weaknesses[0]
        if top.sample_size >= 3 and top.confidence >= 0.3:
            db.add(PlayerInsight(
                user_id=user_id,
                insight_type="recurring_weakness",
                title=f"{top.category.replace('_', ' ').title()} is recurring",
                body=f"This theme has appeared in {top.sample_size} detected mistakes. It is prioritized in your training queue.",
                confidence=top.confidence,
                evidence_json=json.dumps({"category": top.category, "sample_size": top.sample_size, "score": top.score}),
            ))

    white = color_scores.get("white", [])
    black = color_scores.get("black", [])
    if len(white) >= 5 and len(black) >= 5:
        white_rate = sum(white) / len(white)
        black_rate = sum(black) / len(black)
        gap = white_rate - black_rate
        if abs(gap) >= 0.15:
            stronger = "White" if gap > 0 else "Black"
            db.add(PlayerInsight(
                user_id=user_id,
                insight_type="color_results",
                title=f"Your recent results are stronger with {stronger}",
                body=f"Score rate: White {white_rate:.0%}, Black {black_rate:.0%}, across {len(white) + len(black)} linked games.",
                confidence=min(0.95, 1.0 - math.exp(-(len(white) + len(black)) / 12.0)),
                evidence_json=json.dumps({"white_score_rate": white_rate, "black_score_rate": black_rate}),
            ))

    eligible_endgames = [stat for stat in endgame_stats if stat.games_count >= 3]
    if eligible_endgames:
        weakest = min(eligible_endgames, key=lambda stat: stat.avg_accuracy)
        db.add(PlayerInsight(
            user_id=user_id,
            insight_type="endgame_focus",
            title=f"{weakest.category.replace('_', ' ').title()} needs attention",
            body=f"Average accuracy is {weakest.avg_accuracy:.1f}% across {weakest.games_count} detected endings.",
            confidence=min(0.92, 1.0 - math.exp(-weakest.games_count / 5.0)),
            evidence_json=json.dumps({"category": weakest.category, "games": weakest.games_count, "accuracy": weakest.avg_accuracy}),
        ))

    review_openings = [stat for stat in opening_stats if stat.games_count >= 3]
    if review_openings:
        weakest_opening = min(review_openings, key=lambda stat: stat.avg_accuracy)
        if weakest_opening.avg_accuracy < 82:
            db.add(PlayerInsight(
                user_id=user_id,
                insight_type="opening_focus",
                title=f"Review {weakest_opening.opening}",
                body=f"Your first-20-ply accuracy is {weakest_opening.avg_accuracy:.1f}% across {weakest_opening.games_count} games as {weakest_opening.color}.",
                confidence=min(0.9, 1.0 - math.exp(-weakest_opening.games_count / 5.0)),
                evidence_json=json.dumps({
                    "opening": weakest_opening.opening,
                    "color": weakest_opening.color,
                    "games": weakest_opening.games_count,
                    "accuracy": weakest_opening.avg_accuracy,
                    "deviation_proxy_ply": weakest_opening.common_deviation_ply,
                }),
            ))

    db.flush()


def compute_overview(db: Session, user_id: str) -> dict[str, object]:
    linked = db.execute(
        select(Game, GamePlayer)
        .join(GamePlayer, GamePlayer.game_id == Game.id)
        .where(GamePlayer.user_id == user_id, Game.analyzed.is_(True))
    ).all()

    all_cpl: list[int] = []
    phase_cpl: dict[str, list[int]] = {"opening": [], "middlegame": [], "endgame": []}
    blunders = 0
    mistakes = 0
    games = len(linked)

    for game, player in linked:
        endgame = _endgame_entry(db, game.id)
        endgame_start = endgame[1] if endgame else None
        rows = _analysis_rows(db, game.id, player.color)
        for move, analysis in rows:
            cpl = analysis.centipawn_loss or 0
            all_cpl.append(cpl)
            if analysis.classification == "blunder":
                blunders += 1
            if analysis.classification in {"mistake", "blunder"}:
                mistakes += 1
            if move.ply <= 20:
                phase_cpl["opening"].append(cpl)
            elif endgame_start is not None and move.ply >= endgame_start:
                phase_cpl["endgame"].append(cpl)
            else:
                phase_cpl["middlegame"].append(cpl)

    return {
        "games_analyzed": games,
        "average_centipawn_loss": round(sum(all_cpl) / len(all_cpl), 2) if all_cpl else None,
        "blunders_per_game": round(blunders / games, 2) if games else 0.0,
        "mistakes_per_game": round(mistakes / games, 2) if games else 0.0,
        "accuracy": accuracy_from_cpl(all_cpl) if all_cpl else None,
        "phase_accuracy": {
            phase: accuracy_from_cpl(values) if values else None
            for phase, values in phase_cpl.items()
        },
    }
