from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import FeatureFlag


DEFAULT_FLAGS: tuple[tuple[str, bool, str], ...] = (
    ("weekly_reports", True, "Generate and surface weekly coaching reports."),
    ("opening_trainer", True, "Enable opening repertoire training."),
    ("endgame_trainer", True, "Enable curated endgame training."),
    ("ai_coach", True, "Enable AI-generated coaching explanations."),
    ("mobile_offline_queue", True, "Allow mobile offline puzzle attempt queueing."),
)


def ensure_default_flags(db: Session) -> None:
    existing = set(db.scalars(select(FeatureFlag.key)).all())
    for key, enabled, description in DEFAULT_FLAGS:
        if key not in existing:
            db.add(FeatureFlag(key=key, enabled=enabled, description=description))
    db.flush()


def list_flags(db: Session) -> list[FeatureFlag]:
    ensure_default_flags(db)
    return list(db.scalars(select(FeatureFlag).order_by(FeatureFlag.key.asc())).all())


def set_flag(
    db: Session,
    *,
    key: str,
    enabled: bool,
    description: str | None,
    admin_user_id: str,
) -> FeatureFlag:
    flag = db.get(FeatureFlag, key)
    if flag is None:
        flag = FeatureFlag(key=key)
        db.add(flag)
    flag.enabled = enabled
    if description is not None:
        flag.description = description.strip() or None
    flag.updated_by_user_id = admin_user_id
    flag.updated_at = datetime.utcnow()
    db.flush()
    return flag


def enabled_flags(db: Session) -> dict[str, bool]:
    return {flag.key: flag.enabled for flag in list_flags(db)}
