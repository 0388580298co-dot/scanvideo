from datetime import datetime

import pytest
from pydantic import ValidationError

from apps.api.schemas.scheduling import ScheduleCreateRequest


def test_schedule_requires_timezone() -> None:
    request = ScheduleCreateRequest(job_id="abc", platform="youtube", scheduled_at=datetime.fromisoformat("2026-09-15T19:00:00+07:00"))
    assert request.scheduled_at.tzinfo is not None


def test_schedule_rejects_unknown_platform() -> None:
    with pytest.raises(ValidationError):
        ScheduleCreateRequest(job_id="abc", platform="facebook", scheduled_at=datetime.fromisoformat("2026-09-15T19:00:00+07:00"))
