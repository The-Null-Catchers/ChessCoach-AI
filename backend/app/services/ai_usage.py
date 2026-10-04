from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsageEvent


def provider_usage(provider: Any) -> tuple[int, int, int, str | None]:
    raw = getattr(provider, "last_usage", None) or {}
    input_tokens = max(0, int(raw.get("prompt_tokens") or raw.get("input_tokens") or 0))
    output_tokens = max(0, int(raw.get("completion_tokens") or raw.get("output_tokens") or 0))
    total_tokens = max(0, int(raw.get("total_tokens") or (input_tokens + output_tokens)))
    request_id = getattr(provider, "last_request_id", None)
    return input_tokens, output_tokens, total_tokens, request_id


def record_ai_usage(
    db: Session,
    *,
    user_id: str,
    move_id: str | None,
    provider: Any,
    status: str,
    latency_ms: int,
    operation: str = "coach_explanation",
    error: Exception | None = None,
) -> AIUsageEvent:
    input_tokens, output_tokens, total_tokens, request_id = provider_usage(provider)
    event = AIUsageEvent(
        user_id=user_id,
        move_id=move_id,
        provider=str(getattr(provider, "name", "unknown"))[:32],
        model=str(getattr(provider, "model", "unknown"))[:120],
        operation=operation,
        status=status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        latency_ms=max(0, int(latency_ms)),
        request_id=str(request_id)[:160] if request_id else None,
        error_type=type(error).__name__[:120] if error is not None else None,
    )
    db.add(event)
    return event
