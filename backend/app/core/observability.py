from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request

logger = logging.getLogger("chesscoach.http")


def configure_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_observability(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "").strip()
        request_id = supplied if supplied and len(supplied) <= 128 else str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                json.dumps(
                    {
                        "event": "http_request_failed",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": elapsed_ms,
                    },
                    separators=(",", ":"),
                )
            )
            raise

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": elapsed_ms,
                },
                separators=(",", ":"),
            )
        )
        return response
