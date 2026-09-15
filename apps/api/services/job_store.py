from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from apps.api.schemas.jobs import CreateJobRequest, JobResponse, JobStatus
from apps.api.core.config import settings


class JobStore:
    def __init__(self, root: Path) -> None:
        self.root = root / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def create(self, request: CreateJobRequest) -> JobResponse:
        import uuid

        job_id = uuid.uuid4().hex
        job = JobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            source_url=request.source_url,
            target_language=request.target_language,
            message="Job queued",
        )
        self._write(job)
        return job

    def get(self, job_id: str) -> JobResponse | None:
        path = self.root / f"{job_id}.json"
        if not path.exists():
            return None
        return JobResponse.model_validate_json(path.read_text(encoding="utf-8"))

    def update(self, job_id: str, **changes: object) -> JobResponse:
        with self._lock:
            current = self.get(job_id)
            if current is None:
                raise KeyError(job_id)
            updated = current.model_copy(update=changes)
            self._write(updated)
            return updated

    def _write(self, job: JobResponse) -> None:
        path = self.root / f"{job.job_id}.json"
        path.write_text(job.model_dump_json(indent=2), encoding="utf-8")


job_store = JobStore(settings.media_root)
