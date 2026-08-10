from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import date
from api.schemas import RouteResponseSchema
from application.services.planner_query_service import PlannerQueryService
from application.ports.cache_port import CachePort
from api.dependencies import get_planner_query_service, get_cache_port
from domain.planner import PlannerMode

router = APIRouter(prefix="/routes", tags=["Planner"])

@router.get(
    "/{route_id}/planner", 
    response_model=RouteResponseSchema,
    summary="Get Planner Details for a Route"
)
async def get_route_planner(
    route_id: str,
    planner_mode: PlannerMode = Query(PlannerMode.WEEKDAY, description="Planner Mode"),
    specific_date: Optional[date] = Query(None, description="Specific date if mode is SPECIFIC_DATE"),
    cache: CachePort = Depends(get_cache_port),
    service: PlannerQueryService = Depends(get_planner_query_service)
):
    # 1. Cache에서 Route 조회
    cached_data = await cache.get(route_id)
    if not cached_data:
        raise HTTPException(status_code=404, detail="Route not found")
        
    # 만약 cache가 여러 검색 결과를 담은 리스트라면 해당 id를 가진 Route를 찾음
    # (현재 Search API는 Query hash를 key로 하여 Route 리스트를 저장함. 
    # 따라서 route_id로 단건 캐싱이 되어있다고 가정하거나, 리스트를 순회하여 찾습니다.)
    route = None
    if isinstance(cached_data, list):
        for r in cached_data:
            if r.id == route_id:
                route = r
                break
    else:
        route = cached_data

    if not route:
        raise HTTPException(status_code=404, detail="Route not found in cache")

    # 2. PlannerQueryService 호출
    try:
        updated_route = await service.get_route_planner_details(
            route=route,
            planner_mode=planner_mode,
            target_date=specific_date
        )
    except Exception:
        # Graceful Degradation: Planner 실패 시 원본 Route 반환
        updated_route = route

    # TODO: Recommendation
    
    # 3. RouteResponseSchema 반환
    return updated_route
