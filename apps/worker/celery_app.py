import os

from celery import Celery


celery_app = Celery(
    "scanvideo",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    include=["apps.worker.tasks.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=False,
)


@celery_app.task(name="scanvideo.health_check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
