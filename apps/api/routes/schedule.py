from fastapi import APIRouter, HTTPException

from apps.api.schemas.scheduling import ScheduleCreateRequest, ScheduleResponse
from apps.api.services.scheduler import SchedulingError, scheduler_service

router = APIRouter(prefix="/api/v1/schedule", tags=["schedule"])


@router.post("", response_model=ScheduleResponse, status_code=201)
def create_schedule(request: ScheduleCreateRequest) -> ScheduleResponse:
    try:
        return scheduler_service.create(request)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[ScheduleResponse])
def list_schedule() -> list[ScheduleResponse]:
    return scheduler_service.list()


@router.post("/{schedule_id}/cancel", response_model=ScheduleResponse)
def cancel_schedule(schedule_id: int) -> ScheduleResponse:
    try:
        return scheduler_service.cancel(schedule_id)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
