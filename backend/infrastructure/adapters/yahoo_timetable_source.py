from typing import List, Optional, Dict
from datetime import date
from domain.route import Route
from domain.planner import ScheduleCandidate, PlannerMode
from infrastructure.scrapers.timetable.scraper import TimetableScraper

class YahooTimetableSource:
    """
    Yahoo Transit timetable source.
    
    This source does NOT calculate routes.
    It only retrieves timetable candidates for an already selected Route.
    
    TimetableSourcePort 프로토콜을 준수합니다.
    """
    def __init__(self, scraper: TimetableScraper):
        self.scraper = scraper

    async def fetch_schedule_candidates(
        self, 
        route: Route, 
        planner_mode: PlannerMode, 
        target_date: Optional[date] = None
    ) -> Dict[int, List[ScheduleCandidate]]:
        dep = route.stations[0].name_jp if route.stations and route.stations[0].name_jp else route.departure_station
        arr = route.stations[-1].name_jp if route.stations and route.stations[-1].name_jp else route.arrival_station
        
        # Adapter는 Route 도메인만 까서 비즈니스 파라미터만 전달하며, URL 조립은 Scraper가 담당합니다.
        candidates_by_segment = await self.scraper.fetch_schedule_candidates(
            departure_station=dep,
            arrival_station=arr,
            planner_mode=planner_mode,
            target_date=target_date
        )
        return candidates_by_segment
