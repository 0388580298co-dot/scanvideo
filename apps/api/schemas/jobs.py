from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    DOWNLOADING = "DOWNLOADING"
    VALIDATING = "VALIDATING"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSLATING = "TRANSLATING"
    SCRIPTED = "SCRIPTED"
    SYNTHESIZING = "SYNTHESIZING"
    RENDERING = "RENDERING"
    QC = "QC"
    COMPLETED = "COMPLETED"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class CreateJobRequest(BaseModel):
    source_url: str = Field(min_length=8, max_length=2048)
    target_language: str = Field(default="vi", min_length=2, max_length=10)
    min_duration: float | None = Field(default=None, ge=0)
    max_duration: float | None = Field(default=None, gt=0)
    auto_publish: bool = False

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value.startswith(("https://", "http://")):
            raise ValueError("source_url must be an http(s) URL")
        return value


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    source_url: str
    target_language: str
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    output_path: str | None = None
    error: str | None = None
    auto_publish: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
