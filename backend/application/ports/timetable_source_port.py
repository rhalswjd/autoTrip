from typing import Protocol, List, Optional, Dict
from datetime import date
from domain.route import Route
from domain.planner import ScheduleCandidate, PlannerMode

class TimetableSourcePort(Protocol):
    """
    PlannerQueryService가 시간표 후보를 가져올 때 의존하는 유일한 인터페이스(Port).
    구현체가 Yahoo인지 JR인지 등 외부 인프라스트럭처에 대해 전혀 알지 못하게 합니다.
    """
    async def fetch_schedule_candidates(
        self, 
        route: Route, 
        planner_mode: PlannerMode, 
        target_date: Optional[date] = None
    ) -> Dict[int, List[ScheduleCandidate]]:
        ...
