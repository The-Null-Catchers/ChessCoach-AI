from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import User, WeeklyReport
from app.services.weekly_reports import build_weekly_report, week_bounds
from app.tasks.celery_app import celery
from app.tasks.email import send_auth_email


@celery.task
def generate_all_weekly_reports():
    db = SessionLocal()
    created = 0
    try:
        users = db.scalars(
            select(User).where(User.is_suspended.is_(False))
        ).all()
        week_start, _ = week_bounds()
        for user in users:
            existing = db.scalar(select(WeeklyReport).where(
                WeeklyReport.user_id == user.id,
                WeeklyReport.week_start == week_start,
            ))
            if existing is not None:
                continue
            build_weekly_report(db, user.id)
            db.commit()
            created += 1
            if user.is_verified:
                send_auth_email.delay(
                    user.email,
                    "Your ChessCoach AI weekly report",
                    "Your weekly chess report is ready. Open ChessCoach AI to review progress, weaknesses and training consistency.",
                )
        return {"processed": created}
    finally:
        db.close()
