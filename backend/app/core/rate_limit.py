from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    requests: int
    window_seconds: int


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, rule: RateLimitRule) -> None:
    if not settings.rate_limit_enabled:
        return

    redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=True,
    )
    key = f"ratelimit:{rule.name}:{_client_key(request)}"
    try:
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, rule.window_seconds)
        ttl = max(redis.ttl(key), 1)
    except RedisError as exc:
        if settings.rate_limit_fail_open:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter unavailable",
        ) from exc
    finally:
        redis.close()

    if count > rule.requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(ttl)},
        )


LOGIN_LIMIT = RateLimitRule("login", 10, 60)
REGISTER_LIMIT = RateLimitRule("register", 5, 60)
PASSWORD_RESET_LIMIT = RateLimitRule("password-reset", 5, 300)
VERIFY_LIMIT = RateLimitRule("verify-email", 10, 300)
