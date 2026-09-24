from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


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
    return TestClient(app)


def _register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "very-secure-password",
            "display_name": "Opening Tester",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_training_queue_hides_answer_and_enforces_ownership(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    client = _client()
    try:
        owner_token = _register(client, "owner-openings@example.com")
        other_token = _register(client, "other-openings@example.com")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}

        created = client.post(
            "/api/v1/repertoires",
            headers=owner_headers,
            json={"name": "Italian Game", "color": "white"},
        )
        assert created.status_code == 201
        repertoire_id = created.json()["id"]

        imported = client.post(
            f"/api/v1/repertoires/{repertoire_id}/import-pgn",
            headers=owner_headers,
            json={
                "pgn": """[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 *
"""
            },
        )
        assert imported.status_code == 200
        assert imported.json()["imported_nodes"] == 5

        queue = client.get(
            f"/api/v1/repertoires/{repertoire_id}/training",
            headers=owner_headers,
        )
        assert queue.status_code == 200
        items = queue.json()
        assert items
        assert "expected_move_uci" not in items[0]
        assert "expected_move_san" not in items[0]
        assert {"line_id", "fen", "ply", "mastery", "repetitions", "lapses"} <= set(items[0])

        forbidden_tree = client.get(
            f"/api/v1/repertoires/{repertoire_id}",
            headers=other_headers,
        )
        forbidden_training = client.get(
            f"/api/v1/repertoires/{repertoire_id}/training",
            headers=other_headers,
        )
        assert forbidden_tree.status_code == 404
        assert forbidden_training.status_code == 404
    finally:
        app.dependency_overrides.clear()
