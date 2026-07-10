from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from api.schemas import RouteResponseSchema, ERROR_RESPONSES
from application.services.search_service import SearchService
from api.dependencies import get_search_service
from domain.search import SearchRequest

router = APIRouter(prefix="/search", tags=["Search"])

@router.get(
    "", 
    response_model=List[RouteResponseSchema],
    summary="Search for Railway Routes",
    description="Searches for train routes between two stations based on optional time and date. Utilizes an internal cache to reduce external scraper load.",
    responses=ERROR_RESPONSES
)
async def search_routes(
    departure_station: str = Query(..., description="The departure station name.", json_schema_extra={"examples": ["Osaka"]}),
    arrival_station: str = Query(..., description="The arrival station name.", json_schema_extra={"examples": ["Kyoto"]}),
    departure_time: Optional[str] = Query(None, description="Departure time in HH:MM format.", json_schema_extra={"examples": ["10:00"]}),
    departure_date: Optional[str] = Query(None, description="Departure date in YYYY-MM-DD format.", json_schema_extra={"examples": ["2024-10-01"]}),
    service: SearchService = Depends(get_search_service)
):
    req = SearchRequest(
        departure_station=departure_station,
        arrival_station=arrival_station,
        departure_time=departure_time,
        departure_date=departure_date
    )
    routes = await service.search(req)
    return routes
