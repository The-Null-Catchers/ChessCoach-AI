from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, coaching, games, health, jobs, training
from app.core.config import settings
from app.core.observability import configure_observability

app = FastAPI(title=settings.app_name, version="0.8.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
configure_observability(app)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(games.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(coaching.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
