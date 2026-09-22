from fastapi import FastAPI
from app.api import auth, coaching, games, jobs
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.2.0")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(games.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(coaching.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/ready")
def ready():
    return {"api": "ok"}
