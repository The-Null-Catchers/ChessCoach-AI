from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import AuditLog, Profile, User
from app.schemas.auth import AuthMessage, LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, TokenPair
from app.services.auth_sessions import (
    InvalidRefreshToken,
    RefreshReuseDetected,
    issue_session_tokens,
    revoke_all_user_sessions,
    revoke_refresh_family,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _access_user_id(authorization: str = Header(...)) -> str:
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError
        return str(decode_token(token, expected_type="access")["sub"])
    except (ValueError, KeyError, jwt.PyJWTError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc


@router.post("/register", response_model=TokenPair, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(payload.password))
    user.profile = Profile(display_name=payload.display_name)
    db.add(user)
    db.flush()
    access, refresh = issue_session_tokens(db, user_id=user.id)
    db.add(AuditLog(user_id=user.id, action="auth.register", entity_type="user", entity_id=user.id))
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access, refresh = issue_session_tokens(db, user_id=user.id)
    db.add(AuditLog(user_id=user.id, action="auth.login", entity_type="user", entity_id=user.id))
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        access, refresh_token = rotate_refresh_token(db, payload.refresh_token)
    except RefreshReuseDetected as exc:
        raise HTTPException(status_code=401, detail="Refresh token reuse detected; session revoked") from exc
    except InvalidRefreshToken as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.post("/logout", response_model=AuthMessage)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    try:
        revoke_refresh_family(db, payload.refresh_token)
    except InvalidRefreshToken as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    return AuthMessage(detail="Logged out")


@router.post("/logout-all", response_model=AuthMessage)
def logout_all(
    user_id: str = Depends(_access_user_id),
    db: Session = Depends(get_db),
):
    revoke_all_user_sessions(db, user_id)
    return AuthMessage(detail="All sessions revoked")
