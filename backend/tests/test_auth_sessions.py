from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import AuditLog, RefreshSession


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


def test_refresh_rotation_detects_reuse_and_revokes_family():
    client, testing_session = _client()
    try:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "email": "rotation@example.com",
                "password": "very-secure-password",
                "display_name": "Rotation",
            },
        )
        assert registered.status_code == 201
        first_refresh = registered.json()["refresh_token"]

        rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
        assert rotated.status_code == 200
        second_refresh = rotated.json()["refresh_token"]
        assert second_refresh != first_refresh

        replay = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
        assert replay.status_code == 401
        assert "reuse" in replay.json()["detail"].lower()

        family_revoked = client.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh})
        assert family_revoked.status_code == 401

        with testing_session() as db:
            assert all(row.revoked_at is not None for row in db.scalars(select(RefreshSession)).all())
            actions = {row.action for row in db.scalars(select(AuditLog)).all()}
            assert "auth.refresh_rotated" in actions
            assert "auth.refresh_reuse_detected" in actions
    finally:
        app.dependency_overrides.clear()


def test_logout_all_revokes_refresh_sessions():
    client, testing_session = _client()
    try:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com",
                "password": "another-secure-password",
                "display_name": "Logout",
            },
        )
        assert registered.status_code == 201
        tokens = registered.json()

        response = client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200

        rejected = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert rejected.status_code == 401

        with testing_session() as db:
            assert all(row.revoked_at is not None for row in db.scalars(select(RefreshSession)).all())
            assert "auth.logout_all" in {row.action for row in db.scalars(select(AuditLog)).all()}
    finally:
        app.dependency_overrides.clear()
