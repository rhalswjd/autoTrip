"""Reusable dated route/provider fixtures; never access external services."""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock

from application.services.search_service import SearchService
from domain.search import SearchRequest
from domain.timetable import Timetable
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from tests.factories import journey


def sample(service, day, departure, arrival, *, names=None, services=None, **updates):
    route = journey(names or ['鳥取', '岩美'], services or [service], id=f'{day}-{service}-{departure}')
    return route.model_copy(update={
        'search_date': day, 'departure_time': departure, 'arrival_time': arrival,
        'departure_datetime': f'{day}T{departure}:00+09:00',
        'total_duration': '16m' if 'はまかぜ' in service else '26m', **updates,
    })


def request(day='2026-11-04', clock='22:00'):
    return SearchRequest(departure_station='鳥取', arrival_station='岩美',
                         departure_date=day, departure_time=clock)


def setup_search(primary, supplemental, *, query=None):
    """Retain date/cache regressions with explicit end-of-service witnesses.

    The coverage-policy suite separately models the real six-candidate frontier.
    These fixtures expose a past-day family, a forward midnight boundary, and
    actual next-day occurrences; they no longer mean unconditional tomorrow.
    """
    provider, stations, cache = AsyncMock(), AsyncMock(), FakeCacheAdapter()
    query = query or request()
    day = query.departure_date
    next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    async def search(**kwargs):
        window_day, clock = kwargs['date'], kwargs['time']
        if (window_day, clock) == (day, query.departure_time):
            return primary
        if isinstance(supplemental, Exception):
            raise supplemental
        if window_day == day:
            if clock == '05:00':
                return [r.model_copy(update={'id': 'evidence-' + r.id, 'search_date': day,
                    'departure_datetime': day + r.departure_datetime[10:]}) for r in supplemental]
            if clock > query.departure_time and primary:
                return [primary[0].model_copy(update={'id':'boundary', 'search_date':next_day,
                    'departure_time':'05:00','departure_datetime':f'{next_day}T05:00:00+09:00'})]
            return []
        if window_day == next_day:
            return [r for r in supplemental if datetime.fromisoformat(r.departure_datetime) >=
                    datetime.fromisoformat(f'{next_day}T{clock}:00+09:00')]
        raise AssertionError('Discovery exceeded D+1')
    provider.search_routes.side_effect = search
    provider.get_timetable.return_value = Timetable(route_id='unused', status='unsupported')
    stations.search_stations.return_value = []
    return SearchService(provider, cache, stations), provider, cache
