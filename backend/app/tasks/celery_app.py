from celery import Celery
from app.core.config import settings

celery = Celery('chesscoach', broker=settings.redis_url, backend=settings.redis_url)
celery.conf.task_track_started = True
celery.conf.task_acks_late = True
celery.conf.worker_prefetch_multiplier = 1
celery.conf.task_routes = {'app.tasks.analysis.*': {'queue': 'analysis'}}
