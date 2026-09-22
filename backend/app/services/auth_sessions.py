from __future__ import annotations

from datetime import datetime
import hashlib
import json
import uuid

import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import decode_token, make_access_token, make_refresh_token
from app.models.entities import AuditLog, RefreshSession


class InvalidRefreshToken(Exception):
    pass


class RefreshReuseDetected(InvalidRefreshToken):
    pass


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def _audit(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    metadata: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type="auth_session",
            metadata_json=json.dumps(metadata, sort_keys=True) if metadata else None,
        )
    )


def _claims(refresh_token: str) -> tuple[str, str, str]:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = str(payload["sub"])
        jti = str(payload["jti"])
        family_id = str(payload["fid"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidRefreshToken from exc
    if not user_id or not jti or not family_id:
        raise InvalidRefreshToken
    return user_id, jti, family_id


def issue_session_tokens(
    db: Session,
    *,
    user_id: str,
    family_id: str | None = None,
) -> tuple[str, str]:
    family = family_id or str(uuid.uuid4())
    refresh_token, jti, expires_at = make_refresh_token(user_id, family_id=family)
    db.add(
        RefreshSession(
            user_id=user_id,
            family_id=family,
            jti_hash=_hash_jti(jti),
            expires_at=expires_at.replace(tzinfo=None),
        )
    )
    return make_access_token(user_id), refresh_token


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    user_id, jti, family_id = _claims(refresh_token)
    session = db.scalar(
        select(RefreshSession).where(RefreshSession.jti_hash == _hash_jti(jti))
    )
    if session is None or session.user_id != user_id or session.family_id != family_id:
        raise InvalidRefreshToken

    now = datetime.utcnow()
    if session.revoked_at is not None:
        db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        _audit(
            db,
            user_id=user_id,
            action="auth.refresh_reuse_detected",
            metadata={"family_id": family_id},
        )
        db.commit()
        raise RefreshReuseDetected

    if session.expires_at <= now:
        session.revoked_at = now
        _audit(db, user_id=user_id, action="auth.refresh_expired")
        db.commit()
        raise InvalidRefreshToken

    access_token, new_refresh = issue_session_tokens(
        db,
        user_id=user_id,
        family_id=family_id,
    )
    db.flush()
    replacement = db.scalar(
        select(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.family_id == family_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.id != session.id,
        )
        .order_by(RefreshSession.created_at.desc())
    )
    session.revoked_at = now
    session.last_used_at = now
    session.replaced_by_id = replacement.id if replacement else None
    _audit(db, user_id=user_id, action="auth.refresh_rotated")
    db.commit()
    return access_token, new_refresh


def revoke_refresh_family(db: Session, refresh_token: str) -> str:
    user_id, jti, family_id = _claims(refresh_token)
    session = db.scalar(
        select(RefreshSession).where(RefreshSession.jti_hash == _hash_jti(jti))
    )
    if session is None or session.user_id != user_id or session.family_id != family_id:
        raise InvalidRefreshToken

    now = datetime.utcnow()
    db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.family_id == family_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    _audit(db, user_id=user_id, action="auth.logout", metadata={"family_id": family_id})
    db.commit()
    return user_id


def revoke_all_user_sessions(db: Session, user_id: str) -> None:
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.utcnow())
    )
    _audit(db, user_id=user_id, action="auth.logout_all")
    db.commit()
