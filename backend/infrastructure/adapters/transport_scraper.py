"""Compose route discovery with explicit official/non-JR timetable providers."""
from urllib.parse import urlencode

from application.ports.scraper_port import ScraperException, UnsupportedTimetable
from domain.timetable import Timetable, calendar_type_for_date
from core.logger import logger
from infrastructure.services.timetable_capabilities import timetable_operator
from domain.service_identity import has_named_service


class TransportScraperAdapter:
    def __init__(self, discovery, official, other, official_metrics=None):
        self.discovery = discovery
        self.official = official
        self.other = other
        self.official_metrics = official_metrics

    async def search_routes(self, departure, arrival, time=None, date=None):
        return await self.discovery.search_routes(departure, arrival, time=time, date=date)

    async def get_timetable(self, route_id, departure="", arrival="", timetable_id=None,
                            railway_name_jp="", search_date=None, cursor=0, station_context=None, not_before=None):
        railway = railway_name_jp.replace("ＪＲ", "JR")
        if 'バス' in railway or 'bus' in railway.casefold():
            return Timetable(route_id=route_id, selected_calendar=calendar_type_for_date(search_date),
                             status='unsupported', message='이 버스 구간은 연결된 철도 시간표 공급자가 지원하지 않습니다.')
        operator = timetable_operator(railway_name_jp, station_context)
        # For an unregistered JR named service, discover actual published official
        # coverage; the JR label alone does not establish ownership or support.
        # Known other operators/sections and non-JR labels retain their routing.
        official_probe = operator == 'unknown' and railway.startswith('JR') and has_named_service(railway)
        if operator == 'jr_west' or official_probe:
            before = self.official_metrics() if self.official_metrics else {}
            try:
                result = await self.official.get_timetable(
                    route_id, departure, arrival, timetable_id=timetable_id,
                    railway_name_jp=railway_name_jp, search_date=search_date, cursor=cursor,
                    **({'not_before': not_before} if not_before else {}))
                if result.selected_departures() or not result.complete:
                    return result
                logger.info('Official timetable cannot prove this complete leg; checking Yahoo fallback')
            except UnsupportedTimetable as exc:
                logger.info('Official timetable unavailable for this leg: %s; checking Yahoo fallback', exc)
            finally:
                if self.official_metrics:
                    after = self.official_metrics()
                    logger.info('JR timetable requests: %s', {key: after[key] - before.get(key, 0) for key in after})
        metrics = getattr(type(self.other), 'statistics', None)
        before = metrics(self.other) if callable(metrics) else {}
        try:
            kwargs = {"timetable_id": timetable_id, "railway_name_jp": railway_name_jp, "search_date": search_date}
            if cursor:
                kwargs['cursor'] = cursor
            result = await self.other.get_timetable(route_id, departure, arrival, **kwargs)
        except ValueError as exc:
            return Timetable(route_id=route_id, source="yahoo", selected_calendar=calendar_type_for_date(search_date),
                             status="unsupported", message=str(exc))
        finally:
            if callable(metrics):
                after = metrics(self.other)
                logger.info('Yahoo timetable requests: %s', {key: after[key] - before.get(key, 0) for key in after})
        return result.model_copy(update={"source": "yahoo"})
