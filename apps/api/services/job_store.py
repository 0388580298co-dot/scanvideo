from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from apps.api.db.base import SessionLocal
from apps.api.db.models import Job, SourceMedia
from apps.api.schemas.jobs import CreateJobRequest, JobResponse, JobStatus


class JobStore:
    """PostgreSQL-backed job repository."""

    def create(self, request: CreateJobRequest) -> JobResponse:
        now = datetime.now(timezone.utc)
        record = Job(
            id=uuid.uuid4().hex,
            status=JobStatus.QUEUED.value,
            source_url=request.source_url,
            target_language=request.target_language,
            auto_publish=request.auto_publish,
            created_at=now,
            updated_at=now,
            message="Job queued",
        )
        with SessionLocal() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._response(record)

    def get(self, job_id: str) -> JobResponse | None:
        with SessionLocal() as session:
            record = session.get(Job, job_id)
            return self._response(record) if record else None

    def list_all(self) -> list[dict]:
        with SessionLocal() as session:
            records = session.scalars(select(Job).order_by(Job.created_at.desc())).all()
            return [self._response(record).model_dump(mode="json") for record in records]

    def update(self, job_id: str, **changes: object) -> JobResponse:
        with SessionLocal() as session:
            record = session.get(Job, job_id)
            if record is None:
                raise KeyError(job_id)
            for key, value in changes.items():
                if key == "status" and isinstance(value, JobStatus):
                    value = value.value
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(record)
            return self._response(record)

    def find_source_by_fingerprint(self, fingerprint: str) -> SourceMedia | None:
        with SessionLocal() as session:
            return session.scalar(select(SourceMedia).where(SourceMedia.fingerprint == fingerprint))

    def register_source_media(
        self,
        job_id: str,
        source_url: str,
        fingerprint: str,
        path: str,
        duration: float,
        width: int,
        height: int,
    ) -> None:
        record = SourceMedia(
            job_id=job_id,
            source_url=source_url,
            fingerprint=fingerprint,
            path=path,
            duration=duration,
            width=width,
            height=height,
        )
        with SessionLocal() as session:
            session.add(record)
            session.commit()

    @staticmethod
    def _response(record: Job) -> JobResponse:
        return JobResponse(
            job_id=record.id,
            status=JobStatus(record.status),
            source_url=record.source_url,
            target_language=record.target_language,
            progress=record.progress,
            message=record.message,
            output_path=record.output_path,
            error=record.error,
            auto_publish=record.auto_publish,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


job_store = JobStore()
