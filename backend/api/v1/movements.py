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
    from utils.notion_parser import extract_notion_page_id
    from fastapi import HTTPException
    
    final_target_page_id = req.target_page_id
    
    if req.notion_page_url:
        try:
            final_target_page_id = extract_notion_page_id(req.notion_page_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif req.target_page_id:
        try:
            final_target_page_id = extract_notion_page_id(req.target_page_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    movement, notion_result = await service.create_movement(
        route_id=req.route_id,
        departure_station=req.departure_station,
        arrival_station=req.arrival_station,
        search_time=req.search_time,
        search_date=req.search_date,
        selected_departure_time=req.selected_departure_time,
        selected_arrival_time=req.selected_arrival_time,
        target_page_id=final_target_page_id,
        legs=req.legs
    )
    return MovementResponseSchema(
        route_id=movement.route.id,
        departure_station=movement.route.departure_station,
        arrival_station=movement.route.arrival_station,
        selected_departure_time=movement.selected_departure_time,
        selected_arrival_time=movement.selected_arrival_time,
        search_mode=movement.search_context.search_mode.value,
        status="saved_to_notion",
        notion_url=notion_result.get("notion_url", ""),
        parent_page_id=notion_result.get("parent_page_id"),
        child_page_ids=notion_result.get("child_page_ids")
    )
