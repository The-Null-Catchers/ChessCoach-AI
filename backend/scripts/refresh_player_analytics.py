"""Rebuild a player's stored summaries from existing analysis."""

import argparse

from app.db.session import SessionLocal
from app.models.entities import User
from app.services.player_analytics import recompute_player_analytics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user_id")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        if db.get(User, args.user_id) is None:
            parser.error("User ID not found")
        recompute_player_analytics(db, args.user_id)


if __name__ == "__main__":
    main()
