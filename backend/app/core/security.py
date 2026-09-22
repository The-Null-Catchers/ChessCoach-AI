from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_token(
    user_id: str,
    token_type: str,
    expires: timedelta,
    *,
    extra_claims: dict[str, str] | None = None,
) -> str:
    now = _now()
    payload: dict[str, object] = {
        "sub": user_id,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def make_access_token(user_id: str) -> str:
    return make_token(user_id, "access", timedelta(minutes=settings.access_token_minutes))


def make_refresh_token(
    user_id: str,
    *,
    family_id: str,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    token_jti = jti or str(uuid.uuid4())
    expires_at = _now() + timedelta(days=settings.refresh_token_days)
    token = make_token(
        user_id,
        "refresh",
        timedelta(days=settings.refresh_token_days),
        extra_claims={"jti": token_jti, "fid": family_id},
    )
    return token, token_jti, expires_at


def decode_token(token: str, *, expected_type: str) -> dict[str, object]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload


def token_pair(user_id: str) -> tuple[str, str]:
    """Backward-compatible stateless helper.

    Auth endpoints use the persisted refresh-session service instead so refresh
    rotation and replay detection remain enforceable.
    """
    family_id = str(uuid.uuid4())
    refresh, _, _ = make_refresh_token(user_id, family_id=family_id)
    return make_access_token(user_id), refresh
