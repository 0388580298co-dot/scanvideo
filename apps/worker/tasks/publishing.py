from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from apps.api.core.config import settings
from apps.api.db.base import SessionLocal
from apps.api.db.models import Job, PlatformAccount, PublishAttempt, PublishedPost, ScheduledPost
from apps.worker.celery_app import celery_app
from apps.worker.services.publishers.tiktok import TikTokPublisher
from apps.worker.services.publishers.youtube import YouTubePublisher


class PublishingError(RuntimeError):
    pass


class PublishTerminalError(PublishingError):
    """The provider has definitively rejected an already-submitted publication."""


def _credential_path(value: str | None) -> Path | None:
    """Resolve an account credential reference without allowing paths outside secrets."""
    if not value:
        return None
    root = settings.secret_root.resolve()
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise PublishingError("Credential reference must point inside SECRET_ROOT")
    return resolved


def _publish(post: ScheduledPost, job: Job, account: PlatformAccount | None = None) -> dict:
    if not job.output_path:
        raise PublishingError("Job has no output media")
    path = Path(job.output_path)
    if not path.exists() or path.stat().st_size == 0:
        raise PublishingError("Output media is missing")

    credential_ref = _credential_path(account.credential_ref if account else None)
    if post.platform == "youtube":
        token_file = credential_ref or Path(os.getenv("YOUTUBE_TOKEN_FILE", "/secrets/youtube_token.json"))
        return YouTubePublisher(
            Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "/secrets/client_secret.json")),
            token_file,
        ).upload(path, post.title, post.description, privacy=post.privacy_level or "private")
    if post.platform == "tiktok":
        token_file = credential_ref or Path(
            os.getenv("TIKTOK_TOKEN_FILE", "/secrets/oauth/tiktok_token.json")
        )
        return TikTokPublisher(token_file=token_file).publish_file(
            path, post.title, privacy_level=post.privacy_level or "SELF_ONLY"
        )
    raise PublishingError(f"Unsupported platform: {post.platform}")


def _publisher(account: PlatformAccount, platform: str):
    credential_ref = _credential_path(account.credential_ref)
    if platform == "youtube":
        return YouTubePublisher(
            Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "/secrets/client_secret.json")),
            credential_ref or Path(os.getenv("YOUTUBE_TOKEN_FILE", "/secrets/youtube_token.json")),
        )
    if platform == "tiktok":
        return TikTokPublisher(token_file=credential_ref or Path(
            os.getenv("TIKTOK_TOKEN_FILE", "/secrets/oauth/tiktok_token.json")
        ))
    raise PublishingError(f"Unsupported platform: {platform}")


def _snapshot(session, post_id: int):
    post = session.get(ScheduledPost, post_id)
    if post is None:
        raise PublishingError("Scheduled post not found")
    job = session.get(Job, post.job_id)
    if job is None:
        raise PublishingError("Job not found")
    account = session.get(PlatformAccount, post.platform_account_id)
    if account is None or not account.enabled or account.platform != post.platform:
        raise PublishingError("Publishing account is missing or disabled")
    return (
        post.job_id,
        post.platform,
        post.title,
        post.description,
        post.privacy_level,
        job.output_path,
        account.id,
        account.platform,
        account.account_name,
        account.credential_ref,
    )


def _finalize_published(session, post_id: int, job_id: str, platform: str, external_id: str, response: dict) -> None:
    now = datetime.now(timezone.utc)
    post = session.get(ScheduledPost, post_id)
    job = session.get(Job, job_id)
    attempt = session.query(PublishAttempt).filter(PublishAttempt.scheduled_post_id == post_id).first()
    if post is None or job is None:
        raise PublishingError("Scheduled post disappeared during reconciliation")
    if attempt:
        attempt.status = "COMPLETE"
        attempt.external_id = external_id
        attempt.provider_status = "PUBLISH_COMPLETE"
        attempt.error = None
        attempt.updated_at = now
    existing = session.query(PublishedPost).filter(PublishedPost.scheduled_post_id == post_id).first()
    if not existing:
        session.add(
            PublishedPost(
                scheduled_post_id=post_id,
                platform=platform,
                external_id=external_id,
                published_at=now,
                metrics={"response": response},
            )
        )
    post.status = "PUBLISHED"
    post.error = None
    job.status = "PUBLISHED"
    job.updated_at = now
    session.commit()


