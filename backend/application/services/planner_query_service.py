from typing import Optional, Dict, List
from datetime import date
from domain.route import Route
from domain.planner import PlannerMetadata, PlannerMode, PlannerState
from application.ports.timetable_source_port import TimetableSourcePort

class PlannerQueryService:
    """
    Planner의 핵심 비즈니스 로직을 처리하는 Application Service.
    Route를 받아 TimetableSource에서 시간표 후보를 조회하고 불변 객체(Immutable)로 조립합니다.
    """
    def __init__(self, timetable_source: TimetableSourcePort):
        # 인프라스트럭처 구현체(Yahoo, JR 등)를 전혀 모른 채 Port(인터페이스)에만 의존합니다.
        self.timetable_source = timetable_source

    def _resolve_target_date(self, mode: PlannerMode, specific_date: Optional[date]) -> Optional[date]:
        """
        PlannerMode에 따른 실제 검색 대상 날짜를 계산합니다.
        
        # TODO
        # Move to PlannerDateResolver utility.
        # PlannerQueryService should orchestrate only.
        """
        if mode == PlannerMode.SPECIFIC_DATE:
            return specific_date
        elif mode == PlannerMode.WEEKDAY:
            # TODO: 가장 가까운 평일 날짜 반환 로직
            pass
        elif mode == PlannerMode.WEEKEND_HOLIDAY:
            # TODO: 가장 가까운 주말 날짜 반환 로직
            pass
        return date.today()

    async def get_route_planner_details(
        self, 
        route: Route, 
        planner_mode: PlannerMode, 
        target_date: Optional[date] = None
    ) -> Route:
        """
        기존 Route를 받아 시간표 후보(ScheduleCandidate)를 추가한 새 Route 객체를 반환합니다.
        기존 Route 검색 기능을 절대 깨지 않도록 안전하게 동작합니다.
        """
        actual_date = self._resolve_target_date(planner_mode, target_date)
        
        # Route 당 1회만 Source를 호출하여 모든 Segment의 Candidate를 한 번에 가져옵니다.
        try:
            candidates_by_segment = await self.timetable_source.fetch_schedule_candidates(
                route=route, 
                planner_mode=planner_mode, 
                target_date=actual_date
            )
        except Exception:
            # TODO:
            # Catch TimetableSourceError only.
            # Do not swallow unexpected exceptions.
            candidates_by_segment = {}
            
        new_segments = []
        for idx, segment in enumerate(route.segments):
            # train Segment에만 Candidate를 붙입니다. (walk, bus 등은 제외)
            if segment.segment_type.lower() == "train":
                # TODO
                # RouteSegment should own stable segment_id.
                # Current implementation uses index only.
                # Will migrate later.
                candidates = candidates_by_segment.get(idx, [])
                # 불변성 유지: 원본 segment를 수정하지 않고 복사본 생성
                updated_segment = segment.model_copy(update={"schedule_candidates": candidates})
                new_segments.append(updated_segment)
            else:
                new_segments.append(segment)

        # TODO
        # PlannerMetadataFactory (future)
        metadata = PlannerMetadata(
            planner_state=PlannerState.AUTO,
            planner_mode=planner_mode
        )
        
        # 불변성 유지: 원본 route를 수정하지 않고 복사본 생성
        return route.model_copy(update={
            "segments": new_segments,
            "planner_metadata": metadata
        })
