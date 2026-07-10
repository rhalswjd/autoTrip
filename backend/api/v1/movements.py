from fastapi import APIRouter, Depends
from api.schemas import MovementRequestSchema, MovementResponseSchema, ERROR_RESPONSES
from application.services.movement_service import MovementService
from api.dependencies import get_movement_service

router = APIRouter(prefix="/movements", tags=["Movements"])

@router.post(
    "", 
    response_model=MovementResponseSchema,
    summary="Create and Save a Movement",
    description="Constructs a Movement entity based on a selected cached route and saves it directly to Notion via the NotionPort.",
    responses=ERROR_RESPONSES
)
async def create_movement(
    req: MovementRequestSchema,
    service: MovementService = Depends(get_movement_service)
):
    movement, notion_url = await service.create_movement(
        route_id=req.route_id,
        departure_station=req.departure_station,
        arrival_station=req.arrival_station,
        search_time=req.search_time,
        search_date=req.search_date,
        selected_departure_time=req.selected_departure_time,
        selected_arrival_time=req.selected_arrival_time
    )
    return MovementResponseSchema(
        route_id=movement.route.id,
        departure_station=movement.route.departure_station,
        arrival_station=movement.route.arrival_station,
        selected_departure_time=movement.selected_departure_time,
        selected_arrival_time=movement.selected_arrival_time,
        search_mode=movement.search_context.search_mode.value,
        status="saved_to_notion",
        notion_url=notion_url
    )
