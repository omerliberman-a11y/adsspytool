from celery import Celery

from adspy.config import get_settings

settings = get_settings()
app = Celery(
    "adspy",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["adspy.workers.tasks"],
)
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
