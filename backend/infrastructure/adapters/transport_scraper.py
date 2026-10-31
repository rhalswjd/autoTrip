"""Compose route discovery with explicit official/non-JR timetable providers."""
from urllib.parse import urlencode

from application.ports.scraper_port import ScraperException
from domain.timetable import Timetable, calendar_type_for_date
from core.logger import logger


class TransportScraperAdapter:
    def __init__(self, discovery, official, other, official_metrics=None):
        self.discovery = discovery
        self.official = official
        self.other = other
        self.official_metrics = official_metrics

    async def search_routes(self, departure, arrival, time=None, date=None):
        return await self.discovery.search_routes(departure, arrival, time=time, date=date)

    async def get_timetable(self, route_id, departure="", arrival="", timetable_id=None,
                            railway_name_jp="", search_date=None, cursor=0):
        railway = railway_name_jp.replace("ＪＲ", "JR")
        if 'バス' in railway or 'bus' in railway.casefold():
            return Timetable(route_id=route_id, selected_calendar=calendar_type_for_date(search_date),
                             status='unsupported', message='이 버스 구간은 연결된 철도 시간표 공급자가 지원하지 않습니다.')
        if "JR" in railway or "新幹線" in railway or timetable_id:
            before = self.official_metrics() if self.official_metrics else {}
            try:
                return await self.official.get_timetable(
                    route_id, departure, arrival, timetable_id=timetable_id,
                    railway_name_jp=railway_name_jp, search_date=search_date, cursor=cursor)
            finally:
                if self.official_metrics:
                    after = self.official_metrics()
                    logger.info('JR timetable requests: %s', {key: after[key] - before[key] for key in after})
        try:
            kwargs = {"timetable_id": timetable_id, "railway_name_jp": railway_name_jp, "search_date": search_date}
            if cursor:
                kwargs['cursor'] = cursor
            result = await self.other.get_timetable(route_id, departure, arrival, **kwargs)
        except ValueError as exc:
            return Timetable(route_id=route_id, source="yahoo", selected_calendar=calendar_type_for_date(search_date),
                             status="unsupported", message=str(exc))
        return result.model_copy(update={"source": "yahoo"})
