from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import Notification, WeeklyReport
from app.models.push import PushSubscription
from app.services.push_notifications import (
    PushSubscriptionConflict,
    deactivate_push_subscription,
    register_push_subscription,
)
from app.services.weekly_reports import build_weekly_report, serialize_report

router = APIRouter(tags=["reports"])


class PushSubscriptionRequest(BaseModel):
    token: str = Field(min_length=16, max_length=4096)
    platform: Literal["android", "ios", "web"]
    device_id: str | None = Field(default=None, max_length=128)
    provider: str = Field(default="default", min_length=1, max_length=32)


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


@router.get("/notifications/push/subscriptions")
def list_push_subscriptions(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(PushSubscription)
        .where(PushSubscription.user_id == user_id)
        .order_by(PushSubscription.updated_at.desc())
    ).all()
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "platform": row.platform,
            "device_id": row.device_id,
            "active": row.active,
            "last_seen_at": row.last_seen_at.isoformat(),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/notifications/push/subscriptions")
def register_push_device(
    payload: PushSubscriptionRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    try:
        row = register_push_subscription(
            db,
            user_id=user_id,
            token=payload.token,
            platform=payload.platform,
            device_id=payload.device_id,
            provider=payload.provider,
        )
    except PushSubscriptionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {
        "id": row.id,
        "provider": row.provider,
        "platform": row.platform,
        "device_id": row.device_id,
        "active": row.active,
    }


@router.delete("/notifications/push/subscriptions/{subscription_id}")
def unregister_push_device(
    subscription_id: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if not deactivate_push_subscription(db, user_id=user_id, subscription_id=subscription_id):
        raise HTTPException(status_code=404, detail="Push subscription not found")
    db.commit()
    return {"id": subscription_id, "active": False}


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
