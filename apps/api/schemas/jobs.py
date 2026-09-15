from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    DOWNLOADING = "DOWNLOADING"
    VALIDATING = "VALIDATING"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSLATING = "TRANSLATING"
    SYNTHESIZING = "SYNTHESIZING"
    RENDERING = "RENDERING"
    QC = "QC"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CreateJobRequest(BaseModel):
    source_url: str = Field(min_length=8)
    target_language: str = Field(default="vi", min_length=2, max_length=10)
    min_duration: float | None = Field(default=None, ge=0)
    max_duration: float | None = Field(default=None, gt=0)
    auto_publish: bool = False


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    source_url: str
    target_language: str
    progress: int = 0
    message: str = ""
    output_path: str | None = None
    error: str | None = None
