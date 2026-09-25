from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import AnalysisJob, AuditLog, FeatureFlag, Game, RefreshSession, User
from app.services.auth_sessions import revoke_all_user_sessions
from app.services.feature_flags import list_flags, set_flag

router = APIRouter(prefix="/admin", tags=["admin"])


class SuspensionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class FeatureFlagUpdate(BaseModel):
    enabled: bool
    description: str | None = Field(default=None, max_length=255)


def require_admin(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/overview")
def overview(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "suspended_users": db.scalar(
            select(func.count()).select_from(User).where(User.is_suspended.is_(True))
        ) or 0,
        "games": db.scalar(select(func.count()).select_from(Game)) or 0,
        "analysis_jobs": db.scalar(select(func.count()).select_from(AnalysisJob)) or 0,
        "failed_analysis_jobs": db.scalar(
            select(func.count()).select_from(AnalysisJob).where(AnalysisJob.status == "failed")
        ) or 0,
        "active_refresh_sessions": db.scalar(
            select(func.count()).select_from(RefreshSession).where(RefreshSession.revoked_at.is_(None))
        ) or 0,
    }


@router.get("/users")
def users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(User)
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(or_(func.lower(User.email).like(needle), User.id == q.strip()))
    rows = db.scalars(query.order_by(User.created_at.desc()).offset(offset).limit(limit)).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "is_verified": user.is_verified,
            "is_admin": user.is_admin,
            "is_suspended": user.is_suspended,
            "suspended_at": user.suspended_at.isoformat() if user.suspended_at else None,
            "suspension_reason": user.suspension_reason,
            "created_at": user.created_at.isoformat(),
        }
        for user in rows
    ]


@router.post("/users/{target_user_id}/suspend")
def suspend_user(
    target_user_id: str,
    payload: SuspensionRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if target_user_id == admin.id:
        raise HTTPException(status_code=409, detail="Admins cannot suspend their own account")
    target = db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_admin:
        raise HTTPException(status_code=409, detail="Admin accounts cannot be suspended here")

    target.is_suspended = True
    target.suspended_at = datetime.utcnow()
    target.suspension_reason = payload.reason.strip()
    revoke_all_user_sessions(db, target.id)
    db.add(AuditLog(
        user_id=admin.id,
        action="admin.user_suspended",
        entity_type="user",
        entity_id=target.id,
        metadata_json=json.dumps({"reason": target.suspension_reason}),
    ))
    db.commit()
    return {"id": target.id, "is_suspended": True}


@router.post("/users/{target_user_id}/unsuspend")
def unsuspend_user(
    target_user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_suspended = False
    target.suspended_at = None
    target.suspension_reason = None
    db.add(AuditLog(
        user_id=admin.id,
        action="admin.user_unsuspended",
        entity_type="user",
        entity_id=target.id,
    ))
    db.commit()
    return {"id": target.id, "is_suspended": False}


@router.get("/feature-flags")
def feature_flags(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    flags = list_flags(db)
    db.commit()
    return [
        {
            "key": flag.key,
            "enabled": flag.enabled,
            "description": flag.description,
            "updated_by_user_id": flag.updated_by_user_id,
            "updated_at": flag.updated_at.isoformat(),
        }
        for flag in flags
    ]


@router.put("/feature-flags/{key}")
def update_feature_flag(
    key: str,
    payload: FeatureFlagUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    normalized = key.strip().lower().replace(" ", "_")
    if not normalized or len(normalized) > 80:
        raise HTTPException(status_code=422, detail="Invalid feature flag key")
    if not all(char.isalnum() or char in {"_", "-", "."} for char in normalized):
        raise HTTPException(status_code=422, detail="Invalid feature flag key")

    flag = set_flag(
        db,
        key=normalized,
        enabled=payload.enabled,
        description=payload.description,
        admin_user_id=admin.id,
    )
    db.add(AuditLog(
        user_id=admin.id,
        action="admin.feature_flag_updated",
        entity_type="feature_flag",
        entity_id=flag.key,
        metadata_json=json.dumps({"enabled": flag.enabled}),
    ))
    db.commit()
    return {
        "key": flag.key,
        "enabled": flag.enabled,
        "description": flag.description,
        "updated_by_user_id": flag.updated_by_user_id,
        "updated_at": flag.updated_at.isoformat(),
    }
