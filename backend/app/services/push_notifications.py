from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Notification
from app.models.push import PushDelivery, PushSubscription


class PushSubscriptionConflict(RuntimeError):
    """Raised when a push token is already owned by another account."""


class PushProviderError(RuntimeError):
    """Raised when an external push provider cannot deliver a message."""


@dataclass(frozen=True)
class PushMessage:
    title: str
    body: str
    data: dict[str, str]


@dataclass(frozen=True)
class PushProviderResult:
    delivered: bool
    message_id: str | None = None
    skipped: bool = False


class PushProvider(Protocol):
    name: str

    def send(self, *, token: str, platform: str, message: PushMessage) -> PushProviderResult:
        ...


class DisabledPushProvider:
    name = "disabled"

    def send(self, *, token: str, platform: str, message: PushMessage) -> PushProviderResult:
        del token, platform, message
        return PushProviderResult(delivered=False, skipped=True)


class WebhookPushProvider:
    name = "webhook"

    def __init__(
        self,
        *,
        url: str,
        bearer_token: str = "",
        timeout_seconds: float = 10.0,
        client: httpx.Client | None = None,
    ):
        if not url.startswith("https://"):
            raise ValueError("Push webhook URL must use HTTPS")
        self.url = url
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
        self.client = client

    def send(self, *, token: str, platform: str, message: PushMessage) -> PushProviderResult:
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        payload = {
            "token": token,
            "platform": platform,
            "notification": {
                "title": message.title,
                "body": message.body,
            },
            "data": message.data,
        }
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds, follow_redirects=False)
        try:
            response = client.post(self.url, json=payload, headers=headers)
            if response.status_code >= 400:
                raise PushProviderError(f"Push provider returned HTTP {response.status_code}")
            message_id = None
            try:
                body = response.json()
                if isinstance(body, dict):
                    raw_id = body.get("id") or body.get("message_id")
                    if raw_id is not None:
                        message_id = str(raw_id)[:160]
            except ValueError:
                pass
            return PushProviderResult(delivered=True, message_id=message_id)
        except httpx.HTTPError as exc:
            raise PushProviderError("Push provider is temporarily unavailable") from exc
        finally:
            if owns_client:
                client.close()


def get_push_provider() -> PushProvider:
    provider = os.getenv("PUSH_PROVIDER", "disabled").strip().lower()
    if provider in {"", "disabled", "none"}:
        return DisabledPushProvider()
    if provider == "webhook":
        url = os.getenv("PUSH_WEBHOOK_URL", "").strip()
        if not url:
            raise RuntimeError("PUSH_WEBHOOK_URL is required when PUSH_PROVIDER=webhook")
        return WebhookPushProvider(
            url=url,
            bearer_token=os.getenv("PUSH_WEBHOOK_TOKEN", ""),
            timeout_seconds=float(os.getenv("PUSH_TIMEOUT_SECONDS", "10")),
        )
    raise RuntimeError(f"Unsupported push provider: {provider}")


def hash_push_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_push_subscription(
    db: Session,
    *,
    user_id: str,
    token: str,
    platform: str,
    device_id: str | None = None,
    provider: str = "default",
) -> PushSubscription:
    normalized = token.strip()
    if len(normalized) < 16 or len(normalized) > 4096:
        raise ValueError("Push token must be between 16 and 4096 characters")
    token_hash = hash_push_token(normalized)
    existing = db.scalar(select(PushSubscription).where(PushSubscription.token_hash == token_hash))
    now = datetime.utcnow()
    if existing is not None:
        if existing.user_id != user_id:
            raise PushSubscriptionConflict("Push token is already registered to another account")
        existing.token = normalized
        existing.platform = platform
        existing.device_id = device_id
        existing.provider = provider
        existing.active = True
        existing.last_seen_at = now
        existing.updated_at = now
        db.flush()
        return existing

    subscription = PushSubscription(
        user_id=user_id,
        token_hash=token_hash,
        token=normalized,
        platform=platform,
        device_id=device_id,
        provider=provider,
        active=True,
        last_seen_at=now,
        updated_at=now,
    )
    db.add(subscription)
    db.flush()
    return subscription


def deactivate_push_subscription(db: Session, *, user_id: str, subscription_id: str) -> bool:
    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.id == subscription_id,
            PushSubscription.user_id == user_id,
        )
    )
    if subscription is None:
        return False
    subscription.active = False
    subscription.updated_at = datetime.utcnow()
    db.flush()
    return True


def queue_notification_deliveries(db: Session, notification: Notification) -> list[PushDelivery]:
    subscriptions = db.scalars(
        select(PushSubscription).where(
            PushSubscription.user_id == notification.user_id,
            PushSubscription.active.is_(True),
        )
    ).all()
    created: list[PushDelivery] = []
    for subscription in subscriptions:
        existing = db.scalar(
            select(PushDelivery).where(
                PushDelivery.notification_id == notification.id,
                PushDelivery.subscription_id == subscription.id,
            )
        )
        if existing is not None:
            continue
        delivery = PushDelivery(
            notification_id=notification.id,
            subscription_id=subscription.id,
            status="pending",
        )
        db.add(delivery)
        created.append(delivery)
    if created:
        db.flush()
    return created


def deliver_push_delivery(
    db: Session,
    delivery_id: str,
    *,
    provider: PushProvider | None = None,
) -> PushDelivery:
    delivery = db.scalar(select(PushDelivery).where(PushDelivery.id == delivery_id))
    if delivery is None:
        raise LookupError("Push delivery not found")
    if delivery.status in {"delivered", "skipped"}:
        return delivery

    notification = db.scalar(select(Notification).where(Notification.id == delivery.notification_id))
    subscription = db.scalar(
        select(PushSubscription).where(PushSubscription.id == delivery.subscription_id)
    )
    if notification is None or subscription is None or not subscription.active:
        delivery.status = "skipped"
        delivery.updated_at = datetime.utcnow()
        db.flush()
        return delivery

    sender = provider or get_push_provider()
    delivery.attempts += 1
    delivery.updated_at = datetime.utcnow()
    try:
        result = sender.send(
            token=subscription.token,
            platform=subscription.platform,
            message=PushMessage(
                title=notification.title,
                body=notification.body,
                data={
                    "notification_id": notification.id,
                    "kind": notification.kind,
                    "entity_type": notification.entity_type or "",
                    "entity_id": notification.entity_id or "",
                },
            ),
        )
    except PushProviderError as exc:
        delivery.status = "failed"
        delivery.last_error = str(exc)[:1000]
        db.flush()
        raise

    delivery.last_error = None
    delivery.provider_message_id = result.message_id
    if result.skipped:
        delivery.status = "skipped"
    elif result.delivered:
        delivery.status = "delivered"
        delivery.delivered_at = datetime.utcnow()
    else:
        delivery.status = "failed"
        delivery.last_error = "Push provider did not confirm delivery"
    db.flush()
    return delivery
