from __future__ import annotations

import json
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import current_user_id
from app.db.session import SessionLocal, get_db
from app.models.entities import AnalysisJob

router = APIRouter(prefix="/analysis-jobs", tags=["analysis"])


@router.get("/{job_id}")
def job_status(job_id: str, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.user_id == user_id))
    if not job:
        raise HTTPException(404, "Job not found")
    return {"id": job.id, "status": job.status, "progress": job.progress, "error": job.error}


@router.get("/{job_id}/events")
def job_events(job_id: str, user_id: str = Depends(current_user_id)):
    def stream():
        last_payload = None
        while True:
            db = SessionLocal()
            try:
                job = db.scalar(select(AnalysisJob).where(
                    AnalysisJob.id == job_id,
                    AnalysisJob.user_id == user_id,
                ))
                if not job:
                    yield "event: error\ndata: {\"detail\":\"Job not found\"}\n\n"
                    return
                payload = json.dumps({
                    "id": job.id,
                    "status": job.status,
                    "progress": job.progress,
                    "error": job.error,
                })
                if payload != last_payload:
                    yield f"event: progress\ndata: {payload}\n\n"
                    last_payload = payload
                if job.status in {"complete", "failed"}:
                    yield f"event: done\ndata: {payload}\n\n"
                    return
            finally:
                db.close()
            time.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
