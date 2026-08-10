from typing import List, Optional
from datetime import date
from domain.route import Route
from domain.planner import ScheduleCandidate, PlannerMode
from infrastructure.scrapers.timetable.scraper import TimetableScraper

class JROdekakeTimetableSource:
    """
    JR Odekake를 Source로 사용하는 Adapter 구현체.
    TimetableSourcePort 프로토콜을 준수합니다.
    """
    def __init__(self, scraper: TimetableScraper):
        self.scraper = scraper

    async def fetch_schedule_candidates(
        self, 
        route: Route, 
        planner_mode: PlannerMode, 
        target_date: Optional[date] = None
    ) -> List[ScheduleCandidate]:
        # TODO: JR Odekake 구현
        # TODO: JR Odekake 검색 로직 및 URL 구성
        
        # 임시로 빈 리스트 반환 (설계 목적)
        return []
