import chess
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import EndgameExercise, EndgameReviewState
from app.services.endgame_trainer import DEFAULT_EXERCISES, ensure_default_exercises


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


def _register(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "endgame@example.com",
            "password": "very-secure-password",
            "display_name": "Endgame",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_default_endgame_positions_and_solutions_are_legal():
    client, testing_session = _client()
    try:
        with testing_session() as db:
            ensure_default_exercises(db)
            db.commit()
            rows = db.scalars(select(EndgameExercise)).all()
            assert len(rows) == len(DEFAULT_EXERCISES)
            for exercise in rows:
                board = chess.Board(exercise.fen)
                assert board.is_valid()
                assert chess.Move.from_uci(exercise.solution_uci) in board.legal_moves
    finally:
        app.dependency_overrides.clear()


def test_endgame_queue_hides_solution_and_attempt_updates_mastery(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    client, testing_session = _client()
    try:
        token = _register(client)
        headers = {"Authorization": f"Bearer {token}"}

        queue = client.get("/api/v1/endgames/trainer/queue", headers=headers)
        assert queue.status_code == 200
        items = queue.json()
        assert items
        assert "solution_uci" not in items[0]
        assert "explanation" not in items[0]

        first = items[0]
        with testing_session() as db:
            exercise = db.get(EndgameExercise, first["exercise_id"])
            solution = exercise.solution_uci

        result = client.post(
            f"/api/v1/endgames/trainer/{first['exercise_id']}/attempt",
            headers=headers,
            json={"move_uci": solution, "grade": "good"},
        )
        assert result.status_code == 200
        payload = result.json()
        assert payload["correct"] is True
        assert payload["expected_move_uci"] == solution
        assert payload["mastery"] > 0

        with testing_session() as db:
            state = db.scalar(
                select(EndgameReviewState).where(
                    EndgameReviewState.exercise_id == first["exercise_id"]
                )
            )
            assert state is not None
            assert state.repetitions == 1
            assert state.interval_days == 3
    finally:
        app.dependency_overrides.clear()
