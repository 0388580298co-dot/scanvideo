from __future__ import annotations

from pathlib import Path
from threading import Lock

from apps.api.core.config import settings
from apps.api.schemas.jobs import CreateJobRequest, JobResponse, JobStatus


class JobStore:
    def __init__(self, root: Path) -> None:
        self.root = root / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def create(self, request: CreateJobRequest) -> JobResponse:
        import uuid
        job = JobResponse(
            job_id=uuid.uuid4().hex,
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

    def list_all(self) -> list[dict]:
        result: list[dict] = []
        for path in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                result.append(JobResponse.model_validate_json(path.read_text(encoding="utf-8")).model_dump(mode="json"))
            except Exception:
                continue
        return result

    def update(self, job_id: str, **changes: object) -> JobResponse:
        with self._lock:
            current = self.get(job_id)
            if current is None:
                raise KeyError(job_id)
            updated = current.model_copy(update=changes)
            self._write(updated)
            return updated

    def _write(self, job: JobResponse) -> None:
        (self.root / f"{job.job_id}.json").write_text(job.model_dump_json(indent=2), encoding="utf-8")


job_store = JobStore(settings.media_root)
