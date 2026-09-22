from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, coaching, games, jobs, training
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(games.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(coaching.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/ready")
def ready():
    return {"api": "ok"}
