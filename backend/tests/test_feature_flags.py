from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password, make_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import AuditLog, FeatureFlag, User


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


def test_feature_flags_are_publicly_readable_and_admin_managed():
    client, sessions = _client()
    try:
        with sessions() as db:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("admin-password-123"),
                is_admin=True,
            )
            db.add(admin)
            db.flush()
            admin_id = admin.id
            db.commit()

        public = client.get("/api/v1/features")
        assert public.status_code == 200
        assert public.json()["weekly_reports"] is True

        headers = {"Authorization": f"Bearer {make_access_token(admin_id)}"}
        updated = client.put(
            "/api/v1/admin/feature-flags/weekly_reports",
            headers=headers,
            json={"enabled": False, "description": "Temporarily paused"},
        )
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False

        public_after = client.get("/api/v1/features")
        assert public_after.status_code == 200
        assert public_after.json()["weekly_reports"] is False

        with sessions() as db:
            flag = db.get(FeatureFlag, "weekly_reports")
            assert flag is not None
            assert flag.updated_by_user_id == admin_id
            actions = {row.action for row in db.scalars(select(AuditLog)).all()}
            assert "admin.feature_flag_updated" in actions
    finally:
        app.dependency_overrides.clear()


def test_non_admin_cannot_modify_feature_flags():
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

        response = client.put(
            "/api/v1/admin/feature-flags/ai_coach",
            headers={"Authorization": f"Bearer {make_access_token(user_id)}"},
            json={"enabled": False},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
