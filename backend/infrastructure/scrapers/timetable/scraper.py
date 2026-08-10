from typing import List, Optional, Dict, Any
from datetime import date
from urllib.parse import urlencode
from domain.planner import ScheduleCandidate, PlannerMode
from infrastructure.scrapers.timetable.downloader import TimetableDownloader
from infrastructure.scrapers.timetable.parser import TimetableParser
from infrastructure.scrapers.timetable.mapper import TimetableMapper

class TimetableScraper:
    """
    TimetableDownloader -> TimetableParser -> TimetableMapper를 조립하는 Facade 클래스.
    이 클래스에서 Yahoo Transit에 맞는 최종 URL을 조합합니다.
    """
    def __init__(self, downloader: TimetableDownloader, parser: TimetableParser, mapper: TimetableMapper):
        self.downloader = downloader
        self.parser = parser
        self.mapper = mapper
        self.base_url = "https://transit.yahoo.co.jp/search/result"

    def _build_url(self, departure_station: str, arrival_station: str, target_date: Optional[date]) -> str:
        dt = target_date or date.today()
        
        params = {
            "from": departure_station,
            "to": arrival_station,
            "type": "1",
            "ticket": "ic",
            "expkind": "1",
            "ws": "3",
            "s": "0", # 0: 출발시간 기준
            "y": str(dt.year),
            "m": f"{dt.month:02d}",
            "d": f"{dt.day:02d}",
        }
        query_string = urlencode(params)
        return f"{self.base_url}?{query_string}"

    async def fetch_schedule_candidates(
        self, 
        departure_station: str, 
        arrival_station: str, 
        planner_mode: PlannerMode,
        target_date: Optional[date]
    ) -> Dict[int, List[ScheduleCandidate]]:
        """
        비즈니스 파라미터를 받아 최종 URL을 조립하고, HTML을 다운로드하여 도메인 딕셔너리를 반환합니다.
        """
        # 1. Build URL
        full_url = self._build_url(departure_station, arrival_station, target_date)
        
        # 2. Download
        html = await self.downloader.fetch_html(full_url)
        
        # 3. Parse (Dict 형태로 추출)
        raw_data = self.parser.parse(html)
        
        # 4. Map (도메인 엔티티 생성)
        candidates_by_segment = self.mapper.map_to_domain(raw_data, departure_station, arrival_station)
        
        return candidates_by_segment

    async def fetch_timetable(self, departure_station: str, arrival_station: str) -> List[Dict[str, Any]]:
        """
        역명으로 시간표 전용 페이지(timetable)의 정확한 노선 URL을 찾아 HTML을 받고,
        시간표 전용 파서로 파싱합니다.
        """
        import urllib.parse
        from core.logger import logger
        from bs4 import BeautifulSoup
        
        try:
            # 1. Resolve URL
            search_url = f"https://transit.yahoo.co.jp/timetable/search?q={urllib.parse.quote(departure_station)}"
            logger.info(f"1. search_url: {search_url}")
            
            station_html = await self.downloader.fetch_html(search_url)
            logger.info(f"2. search_html length: {len(station_html)}")
            logger.info(f"3. search_html prefix (1000 chars): {station_html[:1000]}")
            
            soup = BeautifulSoup(station_html, 'html.parser')
            full_url = None
            
            logger.info("4. All <a> tags text and href:")
            for a in soup.select("a"):
                text = a.text.strip()
                href = a.get("href", "")
                logger.info(f"  [text] {text} \n  [href] {href}")
                
                if "timetable" in href and arrival_station in text:
                    full_url = f"https://transit.yahoo.co.jp{href}"
                    logger.info(f"5. full_url determined as: {full_url}")
                    break
            
            logger.info(f"6. full_url is None?: {full_url is None}")
            
            if not full_url:
                raise Exception(f"Could not find timetable link for {departure_station} -> {arrival_station}")
                
            logger.info(f"7. Download Target full_url: {full_url}")
            
            # 2. Download true Timetable HTML
            html = await self.downloader.fetch_html(full_url)
            
            logger.info(f"8. After download html length: {len(html)}")
            logger.info(f"8. After download html prefix (3000 chars): {html[:3000]}")
            
            soup_tt = BeautifulSoup(html, 'html.parser')
            logger.info(f"HTML Title: {soup_tt.title.text if soup_tt.title else ''}")
            
            logger.info(f"9. Before parse_timetable html length: {len(html)}")
            
            # 3. Parse with new logic
            raw_data = self.parser.parse_timetable(html)
            
            logger.info(f"fetch_timetable END -> type(raw_data): {type(raw_data)}, len(raw_data): {len(raw_data)}")
            return raw_data
        except Exception as e:
            logger.exception(f"11. Exception caught in fetch_timetable: {e}")
            raise
