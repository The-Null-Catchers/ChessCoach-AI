from __future__ import annotations

import os

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import Game, User

DEMO_EMAIL = os.getenv("PORTFOLIO_DEMO_EMAIL", "").strip().lower()
ALLOW_ADMIN = os.getenv("ALLOW_PORTFOLIO_DEMO_ADMIN", "").lower() in {"1", "true", "yes"}


def enable_demo_admin() -> None:
    if not ALLOW_ADMIN:
        raise SystemExit(
            "Refusing to grant admin access. Set ALLOW_PORTFOLIO_DEMO_ADMIN=true explicitly."
        )
    if not DEMO_EMAIL:
        raise SystemExit("PORTFOLIO_DEMO_EMAIL is required.")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            raise SystemExit("Portfolio demo account does not exist. Run the demo seed first.")

        demo_game = db.scalar(
            select(Game.id)
            .where(Game.user_id == user.id, Game.source == "portfolio_demo")
            .limit(1)
        )
        if demo_game is None:
            raise SystemExit(
                "Refusing to grant admin access because the account is not a seeded portfolio demo account."
            )

        if user.is_admin:
            print(f"Portfolio demo admin already enabled for {DEMO_EMAIL}")
            return

        user.is_admin = True
        db.commit()
        print(f"Enabled portfolio demo admin access for {DEMO_EMAIL}")


if __name__ == "__main__":
    enable_demo_admin()
