from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.feature_flags import enabled_flags

router = APIRouter(prefix="/features", tags=["features"])


@router.get("")
def features(db: Session = Depends(get_db)):
    flags = enabled_flags(db)
    db.commit()
    return flags
