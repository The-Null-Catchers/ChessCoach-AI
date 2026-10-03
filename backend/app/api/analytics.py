from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import EndgameStat, OpeningStat, PlayerInsight, PlayerWeakness, Profile
from app.models.weakness_history import WeaknessSnapshot
from app.services.player_analytics import compute_overview

router = APIRouter(tags=["analytics"])


def _trend_direction(delta: float) -> str:
    if delta < -0.01:
        return "improving"
    if delta > 0.01:
        return "worsening"
    return "stable"


@router.get("/analytics")
def analytics(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
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
                "direction": _trend_direction(item.trend),
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


@router.get("/analytics/weakness-history")
def weakness_history(
    category: str | None = None,
    limit: int = Query(default=12, ge=1, le=52),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if category is not None:
        category = category.strip()
        if not category:
            raise HTTPException(422, "category must not be blank")
        categories = [category]
    else:
        current = db.scalars(
            select(PlayerWeakness)
            .where(PlayerWeakness.user_id == user_id)
            .order_by(PlayerWeakness.score.desc())
            .limit(10)
        ).all()
        categories = [item.category for item in current]

    current_by_category = {
        item.category: item
        for item in db.scalars(
            select(PlayerWeakness).where(
                PlayerWeakness.user_id == user_id,
                PlayerWeakness.category.in_(categories) if categories else False,
            )
        ).all()
    } if categories else {}

    payload = []
    for item_category in categories:
        snapshots = db.scalars(
            select(WeaknessSnapshot)
            .where(
                WeaknessSnapshot.user_id == user_id,
                WeaknessSnapshot.category == item_category,
            )
            .order_by(WeaknessSnapshot.captured_at.desc())
            .limit(limit)
        ).all()
        chronological = list(reversed(snapshots))
        long_term_delta = round(
            chronological[-1].score - chronological[0].score,
            4,
        ) if len(chronological) >= 2 else 0.0
        current = current_by_category.get(item_category)
        payload.append({
            "category": item_category,
            "current_score": current.score if current else (chronological[-1].score if chronological else None),
            "current_trend": current.trend if current else 0.0,
            "direction": _trend_direction(long_term_delta),
            "delta": long_term_delta,
            "snapshots": [
                {
                    "score": snapshot.score,
                    "confidence": snapshot.confidence,
                    "sample_size": snapshot.sample_size,
                    "captured_at": snapshot.captured_at.isoformat(),
                }
                for snapshot in chronological
            ],
        })

    return {"categories": payload}


@router.get("/openings")
def openings(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
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
