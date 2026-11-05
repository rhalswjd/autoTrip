"""Promote proven full-destination trains, never splice them into transfer legs."""
import hashlib
import uuid

from application.ports.cache_port import CachePort
from application.ports.scraper_port import ScraperPort
from core.logger import logger
from domain.journey import corridor_identity, elapsed_minutes, station_names_match
from domain.route import Route
from domain.search import SearchRequest
from domain.timetable import Timetable, calendar_type_for_date


class DirectAlternativeDiscovery:
    def __init__(self, provider: ScraperPort, cache: CachePort, max_probes: int = 1):
        self.provider, self.cache, self.max_probes = provider, cache, max_probes

    async def discover(self, routes: list[Route], request: SearchRequest) -> list[Route]:
        direct_corridors = {
            corridor_identity(r.segments[0].railway_name_jp or r.segments[0].railway_name)
            for r in routes if r.transfer_count == 0 and r.segments
        }
        probes = 0
        for route in routes:
            if probes >= self.max_probes:
                break
            if (route.transfer_count == 0 or not route.segments
                    or any(s.segment_type != 'train' for s in route.segments)
                    or any(marker in s.railway_name_jp for s in route.segments for marker in ('新幹線', '特急', '急行'))):
                continue
            first = route.segments[0]
            railway = first.railway_name_jp or first.railway_name
            corridor = corridor_identity(railway)
            if corridor in direct_corridors:
                continue
            probes += 1
            origin, target = route.stations[0], route.stations[-1]
            dep, arr = origin.name_jp or origin.name, target.name_jp or target.name
            service_date = route.search_date or request.departure_date
            key = 'direct-evidence-v1:' + hashlib.sha256(repr((dep, arr, railway, service_date)).encode()).hexdigest()
            try:
                timetable = await self.cache.get(key)
                if not isinstance(timetable, Timetable):
                    timetable = await self.provider.get_timetable(route.id, dep, arr,
                        railway_name_jp=railway, search_date=service_date)
                    if not isinstance(timetable, Timetable):
                        continue
                    if timetable.status == 'available':
                        await self.cache.set(key, timetable, ttl_seconds=3600)
                candidates = []
                for exact in getattr(timetable, calendar_type_for_date(service_date).value):
                    stops = exact.metadata.get('stop_sequence', [])
                    start = next((i for i, stop in enumerate(stops) if station_names_match(dep, str(stop))), None)
                    if (exact.operating_date != service_date or start is None
                            or not any(station_names_match(arr, str(stop)) for stop in stops[start + 1:])
                            or elapsed_minutes(exact.time, exact.arrival_time) is None):
                        continue
                    candidates.append(exact)
                if not candidates:
                    continue
                # A full-day service family is explicitly separate from strict timed results.
                exact = min(candidates, key=lambda x: x.time)
                duration = f'{elapsed_minutes(exact.time, exact.arrival_time)}m'
                direct = route.model_copy(update={
                    'id': str(uuid.uuid4()), 'stations': [origin, target],
                    'segments': [first.model_copy(update={'is_through': False, 'base_fare': None,
                        'express_fare': None, 'departure_time': exact.time, 'arrival_time': exact.arrival_time,
                        'departure_platform': exact.platform or None, 'duration': duration})],
                    'transfer_count': 0, 'departure_time': exact.time, 'arrival_time': exact.arrival_time,
                    'departure_datetime': exact.departure_datetime, 'arrival_datetime': exact.arrival_datetime,
                    'total_duration': duration, 'onboard_duration': duration, 'non_riding_duration': '0m',
                    'total_fare': 0, 'fare_status': 'unknown', 'fare_breakdown': None, 'railway_name': first.railway_name,
                    'family_key': '', 'categories': [], 'search_source': 'timetable_evidence', 'source_rank': None,
                    'result_kind': 'daily_alternative', 'evidence_url': exact.source_url,
                    'alternative_reason': 'Verified direct service on this date; departure may be outside your requested time.',
                })
                return [direct]
            except Exception as exc:
                logger.warning('Direct-alternative evidence unavailable: %s', type(exc).__name__)
                if '429' in str(exc):
                    raise
        return []
