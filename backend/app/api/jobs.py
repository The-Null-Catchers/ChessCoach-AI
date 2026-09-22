from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.games import current_user_id
from app.db.session import get_db
from app.models.entities import AnalysisJob

router = APIRouter(prefix='/analysis-jobs', tags=['analysis'])

@router.get('/{job_id}')
def job_status(job_id: str, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.user_id == user_id))
    if not job: raise HTTPException(404, 'Job not found')
    return {'id': job.id, 'status': job.status, 'progress': job.progress, 'error': job.error}
