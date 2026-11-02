from fastapi import APIRouter, Depends, Query
from typing import List
from api.schemas import StationSearchResponseSchema, ERROR_RESPONSES
from application.services.station_service import StationService
from api.dependencies import get_station_service
from domain.station_identity import prefecture_label

router = APIRouter(prefix="/stations", tags=["Stations"])

@router.get(
    "/search", 
    response_model=List[StationSearchResponseSchema],
    summary="Auto-complete Station Search",
    description="Queries the local SQLite database to provide station auto-complete suggestions based on a partial English or Japanese name.",
    responses=ERROR_RESPONSES
)
async def search_stations(
    q: str = Query(..., description="Prefix or substring to search for", json_schema_extra={"examples": ["Osa"]}),
    service: StationService = Depends(get_station_service)
):
    stations = await service.search(query=q)
    return [
        StationSearchResponseSchema(
            id=station.id,
            english_name=station.name,
            display_name_en=station.display_name_en or station.name,
            japanese_name=station.name_jp,
            prefecture=station.prefecture,
            region=prefecture_label(station.prefecture),
            railway_company=station.railway_company,
            display_label=f'{station.display_name_en or station.name} · {prefecture_label(station.prefecture)}' if station.prefecture else station.display_name_en or station.name,
            provider_ids=station.provider_ids,
            provider_aliases=station.provider_aliases,
            has_midori_office=station.has_midori_office
        )
        for station in stations
    ]
