from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import Game, GamePlayer, Profile, User
from app.services.player_identity import link_game_players


def test_links_profile_name_to_correct_color():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="alice@example.com", password_hash="test")
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id, display_name="Alice"))
        game = Game(
            user_id=user.id,
            fingerprint="a" * 64,
            pgn="1. e4 e5 *",
            white_name="Alice",
            black_name="Bob",
            result="*",
        )
        db.add(game)
        db.flush()
        white, black = link_game_players(db, game=game, user_id=user.id)
        assert white.user_id == user.id
        assert black.user_id is None


def test_ambiguous_alias_never_links_both_colors():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="same@example.com", password_hash="test")
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id, display_name="SameName"))
        game = Game(
            user_id=user.id,
            fingerprint="b" * 64,
            pgn="1. e4 e5 *",
            white_name="SameName",
            black_name="SameName",
            result="*",
        )
        db.add(game)
        db.flush()
        white, black = link_game_players(db, game=game, user_id=user.id)
        assert white.user_id is None
        assert black.user_id is None


def test_existing_single_player_link_is_preserved():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="manual@example.com", password_hash="test")
        db.add(user)
        db.flush()
        game = Game(
            user_id=user.id,
            fingerprint="c" * 64,
            pgn="1. e4 e5 *",
            white_name="White",
            black_name="Black",
            result="*",
        )
        db.add(game)
        db.flush()
        db.add(GamePlayer(game_id=game.id, user_id=user.id, color="black", name="Black"))
        db.flush()
        white, black = link_game_players(db, game=game, user_id=user.id)
        assert white.user_id is None
        assert black.user_id == user.id
