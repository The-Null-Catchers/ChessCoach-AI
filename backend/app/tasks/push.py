from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.push import PushDelivery
from app.services.push_notifications import PushProviderError, deliver_push_delivery
from app.tasks.celery_app import celery


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
    try:
        rows = db.scalars(
            select(PushDelivery)
            .where(PushDelivery.status.in_(["pending", "failed"]))
            .order_by(PushDelivery.created_at.asc())
            .limit(max(1, min(limit, 500)))
        ).all()
        ids = [row.id for row in rows]
    finally:
        db.close()

    for delivery_id in ids:
        deliver_push.delay(delivery_id)
    return {"queued": len(ids)}
