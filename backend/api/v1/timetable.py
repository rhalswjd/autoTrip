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
    timetable = await service.get_timetable(route_id)
    return timetable
