from typing import List
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from infrastructure.scrapers.dtos import ScrapedRouteDTO, ScrapedTimetableDTO, ScrapedStationDTO
from infrastructure.exceptions import HtmlParsingException
from infrastructure.scrapers.selectors import JROdekakeSelectors
from core.logger import logger

class HtmlParser(ABC):
    @abstractmethod
    def parse_routes(self, html: str) -> List[ScrapedRouteDTO]:
        pass
        
    @abstractmethod
    def parse_timetable(self, html: str, route_id: str) -> ScrapedTimetableDTO:
        pass

class RealHtmlParser(HtmlParser):
    def parse_routes(self, html: str) -> List[ScrapedRouteDTO]:
        logger.debug("Parser Started: parse_routes")
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            station_name_node = soup.select_one(JROdekakeSelectors.STATION_NAME)
            if not station_name_node:
                logger.debug("Parser Finished: Empty route nodes")
                return []
                
            station_name_jp = station_name_node.text.strip()
            
            midori_node = soup.select_one(JROdekakeSelectors.MIDORI_ICON)
            has_midori = midori_node is not None

            platform_node = soup.select_one(JROdekakeSelectors.PLATFORM_INFO)
            platform_info = platform_node.text.strip() if platform_node else None

            station_dto = ScrapedStationDTO(
                name_jp=station_name_jp,
                lat=0.0,
                lng=0.0,
                has_midori_madoguchi=has_midori
            )

            route_dto = ScrapedRouteDTO(
                id="parsed_route_1",
                departure=station_name_jp,
                arrival="Unknown",
                railway_name="JR West",
                total_time="30m",
                fare=0,
                transfers=0,
                polyline_str="",
                platform_info=platform_info,
                stations=[station_dto]
            )
            logger.debug("Parser Finished: parse_routes success")
            return [route_dto]
        except Exception as e:
            logger.error(f"Parser Error: {e}")
            raise HtmlParsingException(f"Failed to parse route HTML: {e}")

    def parse_timetable(self, html: str, route_id: str) -> ScrapedTimetableDTO:
        try:
            return ScrapedTimetableDTO(
                route_id=route_id,
                first_train="06:00",
                last_train="23:00",
                entries=[]
            )
        except Exception as e:
            raise HtmlParsingException(f"Failed to parse timetable HTML: {e}")
