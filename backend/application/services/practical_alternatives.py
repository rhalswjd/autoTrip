"""One bounded later-window probe, triggered by measured excessive non-riding time."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from application.ports.scraper_port import ScraperPort
from application.services.route_families import duration_minutes, group_route_families, categorize_routes
from core.logger import logger
from domain.route import Route
from domain.search import SearchRequest


@dataclass(frozen=True)
class PracticalServicePolicy:
    minimum_elapsed: int = 180
    minimum_non_riding: int = 90
    minimum_saving: int = 60
    service_window_hour: int = 4


class PracticalAlternativeDiscovery:
    def __init__(self, provider: ScraperPort, policy: PracticalServicePolicy | None = None):
        self.provider, self.policy = provider, policy or PracticalServicePolicy()

    async def discover(self, routes: list[Route], request: SearchRequest, origin: str, target: str) -> list[Route]:
        known = [r for r in routes if duration_minutes(r.total_duration) is not None]
        if not known:
            return []
        best = min(known, key=lambda r: duration_minutes(r.total_duration))
        elapsed = duration_minutes(best.total_duration)
        non_riding = duration_minutes(best.non_riding_duration)
        if (elapsed < self.policy.minimum_elapsed or non_riding is None
                or non_riding < self.policy.minimum_non_riding or non_riding < elapsed / 2):
            return []
        requested = datetime.fromisoformat(f'{request.departure_date}T{request.departure_time}')
        departure = datetime.combine(requested.date(), time.fromisoformat(best.departure_time or request.departure_time))
        if departure < requested:
            departure += timedelta(days=1)
        # Derive the date from the actual slow journey, not a "night == 23" rule.
        arrival = departure + timedelta(minutes=elapsed)
        window = max(requested + timedelta(minutes=90), datetime.combine(arrival.date(), time(self.policy.service_window_hour)))
        day, clock = window.date().isoformat(), window.strftime('%H:%M')
        try:
            candidates = await self.provider.search_routes(departure=origin, arrival=target, time=clock, date=day)
        except Exception as exc:
            logger.warning('Later-service probe failed: %s', type(exc).__name__)
            if '429' in str(exc):
                raise
            return []
        alternatives = []
        for route in categorize_routes(group_route_families(candidates)):
            duration = duration_minutes(route.total_duration)
            if duration is None or elapsed - duration < self.policy.minimum_saving or route.transfer_count > best.transfer_count:
                continue
            reason = f'{elapsed - duration}m shorter journey · {best.transfer_count - route.transfer_count} fewer transfers · searched {day} {clock}'
            alternatives.append(route.model_copy(update={'result_kind': 'later_practical', 'search_date': day,
                'search_time': clock, 'alternative_reason': reason}))
        return alternatives
