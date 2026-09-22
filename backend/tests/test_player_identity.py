from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import Game, Profile, User
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
