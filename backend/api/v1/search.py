from fastapi import APIRouter, Depends, Query
from typing import List
from api.schemas import RouteResponseSchema, ERROR_RESPONSES
from application.services.search_service import SearchService
from api.dependencies import get_search_service
from domain.search import SearchRequest

router = APIRouter(prefix="/search", tags=["Search"])

@router.get(
    "", 
    response_model=List[RouteResponseSchema],
    summary="Search for Railway Routes",
    description="Searches for train routes between two stations for an explicit departure date and time. Utilizes an internal cache to reduce external scraper load.",
    responses=ERROR_RESPONSES
)
async def search_routes(
    departure_station: str = Query(..., description="The departure station name.", json_schema_extra={"examples": ["Osaka"]}),
    arrival_station: str = Query(..., description="The arrival station name.", json_schema_extra={"examples": ["Kyoto"]}),
    departure_time: str = Query(..., pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$", description="Departure time in HH:MM format.", json_schema_extra={"examples": ["10:00"]}),
    departure_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Departure date in YYYY-MM-DD format.", json_schema_extra={"examples": ["2024-10-01"]}),
    departure_station_id: str | None = Query(None, description='Stable selected station ID; names are presentation only when supplied.'),
    arrival_station_id: str | None = Query(None, description='Stable selected destination station ID.'),
    service: SearchService = Depends(get_search_service)
):
    req = SearchRequest(
        departure_station=departure_station,
        arrival_station=arrival_station,
        departure_time=departure_time,
        departure_date=departure_date,
        departure_station_id=departure_station_id,
        arrival_station_id=arrival_station_id
    )
    routes = await service.search(req)
    return routes
