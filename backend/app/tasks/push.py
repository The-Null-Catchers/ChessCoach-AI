from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.push import PushDelivery
from app.services.push_notifications import PushProviderError, deliver_push_delivery
from app.tasks.celery_app import celery

MAX_PUSH_ATTEMPTS = 4


@celery.task(bind=True, autoretry_for=(PushProviderError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def deliver_push(self, delivery_id: str):
    del self
    db = SessionLocal()
    try:
        delivery = deliver_push_delivery(db, delivery_id)
        db.commit()
        return {"id": delivery.id, "status": delivery.status, "attempts": delivery.attempts}
    except Exception:
        db.commit()
        raise
    finally:
        db.close()


@celery.task
def deliver_pending_pushes(limit: int = 100):
    db = SessionLocal()
    ids: list[str] = []
    try:
        rows = db.scalars(
            select(PushDelivery)
            .where(
                PushDelivery.status.in_(["pending", "failed"]),
                PushDelivery.attempts < MAX_PUSH_ATTEMPTS,
            )
            .order_by(PushDelivery.created_at.asc())
            .limit(max(1, min(limit, 500)))
        ).all()
        now = datetime.utcnow()
        for row in rows:
            row.status = "queued"
            row.updated_at = now
            ids.append(row.id)
        db.commit()
    finally:
        db.close()

    queued = 0
    for delivery_id in ids:
        try:
            deliver_push.delay(delivery_id)
            queued += 1
        except Exception:
            recovery_db = SessionLocal()
            try:
                row = recovery_db.get(PushDelivery, delivery_id)
                if row is not None and row.status == "queued":
                    row.status = "pending"
                    row.updated_at = datetime.utcnow()
                    recovery_db.commit()
            finally:
                recovery_db.close()
            raise
    return {"queued": queued}
