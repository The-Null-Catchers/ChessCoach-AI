from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import PlayerWeakness, TrainingPlan, TrainingSession


def _week_start(now: datetime) -> datetime:
    day = now - timedelta(days=now.weekday())
    return day.replace(hour=0, minute=0, second=0, microsecond=0)


def generate_weekly_plan(db: Session, user_id: str, now: datetime | None = None) -> TrainingPlan:
    now = now or datetime.utcnow()
    week = _week_start(now)
    existing = db.scalar(select(TrainingPlan).where(
        TrainingPlan.user_id == user_id,
        TrainingPlan.week_start == week,
    ))
    if existing:
        return existing

    weaknesses = db.scalars(
        select(PlayerWeakness)
        .where(PlayerWeakness.user_id == user_id)
        .order_by(PlayerWeakness.score.desc())
        .limit(3)
    ).all()
    focus = [w.category for w in weaknesses]
    summary = "Focus on " + ", ".join(focus) if focus else "Build consistency from recent games"

    plan = TrainingPlan(user_id=user_id, week_start=week, status="active", focus_summary=summary)
    db.add(plan)
    db.flush()

    schedule = [
        (0, "tactics", focus[0] if focus else "mixed_tactics", 10),
        (1, "game_review", focus[0] if focus else None, 2),
        (2, "tactics", focus[1] if len(focus) > 1 else "mixed_tactics", 10),
        (3, "endgame", focus[1] if len(focus) > 1 else "rook_endgames", 8),
        (4, "mixed_review", focus[2] if len(focus) > 2 else None, 12),
    ]
    for day_offset, kind, category, target in schedule:
        db.add(TrainingSession(
            plan_id=plan.id,
            user_id=user_id,
            session_type=kind,
            focus_category=category,
            target_count=target,
            scheduled_for=week + timedelta(days=day_offset, hours=18),
        ))
    db.flush()
    return plan
