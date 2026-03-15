from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "anima_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=270,  # 4.5 minutes soft limit
    worker_concurrency=2,      # Limit to 2 concurrent renders to save CPU/RAM
    worker_max_tasks_per_child=10, # Restart worker after 10 tasks to prevent memory leaks
)
