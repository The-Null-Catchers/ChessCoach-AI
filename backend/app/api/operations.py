from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.admin import require_admin
from app.db.session import get_db
from app.models.ai_usage import AIUsageEvent
from app.models.entities import User

router = APIRouter(prefix="/admin/operations", tags=["admin"])


@router.get("/ai-usage")
def ai_usage(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=90),
):
    since = datetime.utcnow() - timedelta(days=days)
    window = AIUsageEvent.created_at >= since

    requests = db.scalar(select(func.count()).select_from(AIUsageEvent).where(window)) or 0
    failures = db.scalar(
        select(func.count()).select_from(AIUsageEvent).where(
            window,
            AIUsageEvent.status == "failed",
        )
    ) or 0
    total_tokens = db.scalar(
        select(func.coalesce(func.sum(AIUsageEvent.total_tokens), 0)).where(window)
    ) or 0
    avg_latency = db.scalar(
        select(func.coalesce(func.avg(AIUsageEvent.latency_ms), 0)).where(window)
    ) or 0

    rows = db.execute(
        select(
            AIUsageEvent.provider,
            AIUsageEvent.model,
            AIUsageEvent.status,
            func.count(AIUsageEvent.id),
            func.coalesce(func.sum(AIUsageEvent.input_tokens), 0),
            func.coalesce(func.sum(AIUsageEvent.output_tokens), 0),
            func.coalesce(func.sum(AIUsageEvent.total_tokens), 0),
            func.coalesce(func.avg(AIUsageEvent.latency_ms), 0),
        )
        .where(window)
        .group_by(AIUsageEvent.provider, AIUsageEvent.model, AIUsageEvent.status)
        .order_by(func.count(AIUsageEvent.id).desc())
    ).all()

    return {
        "window_days": days,
        "requests": int(requests),
        "failed_requests": int(failures),
        "failure_rate": round(failures / requests, 4) if requests else 0.0,
        "total_tokens": int(total_tokens),
        "avg_latency_ms": round(float(avg_latency), 2),
        "providers": [
            {
                "provider": provider,
                "model": model,
                "status": status,
                "requests": int(count),
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "total_tokens": int(tokens),
                "avg_latency_ms": round(float(latency), 2),
            }
            for provider, model, status, count, input_tokens, output_tokens, tokens, latency in rows
        ],
    }
