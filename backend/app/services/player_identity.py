from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ConnectedAccount, Game, GamePlayer, Profile


def _normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def _rating(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = int(value)
        return parsed if 100 <= parsed <= 4000 else None
    except ValueError:
        return None


def aliases_for_user(db: Session, user_id: str, explicit_name: str | None = None) -> set[str]:
    aliases: set[str] = set()
    if explicit_name:
        aliases.add(_normalize(explicit_name))
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile and profile.display_name:
        aliases.add(_normalize(profile.display_name))
    accounts = db.scalars(select(ConnectedAccount).where(ConnectedAccount.user_id == user_id)).all()
    for account in accounts:
        if account.handle:
            aliases.add(_normalize(account.handle))
    return {alias for alias in aliases if alias}


def link_game_players(
    db: Session,
    *,
    game: Game,
    user_id: str,
    explicit_name: str | None = None,
    white_rating: str | None = None,
    black_rating: str | None = None,
) -> tuple[GamePlayer, GamePlayer]:
    aliases = aliases_for_user(db, user_id, explicit_name)
    specs = [
        ("white", game.white_name, _rating(white_rating)),
        ("black", game.black_name, _rating(black_rating)),
    ]
    linked: list[GamePlayer] = []
    for color, name, rating in specs:
        player = db.scalar(select(GamePlayer).where(
            GamePlayer.game_id == game.id,
            GamePlayer.color == color,
        ))
        matched_user = user_id if _normalize(name) in aliases else None
        if player is None:
            player = GamePlayer(
                game_id=game.id,
                user_id=matched_user,
                color=color,
                name=name,
                rating=rating,
            )
            db.add(player)
        else:
            player.name = name
            player.rating = player.rating or rating
            if matched_user:
                player.user_id = user_id
        linked.append(player)
    db.flush()
    return linked[0], linked[1]


def backfill_owned_games(db: Session, user_id: str) -> None:
    games = db.scalars(select(Game).where(Game.user_id == user_id)).all()
    for game in games:
        link_game_players(db, game=game, user_id=user_id)
