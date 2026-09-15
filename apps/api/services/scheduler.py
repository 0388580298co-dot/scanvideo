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
        when = request.scheduled_at
        if when.tzinfo is None:
            raise SchedulingError("scheduled_at must include a timezone")
        when = when.astimezone(timezone.utc)
        with SessionLocal() as session:
            job = session.get(Job, request.job_id)
            if job is None:
                raise SchedulingError("Job not found")
            if job.status not in {"COMPLETED", "SCHEDULED", "PUBLISHED"}:
                raise SchedulingError("Only completed jobs can be scheduled")
            if not job.output_path:
                raise SchedulingError("Job has no output media")

            account_id = request.account_id
            if account_id is not None:
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

            post = ScheduledPost(
                job_id=request.job_id,
                platform_account_id=account_id,
                scheduled_at=when,
                status="SCHEDULED",
            )
            session.add(post)
            job.status = "SCHEDULED"
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(post)
            return self._response(post, request)

    def list(self) -> list[ScheduleResponse]:
        with SessionLocal() as session:
            rows = session.scalars(select(ScheduledPost).order_by(ScheduledPost.scheduled_at)).all()
            return [self._response(row) for row in rows]

    def due(self, now: datetime | None = None) -> list[int]:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with SessionLocal() as session:
            rows = session.scalars(
                select(ScheduledPost).where(
                    ScheduledPost.status == "SCHEDULED",
                    ScheduledPost.scheduled_at <= current,
                ).with_for_update(skip_locked=True)
            ).all()
            ids = [row.id for row in rows]
            for row in rows:
                row.status = "PROCESSING"
            session.commit()
            return ids

    def mark_failed(self, post_id: int, error: str) -> None:
        with SessionLocal() as session:
            post = session.get(ScheduledPost, post_id)
            if post:
                post.status = "FAILED"
                session.commit()

    @staticmethod
    def _response(post: ScheduledPost, request: ScheduleCreateRequest | None = None) -> ScheduleResponse:
        return ScheduleResponse(
            id=post.id,
            job_id=post.job_id,
            platform=request.platform if request else "",
            scheduled_at=post.scheduled_at,
            status=post.status,
            title=request.title if request else "",
            description=request.description if request else "",
            account_id=post.platform_account_id,
        )


scheduler_service = SchedulerService()
