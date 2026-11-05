"""Bounded evidence for a useful family's next operating occurrence.

Requested-time candidates cannot describe a whole service day. Learn at most
two windows on that day, advancing from the provider's actual candidate tail.
Tomorrow is queried only for a known missing family after a day-boundary witness,
or when primary discovery is empty. This is bounded evidence, not an exhaustive
daily train catalogue or a proof of every service's final departure.
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from application.ports.cache_port import CachePort
from application.ports.scraper_port import ScraperPort
from core.logger import logger
from domain.chronology import JST, dated_clock
from domain.journey import canonical_station, family_identity
from domain.route import Route
from domain.search import SearchRequest
from domain.service_identity import service_identities
from application.services.route_families import duration_minutes


DISCOVERY_POLICY_VERSION = 'operating-family-v1'


@dataclass(frozen=True)
class _DayEvidence:
    routes: list[Route]
    failed: bool = False


@dataclass(frozen=True)
class NextDayDiscoveryPolicy:
    start: time = time(5)
    max_samples_per_day: int = 2
    sufficient_families: int = 2

    def supplemental_request(self, request: SearchRequest) -> SearchRequest:
        """Use the requested Japanese calendar, including future trips/holidays."""
        requested = dated_clock(request.departure_date, request.departure_time)
        return request.model_copy(update={
            'departure_date': (requested.date() + timedelta(days=1)).isoformat(),
            'departure_time': self.start.strftime('%H:%M'),
        })


def contextualize_routes(routes: list[Route], request: SearchRequest) -> list[Route]:
    """The query context and provider-proven actual departure day may differ.

    Keep search_date as the effective departure calendar used by the existing
    timetable/badge contract. Full provider datetimes take precedence; legacy
    adapters without calendar evidence retain their explicit query calendar.
    """
    result = []
    for route in routes:
        day = request.departure_date
        if route.departure_datetime:
            departure = datetime.fromisoformat(route.departure_datetime)
            if departure.tzinfo is None:
                raise ValueError('Provider route departure datetime must include a timezone')
            day = departure.astimezone(JST).date().isoformat()
        result.append(route.model_copy(update={'search_date': day, 'search_time': request.departure_time}))
    return result


class NextDayRouteDiscovery:
    def __init__(self, provider: ScraperPort, cache: CachePort, ttl: int = 3600,
                 policy: NextDayDiscoveryPolicy | None = None):
        self.provider, self.cache, self.ttl = provider, cache, ttl
        self.policy = policy or NextDayDiscoveryPolicy()

    @staticmethod
    def _instant(route: Route) -> datetime | None:
        if not route.departure_datetime:
            return None
        value = datetime.fromisoformat(route.departure_datetime)
        return value.astimezone(JST) if value.tzinfo is not None else None

    def _families(self, routes: list[Route]) -> dict[tuple, Route]:
        """Earliest source-proven occurrence, not fastest clock or train number."""
        families = {}
        for route in routes:
            identity, instant = family_identity(route), self._instant(route)
            if not identity or instant is None or not any(l.segment_type != 'walk' for l in route.passenger_legs):
                continue
            if identity not in families or instant < self._instant(families[identity]):
                families[identity] = route
        return families

    def _on_day(self, routes: list[Route], day: str) -> list[Route]:
        return [r for r in routes if self._instant(r) is not None and self._instant(r).date().isoformat() == day]

    def _continuation(self, routes: list[Route], request: SearchRequest) -> SearchRequest | None:
        instants = [self._instant(r) for r in routes if self._instant(r) is not None]
        if not instants:
            return None
        frontier = max(instants) + timedelta(minutes=1)
        if (frontier.date().isoformat() != request.departure_date
                or frontier <= dated_clock(request.departure_date, request.departure_time)):
            return None
        return request.model_copy(update={'departure_time': frontier.strftime('%H:%M')})

    async def _sample(self, request: SearchRequest) -> list[Route] | None:
        """Cache success and failure separately; a failed window stops this pass."""
        origin = ('id', request.departure_station_id) if request.departure_station_id else (
            'name', canonical_station(request.departure_station))
        target = ('id', request.arrival_station_id) if request.arrival_station_id else (
            'name', canonical_station(request.arrival_station))
        context = (DISCOVERY_POLICY_VERSION, origin, target, request.departure_date,
                   request.departure_time, self.policy, 'departure')
        key = 'service-day-discovery:' + hashlib.sha256(repr(context).encode()).hexdigest()
        cached = await self.cache.get(key)
        if cached is not None:
            return None if cached == 'provider_error' else cached
        try:
            routes = await self.provider.search_routes(
                departure=request.departure_station, arrival=request.arrival_station,
                date=request.departure_date, time=request.departure_time)
            routes = contextualize_routes(routes, request)
        except Exception as exc:
            logger.warning('Optional operating-family discovery failed: date=%s time=%s error=%s',
                           request.departure_date, request.departure_time, type(exc).__name__)
            await self.cache.set(key, 'provider_error', ttl_seconds=min(self.ttl, 60))
            return None
        await self.cache.set(key, routes, ttl_seconds=self.ttl)
        logger.info('Service-day sample: date=%s time=%s candidates=%d',
                    request.departure_date, request.departure_time, len(routes))
        return routes

    async def _day_candidates(self, request: SearchRequest, *, wanted: set[tuple] | None = None,
                              boundary: datetime | None = None) -> _DayEvidence:
        sample = request.model_copy(update={'departure_time': self.policy.start.strftime('%H:%M')})
        candidates = []
        for _ in range(self.policy.max_samples_per_day):
            routes = await self._sample(sample)
            if routes is None:
                return _DayEvidence(candidates, failed=True)
            candidates.extend(self._on_day(routes, request.departure_date))
            families = self._families(candidates)
            if wanted is not None and wanted <= families.keys():
                break
            if wanted is None and len(families) >= self.policy.sufficient_families:
                # For a requested day, a missing family's later-today occurrence
                # may sit beyond its morning sample. Continue while past samples
                # are the only evidence, within the same fixed two-window bound.
                if boundary is None or all(self._instant(r) >= boundary for r in families.values()):
                    break
            continuation = self._continuation(routes, sample)
            if continuation is None:
                break
            sample = continuation
        return _DayEvidence(candidates)

    @staticmethod
    def _useful(candidate: Route, primary: list[Route]) -> bool:
        if not primary:
            return True
        # Preserve named premium service diversity, and simpler/faster topology,
        # without introducing another scoring or route-identity system.
        premium = any(identity.category in ('特急', '急行', '新幹線')
                      for leg in candidate.passenger_legs for name in leg.railway_names_jp
                      for identity in service_identities(name))
        durations = [duration_minutes(r.total_duration) for r in primary]
        known = [n for n in durations if n is not None]
        duration = duration_minutes(candidate.total_duration)
        transfers = min(r.transfer_count for r in primary)
        return (premium or candidate.transfer_count < transfers or
                (candidate.transfer_count <= transfers and duration is not None and bool(known)
                 and duration < min(known)))

    async def discover(self, request: SearchRequest, primary_routes: list[Route] | None = None) -> list[Route]:
        primary = primary_routes or []
        requested = dated_clock(request.departure_date, request.departure_time)
        next_request = self.policy.supplemental_request(request)
        if not primary:
            candidates = await self._day_candidates(next_request)
            return list(self._families(candidates.routes).values())
        # Legacy/undated adapters cannot establish end-of-service. Do not guess
        # tomorrow from HH:mm or from the current wall clock.
        dated_primary = [r for r in primary if self._instant(r) is not None and self._instant(r) >= requested]
        if not dated_primary:
            return []
        today = self._on_day(dated_primary, request.departure_date)
        if len(self._families(today)) >= self.policy.sufficient_families:
            logger.info('Operating-family recovery skipped: sufficient same-day families')
            return []
        evidence = await self._day_candidates(request, boundary=requested)
        if evidence.failed:
            return []
        known = self._families(evidence.routes)
        represented = self._families(dated_primary)
        future = self._families([r for r in evidence.routes if self._instant(r) >= requested])
        today_additions = {k: r for k, r in future.items()
                           if (k not in represented or self._instant(represented[k]).date() > requested.date())
                           and self._useful(r, today)}
        missing = {k for k, r in known.items() if k not in represented and k not in future
                   and self._instant(r) < requested and self._useful(r, today)}
        if not missing:
            return list(today_additions.values())
        # A past sample by itself cannot prove exhaustion. Require the provider's
        # forward results to reach tomorrow. One tail probe is allowed, never a
        # loop over the rest of the day. Inconclusive coverage fails closed.
        reaches_tomorrow = any(self._instant(r).date() > requested.date() for r in dated_primary)
        if not reaches_tomorrow:
            continuation = self._continuation(dated_primary, request)
            if continuation is None:
                return list(today_additions.values())
            remaining = await self._sample(continuation)
            if remaining is None:
                return list(today_additions.values())
            remaining_today = self._families([r for r in self._on_day(remaining, request.departure_date)
                                               if self._instant(r) >= requested])
            today_additions.update({k: r for k, r in remaining_today.items()
                                    if k not in represented and self._useful(r, today)})
            missing -= remaining_today.keys()
            reaches_tomorrow = any(self._instant(r) is not None and self._instant(r).date() > requested.date()
                                   for r in remaining)
        if not missing or not reaches_tomorrow:
            logger.info('Operating-family recovery: no exhausted family proven within the discovery bound')
            return list(today_additions.values())
        candidates = await self._day_candidates(next_request, wanted=missing)
        recovered = self._families(candidates.routes)
        result = list(today_additions.values()) + [r for k, r in recovered.items() if k in missing]
        logger.info('Operating-family recovery: known=%d missing=%d today=%d recovered=%d',
                    len(known), len(missing), len(today_additions), len(result) - len(today_additions))
        return result
