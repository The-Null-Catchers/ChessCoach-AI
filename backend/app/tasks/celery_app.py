from celery import Celery

from app.core.config import settings

celery = Celery(
    "chesscoach",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.analysis", "app.tasks.email", "app.tasks.reports"],
)
celery.conf.task_track_started = True
celery.conf.task_acks_late = True
celery.conf.worker_prefetch_multiplier = 1
celery.conf.task_routes = {
    "app.tasks.analysis.*": {"queue": "analysis"},
    "app.tasks.email.*": {"queue": "notifications"},
    "app.tasks.reports.*": {"queue": "notifications"},
}
celery.conf.beat_schedule = {
    "weekly-player-reports": {
        "task": "app.tasks.reports.generate_all_weekly_reports",
        "schedule": 604800.0,
    },
}
