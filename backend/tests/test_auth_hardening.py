from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import AuditLog, AuthActionToken, RefreshSession, User
from app.services.auth_action_tokens import consume_action_token, issue_action_token


def _client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def test_action_token_is_one_time_and_hashed():
    _, testing_session = _client()
    try:
        with testing_session() as db:
            user = User(email="token@example.com", password_hash=hash_password("very-secure-password"))
            db.add(user)
            db.flush()
            raw = issue_action_token(db, user_id=user.id, purpose="verify_email")
            db.commit()

            stored = db.scalar(select(AuthActionToken))
            assert stored is not None
            assert stored.token_hash != raw
            assert len(stored.token_hash) == 64

            consumed_user = consume_action_token(db, token=raw, purpose="verify_email")
            assert consumed_user is not None
            assert consume_action_token(db, token=raw, purpose="verify_email") is None
    finally:
        app.dependency_overrides.clear()


def test_password_reset_changes_password_and_revokes_sessions(monkeypatch):
    client, testing_session = _client()
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr("app.api.auth.send_auth_email.delay", lambda *args, **kwargs: None)
    try:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset@example.com",
                "password": "old-secure-password",
                "display_name": "Reset",
            },
        )
        assert registered.status_code == 201
        refresh_token = registered.json()["refresh_token"]

        with testing_session() as db:
            user = db.scalar(select(User).where(User.email == "reset@example.com"))
            raw = issue_action_token(db, user_id=user.id, purpose="password_reset")
            db.commit()

        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw, "new_password": "new-secure-password"},
        )
        assert response.status_code == 200

        with testing_session() as db:
            user = db.scalar(select(User).where(User.email == "reset@example.com"))
            assert verify_password("new-secure-password", user.password_hash)
            assert all(row.revoked_at is not None for row in db.scalars(select(RefreshSession)).all())
            actions = {row.action for row in db.scalars(select(AuditLog)).all()}
            assert "auth.password_reset_completed" in actions

        rejected = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert rejected.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_email_verification_marks_user_verified(monkeypatch):
    client, testing_session = _client()
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr("app.api.auth.send_auth_email.delay", lambda *args, **kwargs: None)
    try:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "verify@example.com",
                "password": "very-secure-password",
                "display_name": "Verify",
            },
        )
        with testing_session() as db:
            user = db.scalar(select(User).where(User.email == "verify@example.com"))
            raw = issue_action_token(db, user_id=user.id, purpose="verify_email")
            db.commit()

        response = client.post("/api/v1/auth/verify-email/confirm", json={"token": raw})
        assert response.status_code == 200

        with testing_session() as db:
            user = db.scalar(select(User).where(User.email == "verify@example.com"))
            assert user.is_verified is True
    finally:
        app.dependency_overrides.clear()


def test_password_reset_request_does_not_reveal_account_existence(monkeypatch):
    client, _ = _client()
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr("app.api.auth.send_auth_email.delay", lambda *args, **kwargs: None)
    try:
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "missing@example.com"},
        )
        assert response.status_code == 200
        assert "If an account exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
