from fastapi import APIRouter, HTTPException

from apps.api.schemas.jobs import CreateJobRequest, JobResponse
from apps.api.services.job_store import job_store
from apps.worker.tasks.pipeline import run_pipeline

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=202)
def create_job(request: CreateJobRequest) -> JobResponse:
    job = job_store.create(request)
    run_pipeline.delay(
        job.job_id,
        request.source_url,
        request.target_language,
        request.min_duration,
        request.max_duration,
        request.auto_publish,
    )
    return job


@router.get("", response_model=list[JobResponse])
def list_jobs() -> list[JobResponse]:
    return [JobResponse.model_validate(item) for item in job_store.list_all()]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/status", response_model=JobResponse)
def get_job_status(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
