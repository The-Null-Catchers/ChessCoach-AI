from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Notification, PlayerInsight, PlayerWeakness, TrainingSession, WeeklyReport
from app.services.player_analytics import compute_overview


def week_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.utcnow()
    start = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
    return start, start + timedelta(days=7)


def build_weekly_report(db: Session, user_id: str, *, now: datetime | None = None) -> WeeklyReport:
    week_start, week_end = week_bounds(now)
    existing = db.scalar(select(WeeklyReport).where(
        WeeklyReport.user_id == user_id,
        WeeklyReport.week_start == week_start,
    ))
    if existing is not None:
        return existing

    weaknesses = db.scalars(
        select(PlayerWeakness)
        .where(PlayerWeakness.user_id == user_id)
        .order_by(PlayerWeakness.score.desc())
        .limit(3)
    ).all()
    insights = db.scalars(
        select(PlayerInsight)
        .where(PlayerInsight.user_id == user_id)
        .order_by(PlayerInsight.created_at.desc())
        .limit(3)
    ).all()
    sessions = db.scalars(
        select(TrainingSession).where(
            TrainingSession.user_id == user_id,
            TrainingSession.scheduled_for >= week_start,
            TrainingSession.scheduled_for < week_end,
        )
    ).all()

    completed = sum(session.completed_at is not None for session in sessions)
    minutes = sum(session.minutes_spent for session in sessions if session.completed_at is not None)
    summary = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "overview": compute_overview(db, user_id),
        "training": {
            "scheduled_sessions": len(sessions),
            "completed_sessions": completed,
            "minutes_spent": minutes,
        },
        "top_weaknesses": [
            {
                "category": item.category,
                "score": item.score,
                "confidence": item.confidence,
                "sample_size": item.sample_size,
                "trend": item.trend,
            }
            for item in weaknesses
        ],
        "insights": [
            {
                "type": item.insight_type,
                "title": item.title,
                "body": item.body,
                "confidence": item.confidence,
            }
            for item in insights
        ],
    }
    report = WeeklyReport(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        summary_json=json.dumps(summary),
    )
    db.add(report)
    db.flush()

    db.add(Notification(
        user_id=user_id,
        kind="weekly_report_ready",
        title="Your weekly chess report is ready",
        body="Review your progress, recurring weaknesses and training consistency from this week.",
        entity_type="weekly_report",
        entity_id=report.id,
    ))
    db.flush()
    return report


def serialize_report(report: WeeklyReport) -> dict[str, object]:
    return {
        "id": report.id,
        "week_start": report.week_start.isoformat(),
        "week_end": report.week_end.isoformat(),
        "created_at": report.created_at.isoformat(),
        "summary": json.loads(report.summary_json),
    }
