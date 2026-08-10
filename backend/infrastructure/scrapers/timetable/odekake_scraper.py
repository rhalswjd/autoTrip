import logging
from typing import List, Dict, Any, Optional

from infrastructure.scrapers.timetable.odekake_downloader import JROdekakeDownloader
from infrastructure.scrapers.timetable.odekake_parser import JROdekakeParser
from infrastructure.scrapers.timetable.odekake_mapper import JROdekakeMapper
from domain.timetable import Timetable, DepartureInfo

logger = logging.getLogger(__name__)

class JROdekakeTimetableScraper:
    def __init__(self):
        self.downloader = JROdekakeDownloader()
        self.parser = JROdekakeParser()
        self.mapper = JROdekakeMapper()
        
    def _get_next_dates(self) -> tuple[str, str, str]:
        import datetime
        today = datetime.date.today()
        
        # next Monday
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + datetime.timedelta(days_ahead)
        
        # next Saturday
        days_ahead = 5 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_saturday = today + datetime.timedelta(days_ahead)
        
        # next Sunday
        days_ahead = 6 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_sunday = today + datetime.timedelta(days_ahead)
        
        return next_monday.strftime("%Y%m%d"), next_saturday.strftime("%Y%m%d"), next_sunday.strftime("%Y%m%d")

    async def get_timetable(self, route_id: str, departure_station: str, arrival_station: str, timetable_id: Optional[str] = None, mode: str = "weekday") -> Timetable:
        """
        특정 방향의 평일, 토요일, 휴일 시간표를 모두 가져옵니다.
        """
        if not timetable_id:
            raise ValueError(f"동적 탐색 불가: 현재 역 이름({departure_station})으로 Odekake Timetable ID를 탐색할 수 없으므로 timetable_id가 필수입니다.")

        weekday_date, saturday_date, holiday_date = self._get_next_dates()
        
        base_url = f"https://timetable.jr-odekake.net/station-timetable/{timetable_id}"
        urls = {
            "weekday": f"{base_url}?date={weekday_date}",
            "saturday": f"{base_url}?date={saturday_date}",
            "holiday": f"{base_url}?date={holiday_date}"
        }
        
        logger.info(f"[{self.__class__.__name__}] Fetching multiple dates...")
        htmls = await self.downloader.fetch_htmls(urls)
        
        departures_map = {"weekday": [], "saturday": [], "holiday": []}
        
        for day_type, html in htmls.items():
            logger.info(f"[{self.__class__.__name__}] Parsing HTML for {day_type}...")
            raw_data = self.parser.parse(html)
            
            logger.info(f"[{self.__class__.__name__}] Mapping to Domain for {day_type}...")
            departures_map[day_type] = self.mapper.map(raw_data, timetable_id)
            
        return Timetable(
            route_id=route_id,
            weekday=departures_map["weekday"],
            saturday=departures_map["saturday"],
            holiday=departures_map["holiday"]
        )
