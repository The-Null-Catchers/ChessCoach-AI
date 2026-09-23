from fastapi.testclient import TestClient

from app.api import health as health_api
from app.main import app


def test_liveness_returns_request_id():
    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_readiness_reports_dependency_state(monkeypatch):
    monkeypatch.setattr(health_api, "check_database", lambda: True)
    monkeypatch.setattr(health_api, "check_redis", lambda: True)
    monkeypatch.setattr(health_api, "check_stockfish", lambda: True)

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"database": True, "redis": True, "stockfish": True},
    }


def test_readiness_fails_closed_when_dependency_is_down(monkeypatch):
    monkeypatch.setattr(health_api, "check_database", lambda: True)
    monkeypatch.setattr(health_api, "check_redis", lambda: False)
    monkeypatch.setattr(health_api, "check_stockfish", lambda: True)

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "not_ready",
        "dependencies": {"database": True, "redis": False, "stockfish": True},
    }
