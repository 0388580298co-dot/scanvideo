from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ScheduleCreateRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    platform: str = Field(pattern=r"^(youtube|tiktok)$")
    scheduled_at: datetime
    title: str = Field(default="", max_length=2200)
    description: str = Field(default="", max_length=5000)
    privacy_level: str | None = None
    account_id: int | None = None


class ScheduleResponse(BaseModel):
    id: int
    job_id: str
    platform: str
    scheduled_at: datetime
    status: str
    title: str
    description: str
    account_id: int | None = None