def _reconcile_existing(post_id: int) -> bool:
    """Finalize a known provider submission; never re-upload an ambiguous submission."""
    with SessionLocal() as session:
        snapshot = _snapshot(session, post_id)
        job_id, platform, _, _, _, _, account_id, account_platform, account_name, credential_ref = snapshot
        attempt = session.query(PublishAttempt).filter(PublishAttempt.scheduled_post_id == post_id).first()
        if not attempt or not attempt.external_id:
            return False
        account = PlatformAccount(
            id=account_id,
            platform=account_platform,
            account_name=account_name,
            credential_ref=credential_ref,
            enabled=True,
        )
        provider = _publisher(account, platform)
        if platform == "youtube":
            existing = provider.lookup(attempt.external_id)
            if existing:
                _finalize_published(session, post_id, job_id, platform, attempt.external_id, existing)
                return True
            attempt.provider_status = "NOT_FOUND"
            attempt.updated_at = datetime.now(timezone.utc)
            session.commit()
            raise ConnectionError("youtube publish submission is not visible yet")

        status_payload = provider.publish_status(attempt.external_id)
        status = str(status_payload.get("data", {}).get("status") or "").upper()
        attempt.provider_status = status[:64] or None
        attempt.updated_at = datetime.now(timezone.utc)
        if status in {"PUBLISH_COMPLETE", "PUBLISHED", "COMPLETE"}:
            _finalize_published(session, post_id, job_id, platform, attempt.external_id, status_payload)
            return True
        if status in {"FAILED", "ERROR", "CANCELLED"}:
            attempt.status = "FAILED"
            attempt.error = f"Provider terminal status: {status}"
            session.commit()
            raise PublishTerminalError(attempt.error)
        session.commit()
        raise ConnectionError(f"{platform} publish status is not terminal: {status or 'UNKNOWN'}")


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
        existing = session.query(PublishedPost).filter(PublishedPost.scheduled_post_id == post_id).first()
        if existing:
            return {"post_id": post_id, "status": "PUBLISHED", "external_id": existing.external_id}
        attempt = session.query(PublishAttempt).filter(PublishAttempt.scheduled_post_id == post_id).first()

    try:
        if attempt and attempt.external_id:
            if _reconcile_existing(post_id):
                return {"post_id": post_id, "status": "PUBLISHED", "external_id": attempt.external_id}

        with SessionLocal() as session:
            job_id, platform, title, description, privacy, output_path, account_id, account_platform, account_name, credential_ref = _snapshot(session, post_id)
            if not output_path:
                raise PublishingError("Job has no output media")
            attempt = session.query(PublishAttempt).filter(PublishAttempt.scheduled_post_id == post_id).first()
            if attempt is None:
                attempt = PublishAttempt(scheduled_post_id=post_id, platform=platform, status="STARTED")
                session.add(attempt)
                session.commit()
            job_snapshot = Job(id=job_id, source_url="", status="PUBLISHED", output_path=output_path)
            post_snapshot = ScheduledPost(id=post_id, job_id=job_id, platform=platform, title=title, description=description, privacy_level=privacy)
            account_snapshot = PlatformAccount(id=account_id, platform=account_platform, account_name=account_name, credential_ref=credential_ref, enabled=True)

        result = _publish(post_snapshot, job_snapshot, account_snapshot)
        external_id = str(result.get("id") or result.get("data", {}).get("publish_id") or "")
        if not external_id:
            raise PublishingError("Provider returned no external publish identifier")

        with SessionLocal() as session:
            db_attempt = session.query(PublishAttempt).filter(PublishAttempt.scheduled_post_id == post_id).first()
            if db_attempt is None:
                raise PublishingError("Publish attempt record disappeared during upload")
            db_attempt.external_id = external_id
            db_attempt.status = "SUBMITTED"
            db_attempt.provider_status = "SUBMITTED"
            db_attempt.error = None
            db_attempt.updated_at = datetime.now(timezone.utc)
            if platform == "youtube":
                _finalize_published(session, post_id, job_id, platform, external_id, result)
                return {"post_id": post_id, "status": "PUBLISHED", "external_id": external_id}
            session.commit()

        reconcile_publish.apply_async(args=[post_id], countdown=20)
        return {"post_id": post_id, "status": "PROCESSING", "external_id": external_id}
    except (TimeoutError, ConnectionError) as exc:
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


@celery_app.task(bind=True, name="scanvideo.reconcile_publish", max_retries=10)
def reconcile_publish(self, post_id: int) -> dict:
    try:
        with SessionLocal() as session:
            post = session.get(ScheduledPost, post_id)
            if post is None:
                raise PublishingError("Scheduled post not found")
            if post.status == "PUBLISHED":
                return {"post_id": post_id, "status": "PUBLISHED"}
        if _reconcile_existing(post_id):
            return {"post_id": post_id, "status": "PUBLISHED"}
        return {"post_id": post_id, "status": "NO_SUBMISSION"}
    except PublishTerminalError as exc:
        with SessionLocal() as session:
            attempt = session.query(PublishAttempt).filter(PublishAttempt.scheduled_post_id == post_id).first()
            post = session.get(ScheduledPost, post_id)
            if attempt:
                attempt.status = "FAILED"
                attempt.error = str(exc)[:4000]
                attempt.updated_at = datetime.now(timezone.utc)
            if post:
                post.status = "FAILED"
                post.error = str(exc)[:4000]
            session.commit()
        return {"post_id": post_id, "status": "FAILED"}
    except ConnectionError as exc:
        if self.request.retries >= self.max_retries:
            with SessionLocal() as session:
                post = session.get(ScheduledPost, post_id)
                attempt = session.query(PublishAttempt).filter(PublishAttempt.scheduled_post_id == post_id).first()
                if post:
                    post.status = "FAILED"
                    post.error = str(exc)[:4000]
                if attempt:
                    attempt.status = "FAILED"
                    attempt.error = str(exc)[:4000]
                    attempt.updated_at = datetime.now(timezone.utc)
                session.commit()
            raise
        raise self.retry(exc=exc, countdown=min(60, 10 + self.request.retries * 5))
    except Exception:
        raise


@celery_app.task(name="scanvideo.dispatch_due_posts")
def dispatch_due_posts() -> dict:
    from apps.api.services.scheduler import scheduler_service

    ids = scheduler_service.due()
    for post_id in ids:
        publish_scheduled.delay(post_id)
    return {"dispatched": len(ids), "post_ids": ids}
