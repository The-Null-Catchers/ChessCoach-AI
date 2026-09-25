from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import (
    LOGIN_LIMIT,
    PASSWORD_RESET_LIMIT,
    REGISTER_LIMIT,
    VERIFY_LIMIT,
    enforce_rate_limit,
)
from app.core.security import decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import AuditLog, Profile, User
from app.schemas.auth import (
    ActionTokenRequest,
    AuthMessage,
    EmailVerificationRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.services.auth_action_tokens import consume_action_token, issue_action_token
from app.services.auth_sessions import (
    InvalidRefreshToken,
    RefreshReuseDetected,
    issue_session_tokens,
    revoke_all_user_sessions,
    revoke_refresh_family,
    rotate_refresh_token,
)
from app.tasks.email import send_auth_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _access_user_id(authorization: str = Header(...)) -> str:
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError
        return str(decode_token(token, expected_type="access")["sub"])
    except (ValueError, KeyError, jwt.PyJWTError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc


def _verification_email(email: str, token: str) -> None:
    if not settings.smtp_host:
        return
    link = f"{settings.frontend_url.rstrip('/')}/verify-email?token={token}"
    send_auth_email.delay(
        email,
        "Verify your ChessCoach AI email",
        f"Verify your ChessCoach AI account:\n\n{link}\n\nThis link expires soon and can only be used once.",
    )


def _password_reset_email(email: str, token: str) -> None:
    if not settings.smtp_host:
        return
    link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    send_auth_email.delay(
        email,
        "Reset your ChessCoach AI password",
        f"Reset your ChessCoach AI password:\n\n{link}\n\nIf you did not request this, ignore this email.",
    )


@router.post("/register", response_model=TokenPair, status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request, REGISTER_LIMIT)
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(payload.password))
    user.profile = Profile(display_name=payload.display_name)
    db.add(user)
    db.flush()
    verification_token = issue_action_token(db, user_id=user.id, purpose="verify_email")
    access, refresh = issue_session_tokens(db, user_id=user.id)
    db.add(AuditLog(user_id=user.id, action="auth.register", entity_type="user", entity_id=user.id))
    db.add(AuditLog(user_id=user.id, action="auth.verification_issued", entity_type="user", entity_id=user.id))
    db.commit()
    _verification_email(user.email, verification_token)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request, LOGIN_LIMIT)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.is_suspended:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

    access, refresh = issue_session_tokens(db, user_id=user.id)
    db.add(AuditLog(user_id=user.id, action="auth.login", entity_type="user", entity_id=user.id))
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/verify-email/request", response_model=AuthMessage)
def request_email_verification(
    payload: EmailVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, VERIFY_LIMIT)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user and not user.is_verified:
        token = issue_action_token(db, user_id=user.id, purpose="verify_email")
        db.add(AuditLog(user_id=user.id, action="auth.verification_issued", entity_type="user", entity_id=user.id))
        db.commit()
        _verification_email(user.email, token)
    return AuthMessage(detail="If the account is eligible, a verification email has been sent")


@router.post("/verify-email/confirm", response_model=AuthMessage)
def confirm_email_verification(
    payload: ActionTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, VERIFY_LIMIT)
    user = consume_action_token(db, token=payload.token, purpose="verify_email")
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user.is_verified = True
    db.add(AuditLog(user_id=user.id, action="auth.email_verified", entity_type="user", entity_id=user.id))
    db.commit()
    return AuthMessage(detail="Email verified")


@router.post("/password-reset/request", response_model=AuthMessage)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, PASSWORD_RESET_LIMIT)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user:
        token = issue_action_token(db, user_id=user.id, purpose="password_reset")
        db.add(AuditLog(user_id=user.id, action="auth.password_reset_issued", entity_type="user", entity_id=user.id))
        db.commit()
        _password_reset_email(user.email, token)
    return AuthMessage(detail="If an account exists for that email, a reset link has been sent")


@router.post("/password-reset/confirm", response_model=AuthMessage)
def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, PASSWORD_RESET_LIMIT)
    user = consume_action_token(db, token=payload.token, purpose="password_reset")
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
    user.password_hash = hash_password(payload.new_password)
    revoke_all_user_sessions(db, user.id)
    db.add(AuditLog(user_id=user.id, action="auth.password_reset_completed", entity_type="user", entity_id=user.id))
    db.commit()
    return AuthMessage(detail="Password updated; sign in again")


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
