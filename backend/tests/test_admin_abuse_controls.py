from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password, make_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import AuditLog, RefreshSession, User
from app.services.auth_sessions import issue_session_tokens


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


def test_admin_can_suspend_user_and_revoke_sessions(monkeypatch):
    client, sessions = _client()
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    try:
        with sessions() as db:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("admin-password-123"),
                is_admin=True,
            )
            user = User(
                email="member@example.com",
                password_hash=hash_password("member-password-123"),
            )
            db.add_all([admin, user])
            db.flush()
            issue_session_tokens(db, user_id=user.id)
            admin_id, user_id = admin.id, user.id
            db.commit()

        token = make_access_token(admin_id)
        response = client.post(
            f"/api/v1/admin/users/{user_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "automated abuse threshold exceeded"},
        )
        assert response.status_code == 200

        with sessions() as db:
            user = db.get(User, user_id)
            assert user.is_suspended is True
            assert user.suspension_reason == "automated abuse threshold exceeded"
            assert all(
                row.revoked_at is not None
                for row in db.scalars(select(RefreshSession).where(RefreshSession.user_id == user_id)).all()
            )
            actions = {row.action for row in db.scalars(select(AuditLog)).all()}
            assert "admin.user_suspended" in actions

        blocked = client.get(
            "/api/v1/games",
            headers={"Authorization": f"Bearer {make_access_token(user_id)}"},
        )
        assert blocked.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_non_admin_cannot_access_admin_overview():
    client, sessions = _client()
    try:
        with sessions() as db:
            user = User(
                email="member@example.com",
                password_hash=hash_password("member-password-123"),
            )
            db.add(user)
            db.flush()
            user_id = user.id
            db.commit()

        response = client.get(
            "/api/v1/admin/overview",
            headers={"Authorization": f"Bearer {make_access_token(user_id)}"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
