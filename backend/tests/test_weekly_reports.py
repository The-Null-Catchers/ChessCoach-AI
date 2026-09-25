from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password, make_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import Notification, User, WeeklyReport
from app.services.weekly_reports import build_weekly_report


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


def test_weekly_report_is_idempotent_and_creates_one_notification():
    _, sessions = _client()
    try:
        with sessions() as db:
            user = User(email="weekly@example.com", password_hash=hash_password("secure-password-123"))
            db.add(user)
            db.flush()
            first = build_weekly_report(db, user.id)
            second = build_weekly_report(db, user.id)
            assert first.id == second.id
            db.commit()

            assert len(db.scalars(select(WeeklyReport)).all()) == 1
            notifications = db.scalars(select(Notification)).all()
            assert len(notifications) == 1
            assert notifications[0].entity_id == first.id
    finally:
        app.dependency_overrides.clear()


def test_user_can_read_weekly_report_and_mark_notification_read():
    client, sessions = _client()
    try:
        with sessions() as db:
            user = User(email="reader@example.com", password_hash=hash_password("secure-password-123"))
            db.add(user)
            db.flush()
            user_id = user.id
            report = build_weekly_report(db, user_id)
            report_id = report.id
            notification = db.scalar(select(Notification).where(Notification.user_id == user_id))
            notification_id = notification.id
            db.commit()

        token = make_access_token(user_id)
        headers = {"Authorization": f"Bearer {token}"}

        reports = client.get("/api/v1/reports/weekly", headers=headers)
        assert reports.status_code == 200
        assert reports.json()[0]["id"] == report_id

        unread = client.get("/api/v1/notifications?unread_only=true", headers=headers)
        assert unread.status_code == 200
        assert len(unread.json()) == 1

        marked = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)
        assert marked.status_code == 200
        assert marked.json()["read_at"] is not None

        unread_after = client.get("/api/v1/notifications?unread_only=true", headers=headers)
        assert unread_after.status_code == 200
        assert unread_after.json() == []
    finally:
        app.dependency_overrides.clear()
