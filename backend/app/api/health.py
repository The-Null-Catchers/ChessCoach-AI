from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, status
from redis import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


def check_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis() -> bool:
    try:
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        try:
            return bool(client.ping())
        finally:
            client.close()
    except Exception:
        return False


def check_stockfish() -> bool:
    return os.path.isfile(settings.stockfish_path) and os.access(settings.stockfish_path, os.X_OK)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> dict[str, object]:
    dependencies = {
        "database": check_database(),
        "redis": check_redis(),
        "stockfish": check_stockfish(),
    }
    if not all(dependencies.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "dependencies": dependencies},
        )
    return {"status": "ready", "dependencies": dependencies}
