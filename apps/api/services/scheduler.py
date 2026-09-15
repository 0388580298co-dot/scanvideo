from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from apps.api.db.base import SessionLocal
from apps.api.db.models import Job, PlatformAccount, ScheduledPost
from apps.api.schemas.scheduling import ScheduleCreateRequest, ScheduleResponse


class SchedulingError(RuntimeError):
    pass


class SchedulerService:
    def create(self, request: ScheduleCreateRequest) -> ScheduleResponse:
        if request.scheduled_at.tzinfo is None:
            raise SchedulingError("scheduled_at must include a timezone")
        when = request.scheduled_at.astimezone(timezone.utc)
        with SessionLocal() as session:
            job = session.get(Job, request.job_id)
            if job is None:
                raise SchedulingError("Job not found")
            if job.status not in {"COMPLETED", "SCHEDULED", "PUBLISHED"}:
                raise SchedulingError("Only completed jobs can be scheduled")
            if not job.output_path:
                raise SchedulingError("Job has no output media")
            account_id = request.account_id or session.scalar(
                select(PlatformAccount.id)
                .where(
                    PlatformAccount.platform == request.platform,
                    PlatformAccount.enabled.is_(True),
                )
                .order_by(PlatformAccount.id)
                .limit(1)
            )
            if account_id is None:
                raise SchedulingError("No enabled platform account is configured")
            account = session.get(PlatformAccount, account_id)
            if account is None or not account.enabled or account.platform != request.platform:
                raise SchedulingError("Invalid platform account")
            duplicate = session.scalar(
                select(ScheduledPost).where(
                    ScheduledPost.job_id == request.job_id,
                    ScheduledPost.platform == request.platform,
                    ScheduledPost.scheduled_at == when,
                    ScheduledPost.status.in_(["SCHEDULED", "PROCESSING"]),
                )
            )
            if duplicate:
                return self._response(duplicate)
            package = job.content_package or {}
            title = request.title or str(package.get("title", "ScanVideo"))
            description = request.description or str(package.get("description", ""))
            privacy = request.privacy_level or (
                "private" if request.platform == "youtube" else "SELF_ONLY"
            )
            post = ScheduledPost(
                job_id=request.job_id,
                platform_account_id=account_id,
                platform=request.platform,
                title=title,
                description=description,
                privacy_level=privacy,
                scheduled_at=when,
                status="SCHEDULED",
            )
            session.add(post)
            job.status = "SCHEDULED"
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(post)
            return self._response(post)

    def list(self) -> list[ScheduleResponse]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(ScheduledPost).order_by(ScheduledPost.scheduled_at)
            ).all()
            return [self._response(row) for row in rows]

    def cancel(self, schedule_id: int) -> ScheduleResponse:
        with SessionLocal() as session:
            post = session.get(ScheduledPost, schedule_id)
            if post is None:
                raise SchedulingError("Scheduled post not found")
            if post.status not in {"SCHEDULED"}:
                raise SchedulingError("Only scheduled posts can be cancelled")
            post.status = "CANCELLED"
            job = session.get(Job, post.job_id)
            if job and job.status == "SCHEDULED":
                remaining = session.scalar(
                    select(ScheduledPost.id)
                    .where(
                        ScheduledPost.job_id == post.job_id,
                        ScheduledPost.status.in_(["SCHEDULED", "PROCESSING"]),
                        ScheduledPost.id != post.id,
                    )
                    .limit(1)
                )
                if remaining is None:
                    job.status = "COMPLETED"
                    job.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(post)
            return self._response(post)

    def due(self, now: datetime | None = None) -> list[int]:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with SessionLocal() as session:
            rows = session.scalars(
                select(ScheduledPost)
                .where(
                    ScheduledPost.status == "SCHEDULED",
                    ScheduledPost.scheduled_at <= current,
                )
                .with_for_update(skip_locked=True)
            ).all()
            ids = [row.id for row in rows]
            for row in rows:
                row.status = "PROCESSING"
            session.commit()
            return ids

    @staticmethod
    def _response(post: ScheduledPost) -> ScheduleResponse:
        return ScheduleResponse(
            id=post.id,
            job_id=post.job_id,
            platform=post.platform,
            scheduled_at=post.scheduled_at,
            status=post.status,
            title=post.title,
            description=post.description,
            account_id=post.platform_account_id,
        )


scheduler_service = SchedulerService()
