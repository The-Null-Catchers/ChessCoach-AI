from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import EndgameStat, OpeningStat, PlayerInsight, PlayerWeakness, Profile
from app.services.player_analytics import compute_overview, recompute_player_analytics

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def analytics(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    recompute_player_analytics(db, user_id)
    db.commit()
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    openings = db.scalars(
        select(OpeningStat)
        .where(OpeningStat.user_id == user_id)
        .order_by(OpeningStat.games_count.desc(), OpeningStat.avg_accuracy.desc())
    ).all()
    endgames = db.scalars(
        select(EndgameStat)
        .where(EndgameStat.user_id == user_id)
        .order_by(EndgameStat.games_count.desc())
    ).all()
    insights = db.scalars(
        select(PlayerInsight)
        .where(PlayerInsight.user_id == user_id)
        .order_by(PlayerInsight.created_at.desc())
        .limit(10)
    ).all()
    weaknesses = db.scalars(
        select(PlayerWeakness)
        .where(PlayerWeakness.user_id == user_id)
        .order_by(PlayerWeakness.score.desc())
        .limit(10)
    ).all()
    return {
        "rating": profile.rating if profile else None,
        "overview": compute_overview(db, user_id),
        "openings": [
            {
                "eco": item.eco,
                "opening": item.opening,
                "variation": item.variation,
                "color": item.color,
                "games": item.games_count,
                "wins": item.wins,
                "draws": item.draws,
                "losses": item.losses,
                "average_accuracy": item.avg_accuracy,
                "common_deviation_ply": item.common_deviation_ply,
                "deviation_basis": "first_significant_opening_error",
            }
            for item in openings
        ],
        "endgames": [
            {
                "category": item.category,
                "games": item.games_count,
                "average_accuracy": item.avg_accuracy,
                "mistakes": item.mistakes,
            }
            for item in endgames
        ],
        "weaknesses": [
            {
                "category": item.category,
                "score": item.score,
                "confidence": item.confidence,
                "sample_size": item.sample_size,
                "trend": item.trend,
            }
            for item in weaknesses
        ],
        "insights": [
            {
                "type": item.insight_type,
                "title": item.title,
                "body": item.body,
                "confidence": item.confidence,
                "created_at": item.created_at.isoformat(),
            }
            for item in insights
        ],
    }


@router.get("/openings")
def openings(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    recompute_player_analytics(db, user_id)
    db.commit()
    rows = db.scalars(
        select(OpeningStat).where(OpeningStat.user_id == user_id).order_by(OpeningStat.games_count.desc())
    ).all()
    return [
        {
            "eco": item.eco,
            "opening": item.opening,
            "variation": item.variation,
            "color": item.color,
            "games": item.games_count,
            "wins": item.wins,
            "draws": item.draws,
            "losses": item.losses,
            "average_accuracy": item.avg_accuracy,
            "common_deviation_ply": item.common_deviation_ply,
        }
        for item in rows
    ]


@router.get("/endgames")
def endgames(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    recompute_player_analytics(db, user_id)
    db.commit()
    rows = db.scalars(
        select(EndgameStat).where(EndgameStat.user_id == user_id).order_by(EndgameStat.games_count.desc())
    ).all()
    return [
        {
            "category": item.category,
            "games": item.games_count,
            "average_accuracy": item.avg_accuracy,
            "mistakes": item.mistakes,
        }
        for item in rows
    ]


@router.get("/insights")
def insights(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    recompute_player_analytics(db, user_id)
    db.commit()
    rows = db.scalars(
        select(PlayerInsight)
        .where(PlayerInsight.user_id == user_id)
        .order_by(PlayerInsight.created_at.desc())
    ).all()
    return [
        {
            "type": item.insight_type,
            "title": item.title,
            "body": item.body,
            "confidence": item.confidence,
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]
