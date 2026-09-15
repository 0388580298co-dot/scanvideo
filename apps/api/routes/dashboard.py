from __future__ import annotations

from fastapi import APIRouter

from apps.api.services.job_store import job_store

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary() -> dict:
    jobs = job_store.list_all()
    counts: dict[str, int] = {}
    for job in jobs:
        status = str(job.get("status", "UNKNOWN"))
        counts[status] = counts.get(status, 0) + 1
    return {"total_jobs": len(jobs), "by_status": counts}


@router.get("/jobs")
def jobs() -> list[dict]:
    return job_store.list_all()
