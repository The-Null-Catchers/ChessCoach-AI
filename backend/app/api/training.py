from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import ReviewState, TrainingSession
from app.services.training_plan import generate_weekly_plan

router = APIRouter(prefix="/training", tags=["training"])


class CompleteSessionRequest(BaseModel):
    minutes_spent: int = Field(default=0, ge=0, le=600)


@router.get("")
def get_training(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    plan = generate_weekly_plan(db, user_id)
    db.commit()
    sessions = db.scalars(
        select(TrainingSession)
        .where(TrainingSession.plan_id == plan.id)
        .order_by(TrainingSession.scheduled_for.asc())
    ).all()
    due_reviews = db.scalars(
        select(ReviewState).where(
            ReviewState.user_id == user_id,
            ReviewState.due_at <= datetime.utcnow(),
        )
    ).all()
    return {
        "plan": {
            "id": plan.id,
            "week_start": plan.week_start.isoformat(),
            "status": plan.status,
            "focus_summary": plan.focus_summary,
        },
        "due_reviews": len(due_reviews),
        "sessions": [
            {
                "id": s.id,
                "type": s.session_type,
                "focus_category": s.focus_category,
                "target_count": s.target_count,
                "scheduled_for": s.scheduled_for.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "minutes_spent": s.minutes_spent,
            }
            for s in sessions
        ],
    }


@router.post("/{session_id}/complete")
def complete_session(
    session_id: str,
    payload: CompleteSessionRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    session = db.scalar(select(TrainingSession).where(
        TrainingSession.id == session_id,
        TrainingSession.user_id == user_id,
    ))
    if not session:
        raise HTTPException(404, "Training session not found")
    session.completed_at = datetime.utcnow()
    session.minutes_spent = payload.minutes_spent
    db.commit()
    return {
        "id": session.id,
        "completed_at": session.completed_at.isoformat(),
        "minutes_spent": session.minutes_spent,
    }
