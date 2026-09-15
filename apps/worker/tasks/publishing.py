from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from apps.api.db.base import SessionLocal
from apps.api.db.models import Job, PublishedPost, ScheduledPost
from apps.worker.celery_app import celery_app
from apps.worker.services.publishers.tiktok import TikTokPublisher
from apps.worker.services.publishers.youtube import YouTubePublisher


class PublishingError(RuntimeError):
    pass


def _publish(post: ScheduledPost, job: Job) -> dict:
    if not job.output_path:
        raise PublishingError("Job has no output media")
    path = Path(job.output_path)
    if not path.exists() or path.stat().st_size == 0:
        raise PublishingError("Output media is missing")
    if post.platform == "youtube":
        return YouTubePublisher(
            Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "/secrets/client_secret.json")),
            Path(os.getenv("YOUTUBE_TOKEN_FILE", "/secrets/youtube_token.json")),
        ).upload(path, post.title, post.description, privacy=post.privacy_level or "private")
    if post.platform == "tiktok":
        return TikTokPublisher(os.getenv("TIKTOK_ACCESS_TOKEN") or None).publish_file(
            path, post.title, privacy_level=post.privacy_level or "SELF_ONLY"
        )
    raise PublishingError(f"Unsupported platform: {post.platform}")


@celery_app.task(
    bind=True,
    name="scanvideo.publish_scheduled",
    max_retries=2,
    autoretry_for=(TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def publish_scheduled(self, post_id: int) -> dict:
    with SessionLocal() as session:
        post = session.get(ScheduledPost, post_id)
        if post is None:
            raise PublishingError("Scheduled post not found")
        if post.status != "PROCESSING":
            return {"post_id": post_id, "status": post.status}
        job = session.get(Job, post.job_id)
        if job is None:
            raise PublishingError("Job not found")
        job_id = post.job_id
        platform = post.platform
        title = post.title
        description = post.description
        privacy = post.privacy_level
        output_path = job.output_path

    try:
        # Work from a detached snapshot so the SQLAlchemy session never crosses
        # the network/upload boundary.
        snapshot = Job(id=job_id, source_url="", status="PUBLISHED", output_path=output_path)
        snapshot.output_path = output_path
        post_snapshot = ScheduledPost(id=post_id, job_id=job_id, platform=platform, title=title, description=description, privacy_level=privacy)
        result = _publish(post_snapshot, snapshot)
        external_id = str(result.get("id") or result.get("data", {}).get("publish_id") or "")
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            db_post = session.get(ScheduledPost, post_id)
            db_job = session.get(Job, job_id)
            if db_post is None or db_job is None:
                raise PublishingError("Scheduled post disappeared during publish")
            db_post.status = "PUBLISHED"
            db_post.error = None
            db_job.status = "PUBLISHED"
            db_job.updated_at = now
            session.add(
                PublishedPost(
                    scheduled_post_id=post_id,
                    platform=platform,
                    external_id=external_id,
                    published_at=now,
                    metrics={"response": result},
                )
            )
            session.commit()
        return {"post_id": post_id, "status": "PUBLISHED", "external_id": external_id}
    except (TimeoutError, ConnectionError) as exc:
        # Celery will retry these transient failures. Do not mark the post
        # permanently failed before the retry budget is exhausted.
        retries = getattr(self.request, "retries", 0)
        if retries >= self.max_retries:
            with SessionLocal() as session:
                db_post = session.get(ScheduledPost, post_id)
                if db_post:
                    db_post.status = "FAILED"
                    db_post.error = str(exc)[:4000]
                    session.commit()
        else:
            with SessionLocal() as session:
                db_post = session.get(ScheduledPost, post_id)
                if db_post:
                    db_post.error = f"Temporary publishing error; retry {retries + 1}/{self.max_retries}"
                    session.commit()
        raise
    except Exception as exc:
        with SessionLocal() as session:
            db_post = session.get(ScheduledPost, post_id)
            if db_post:
                db_post.status = "FAILED"
                db_post.error = str(exc)[:4000]
                session.commit()
        raise


@celery_app.task(name="scanvideo.dispatch_due_posts")
def dispatch_due_posts() -> dict:
    from apps.api.services.scheduler import scheduler_service
    ids = scheduler_service.due()
    for post_id in ids:
        publish_scheduled.delay(post_id)
    return {"dispatched": len(ids), "post_ids": ids}
