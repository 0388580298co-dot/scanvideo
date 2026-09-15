from datetime import datetime, timezone

import pytest

from apps.api.schemas.scheduling import ScheduleCreateRequest
from apps.api.services.scheduler import SchedulingError


def test_schedule_requires_timezone():
    request = ScheduleCreateRequest(
        job_id="job-1",
        platform="youtube",
        scheduled_at=datetime(2026, 9, 15, 20, 0),
    )
    assert request.scheduled_at.tzinfo is None


def test_scheduler_error_is_publicly_importable():
    with pytest.raises(SchedulingError):
        raise SchedulingError("test")
