from fastapi import APIRouter, Depends, Path
from api.schemas import TimetableResponseSchema, ERROR_RESPONSES
from application.services.timetable_service import TimetableService
from api.dependencies import get_timetable_service

router = APIRouter(prefix="/routes", tags=["Timetable"])

@router.get(
    "/{route_id}/timetable", 
    response_model=TimetableResponseSchema,
    summary="Get Route Timetable",
    description="Fetches the full departure timetable for a specific route ID from the external scraper.",
    responses=ERROR_RESPONSES
)
async def get_timetable(
    route_id: str = Path(..., description="The unique route identifier.", json_schema_extra={"examples": ["route_12345"]}),
    service: TimetableService = Depends(get_timetable_service)
):
    try:
        return await service.get_timetable(route_id)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc)) from exc

from typing import Optional
from fastapi import Query

@router.get("/{route_id}/legs/{leg_index}/timetable", response_model=TimetableResponseSchema)
async def get_passenger_leg_timetable(
    route_id: str,
    leg_index: int = Path(..., ge=0),
    cursor: int = Query(0, ge=0),
    date: str | None = Query(None, pattern=r'^\d{4}-\d{2}-\d{2}$'),
    not_before: str | None = Query(None),
    service: TimetableService = Depends(get_timetable_service),
):
    try:
        return await service.get_leg_timetable(route_id, leg_index, cursor, service_date=date, not_before=not_before)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc)) from exc

@router.get(
    "/{route_id}/segments/{segment_index}/timetable", 
    response_model=TimetableResponseSchema,
    summary="Get Leg Timetable",
    description="Fetches the departure timetable for a specific leg (segment) of a route.",
    responses=ERROR_RESPONSES
)
async def get_segment_timetable(
    route_id: str = Path(..., description="The unique route identifier."),
    segment_index: int = Path(..., description="The 0-based index of the route segment."),
    timetable_id: Optional[str] = Query(None, description="Optional JR Odekake timetable ID. If not provided, dynamic lookup will fail."),
    service: TimetableService = Depends(get_timetable_service)
):
    try:
        timetable = await service.get_segment_timetable(route_id, segment_index, timetable_id)
        return timetable
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404 if "not found" in str(e) else 400, detail=str(e))

@router.get(
    "/{route_id}/segments/{segment_index}/platform", 
    response_model=dict,
    summary="Get Platform for Selected Train",
    description="Reads the exact selected timetable departure's platform without fuzzy route searches.",
    responses=ERROR_RESPONSES
)
async def get_segment_platform(
    route_id: str = Path(..., description="The unique route identifier."),
    segment_index: int = Path(..., description="The 0-based index of the route segment."),
    time: str = Query(..., description="The departure time in HH:MM format."),
    train_name: str = Query(..., description="The name of the train to match."),
    date: Optional[str] = Query(None, description="The departure date in YYYY-MM-DD format."),
    service: TimetableService = Depends(get_timetable_service)
):
    try:
        platform = await service.get_segment_platform(route_id, segment_index, time, train_name, date)
        return {"platform": platform}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

