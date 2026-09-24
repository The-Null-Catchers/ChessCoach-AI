from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import AuthActionToken, User


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_action_token(db: Session, *, user_id: str, purpose: str) -> str:
    now = _now()
    for existing in db.scalars(
        select(AuthActionToken).where(
            AuthActionToken.user_id == user_id,
            AuthActionToken.purpose == purpose,
            AuthActionToken.consumed_at.is_(None),
        )
    ):
        existing.consumed_at = now

    raw = secrets.token_urlsafe(32)
    db.add(
        AuthActionToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=_hash_token(raw),
            expires_at=now + timedelta(minutes=settings.auth_action_token_minutes),
        )
    )
    db.flush()
    return raw


def consume_action_token(db: Session, *, token: str, purpose: str) -> User | None:
    now = _now()
    row = db.scalar(
        select(AuthActionToken).where(
            AuthActionToken.token_hash == _hash_token(token),
            AuthActionToken.purpose == purpose,
        )
    )
    if row is None or row.consumed_at is not None or row.expires_at <= now:
        return None

    user = db.get(User, row.user_id)
    if user is None:
        return None

    row.consumed_at = now
    db.flush()
    return user
