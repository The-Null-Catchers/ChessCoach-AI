from celery import Celery
from app.core.config import settings

celery = Celery(\n    'chesscoach',\n    broker=settings.redis_url,\n    backend=settings.redis_url,\n    include=['app.tasks.analysis', 'app.tasks.email'],\n)
celery.conf.task_track_started = True
celery.conf.task_acks_late = True
celery.conf.worker_prefetch_multiplier = 1
celery.conf.task_routes = {
    'app.tasks.analysis.*': {'queue': 'analysis'},
    'app.tasks.email.*': {'queue': 'notifications'},
}
