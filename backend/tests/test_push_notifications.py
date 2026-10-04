from __future__ import annotations

import json

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.entities import Notification, User
from app.models.push import PushDelivery, PushSubscription
from app.services.push_notifications import (
    DisabledPushProvider,
    PushMessage,
    PushProviderResult,
    WebhookPushProvider,
    deliver_push_delivery,
    queue_notification_deliveries,
    register_push_subscription,
)


class RecordingProvider:
    name = "recording"

    def __init__(self):
        self.calls: list[tuple[str, str, PushMessage]] = []

    def send(self, *, token: str, platform: str, message: PushMessage) -> PushProviderResult:
        self.calls.append((token, platform, message))
        return PushProviderResult(delivered=True, message_id="msg-123")


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def test_subscription_outbox_is_idempotent_and_delivers_without_exposing_provider_details():
    db = _db()
    try:
        user = User(email="push@example.com", password_hash="x")
        db.add(user)
        db.flush()
        subscription = register_push_subscription(
            db,
            user_id=user.id,
            token="device-token-that-is-long-enough",
            platform="android",
            device_id="pixel-test",
        )
        notification = Notification(
            user_id=user.id,
            kind="weekly_report_ready",
            title="Weekly report",
            body="Your report is ready",
            entity_type="weekly_report",
            entity_id="report-1",
        )
        db.add(notification)
        db.flush()

        first = queue_notification_deliveries(db, notification)
        second = queue_notification_deliveries(db, notification)
        assert len(first) == 1
        assert second == []

        provider = RecordingProvider()
        delivery = deliver_push_delivery(db, first[0].id, provider=provider)
        assert delivery.status == "delivered"
        assert delivery.attempts == 1
        assert delivery.provider_message_id == "msg-123"
        assert delivery.delivered_at is not None
        assert provider.calls[0][0] == subscription.token
        assert provider.calls[0][1] == "android"
        assert provider.calls[0][2].data["notification_id"] == notification.id

        # Completed rows are safe to replay and must not send a duplicate notification.
        replay = deliver_push_delivery(db, first[0].id, provider=provider)
        assert replay.status == "delivered"
        assert len(provider.calls) == 1
    finally:
        db.close()


def test_reregistering_same_token_reactivates_same_subscription():
    db = _db()
    try:
        user = User(email="push2@example.com", password_hash="x")
        db.add(user)
        db.flush()
        first = register_push_subscription(
            db,
            user_id=user.id,
            token="same-device-token-long-enough",
            platform="android",
        )
        first.active = False
        db.flush()
        second = register_push_subscription(
            db,
            user_id=user.id,
            token="same-device-token-long-enough",
            platform="ios",
            device_id="new-device-id",
        )
        assert second.id == first.id
        assert second.active is True
        assert second.platform == "ios"
        assert second.device_id == "new-device-id"
        assert db.query(PushSubscription).count() == 1
    finally:
        db.close()


def test_disabled_provider_marks_delivery_skipped():
    db = _db()
    try:
        user = User(email="disabled@example.com", password_hash="x")
        db.add(user)
        db.flush()
        register_push_subscription(
            db,
            user_id=user.id,
            token="disabled-device-token-long-enough",
            platform="web",
        )
        notification = Notification(
            user_id=user.id,
            kind="test",
            title="Test",
            body="Test body",
        )
        db.add(notification)
        db.flush()
        delivery = queue_notification_deliveries(db, notification)[0]
        result = deliver_push_delivery(db, delivery.id, provider=DisabledPushProvider())
        assert result.status == "skipped"
        assert db.get(PushDelivery, delivery.id).attempts == 1
    finally:
        db.close()


def test_webhook_provider_sends_normalized_payload_and_bearer_header():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization")
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"message_id": "remote-42"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = WebhookPushProvider(
        url="https://push.example.test/deliver",
        bearer_token="secret",
        client=client,
    )
    try:
        result = provider.send(
            token="opaque-token",
            platform="android",
            message=PushMessage(
                title="Coach update",
                body="Training is ready",
                data={"kind": "training"},
            ),
        )
    finally:
        client.close()

    assert result.delivered is True
    assert result.message_id == "remote-42"
    assert seen["authorization"] == "Bearer secret"
    payload = seen["payload"]
    assert payload["token"] == "opaque-token"
    assert payload["platform"] == "android"
    assert payload["notification"]["title"] == "Coach update"
    assert payload["data"] == {"kind": "training"}
