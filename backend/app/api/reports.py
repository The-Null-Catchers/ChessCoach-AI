from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import Notification, WeeklyReport
from app.services.weekly_reports import build_weekly_report, serialize_report

router = APIRouter(tags=["reports"])


@router.get("/reports/weekly")
def list_weekly_reports(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    limit: int = Query(default=12, ge=1, le=52),
):
    rows = db.scalars(
        select(WeeklyReport)
        .where(WeeklyReport.user_id == user_id)
        .order_by(WeeklyReport.week_start.desc())
        .limit(limit)
    ).all()
    return [serialize_report(row) for row in rows]


@router.post("/reports/weekly/current")
def generate_current_weekly_report(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    report = build_weekly_report(db, user_id)
    db.commit()
    return serialize_report(report)


@router.get("/notifications")
def notifications(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
):
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    rows = db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "body": row.body,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "read_at": row.read_at.isoformat() if row.read_at else None,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if row.read_at is None:
        row.read_at = datetime.utcnow()
        db.commit()
    return {"id": row.id, "read_at": row.read_at.isoformat()}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Notification).where(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    )).all()
    now = datetime.utcnow()
    for row in rows:
        row.read_at = now
    db.commit()
    return {"updated": len(rows)}
