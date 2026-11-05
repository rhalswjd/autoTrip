"""End-of-service evidence, rather than a date change, triggers recovery."""
from unittest.mock import AsyncMock
import json
import hashlib
import httpx

import pytest

from application.ports.scraper_port import ScraperException
from application.services.next_day_discovery import NextDayRouteDiscovery
from application.services.search_service import SearchService
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from tests.fixtures.route_discovery import sample, request
from tests.fixtures.yahoo_routes import route_page, route_spec
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter


DAY, NEXT = '2026-11-06', '2026-11-07'


def local(day=DAY, clock='20:32'):
    return sample('ＪＲ山陰本線', day, clock, clock)


def express(day=DAY, clock='12:56', number=4):
    return sample(f'ＪＲ特急はまかぜ{number}号', day, clock, clock)


def provider_for(windows):
    provider = AsyncMock()
    async def search(**kwargs):
        key = (kwargs['date'], kwargs['time'])
        assert key in windows, f'Unexpected/unbounded discovery {key}'
        value = windows[key]
        if isinstance(value, Exception):
            raise value
        return value
    provider.search_routes.side_effect = search
    return provider


def coverage_windows():
    # The provider caps each time query at six candidates. Its second page ends
    # at 12:15, so the next sample must derive 12:16, not a fixed noon anchor.
    return {
        (DAY, '05:00'): [local(clock=t) for t in ('05:23','06:13','06:47','08:06','09:45','12:15')],
        (DAY, '12:16'): [express(), local(clock='13:33'), local(clock='15:21')],
        (DAY, '21:53'): [local(NEXT, '05:23')],
        (NEXT, '05:00'): [local(NEXT, t) for t in ('05:23','06:13','06:47','08:06','09:45','12:15')],
        (NEXT, '12:16'): [express(NEXT), local(NEXT, '13:33')],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize('global_ids', [False, True])
async def test_page_local_metadata_binds_to_local_or_global_dom_route_numbers(global_ids):
    specs = [route_spec('ＪＲ山陰本線', t, '13:00') for t in ('08:06','09:45','12:15')]
    html = route_page(specs, start=4, end=6, count=6)
    if global_ids:
        for i in (3,2,1):
            html = html.replace(f'id="route0{i}"', f'id="route0{i+3}"')
    prefix, script = html.split('<script id="__NEXT_DATA__" type="application/json">')
    payload = json.loads(script.removesuffix('</script>'))
    for feature, clock in zip(payload['props']['pageProps']['naviSearchParam']['featureInfoList'], ('080600','094500','121500')):
        feature['summaryInfo']['calendarData'] = {'startTime': '20261106T' + clock, 'endTime': '20261106T130000'}
    response = httpx.Response(200, text=prefix + '<script id="__NEXT_DATA__">' + json.dumps(payload) + '</script>',
        request=httpx.Request('GET','https://transit.yahoo.co.jp/search/result'))
    client = AsyncMock()
    client.get.return_value = response
    routes, next_page = await YahooTransitAdapter()._fetch_yahoo_page('https://transit.yahoo.co.jp/search/result',
        None, {'from':'新大阪','to':'敦賀'}, client, DAY, '05:00', 'earliest', 3)
    assert [r.departure_datetime for r in routes] == [f'{DAY}T{t}:00+09:00' for t in ('08:06','09:45','12:15')]
    assert [r.source_rank for r in routes] == [4,5,6]
    assert next_page is None


@pytest.mark.asyncio
@pytest.mark.parametrize('clock', ['10:00', '12:00', '17:00'])
async def test_good_same_day_family_coverage_never_queries_tomorrow(clock):
    provider = provider_for({})
    primary = [local(clock='18:00'), express(clock='18:10')]
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(request(DAY, clock), primary)
    assert result == []
    provider.search_routes.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_candidate_frontier_recovers_exhausted_family_without_losing_today_local():
    provider = provider_for(coverage_windows())
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY, '20:00'), [local(), local(clock='21:52')])
    assert len(result) == 1
    assert 'はまかぜ' in result[0].segments[0].railway_name_jp
    assert result[0].departure_datetime == f'{NEXT}T12:56:00+09:00'
    assert [(c.kwargs['date'], c.kwargs['time']) for c in provider.search_routes.await_args_list] == [
        (DAY,'05:00'), (DAY,'12:16'), (DAY,'21:53'), (NEXT,'05:00'), (NEXT,'12:16')]
    provider.get_timetable.assert_not_awaited()


@pytest.mark.asyncio
async def test_hidden_but_still_available_family_uses_today_not_tomorrow():
    windows = coverage_windows()
    windows[(DAY,'12:16')] = [express(clock='18:10'), express(clock='19:30', number=6)]
    provider = provider_for(windows)
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY, '17:00'), [local(clock='17:28')])
    assert len(result) == 1 and result[0].departure_datetime == f'{DAY}T18:10:00+09:00'
    assert all(c.kwargs['date'] == DAY for c in provider.search_routes.await_args_list)


@pytest.mark.asyncio
async def test_past_sample_alone_cannot_prove_service_exhaustion():
    windows = coverage_windows()
    windows[(DAY,'21:53')] = [local(clock='22:30')]  # bounded evidence never reaches the day boundary
    provider = provider_for(windows)
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY, '20:00'), [local(), local(clock='21:52')])
    assert result == []
    assert all(c.kwargs['date'] == DAY for c in provider.search_routes.await_args_list)


@pytest.mark.asyncio
async def test_primary_already_crosses_midnight_needs_no_extra_boundary_probe():
    windows = coverage_windows()
    del windows[(DAY,'21:53')]
    provider = provider_for(windows)
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY, '22:00'), [local(NEXT,'05:23')])
    assert len(result) == 1 and result[0].search_date == NEXT
    assert provider.search_routes.await_count == 4


@pytest.mark.asyncio
async def test_missing_target_not_replaced_by_unrelated_tomorrow_families():
    windows = coverage_windows()
    windows[(NEXT,'12:16')] = [sample('Unrelated', NEXT, '13:00', '15:00')]
    provider = provider_for(windows)
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY,'22:00'), [local(NEXT,'05:23')])
    assert result == []


@pytest.mark.asyncio
async def test_next_day_stops_when_known_missing_family_found_in_first_window():
    windows = coverage_windows()
    windows[(NEXT,'05:00')] = [express(NEXT,'07:00'), express(NEXT,'09:00',number=6)]
    del windows[(NEXT,'12:16')]
    provider = provider_for(windows)
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY,'22:00'), [local(NEXT,'05:23')])
    assert len(result) == 1 and result[0].departure_time == '07:00'
    assert provider.search_routes.await_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', [(DAY,'05:00'),(DAY,'12:16'),(DAY,'21:53'),(NEXT,'05:00'),(NEXT,'12:16')])
async def test_optional_failure_stops_exploration_and_cached_failure_prevents_retry_storm(stage):
    windows = coverage_windows()
    windows[stage] = ScraperException('HTTP 429')
    provider = provider_for(windows)
    discovery = NextDayRouteDiscovery(provider, FakeCacheAdapter())
    req, primary = request(DAY,'20:00'), [local(), local(clock='21:52')]
    assert await discovery.discover(req, primary) == []
    calls = provider.search_routes.await_count
    assert provider.search_routes.await_args.kwargs['date'] == stage[0]
    assert provider.search_routes.await_args.kwargs['time'] == stage[1]
    assert await discovery.discover(req, primary) == []
    assert provider.search_routes.await_count == calls <= 5


@pytest.mark.asyncio
async def test_service_day_samples_reused_across_requested_times_and_stop_at_d_plus_one():
    provider = provider_for(coverage_windows())
    discovery = NextDayRouteDiscovery(provider, FakeCacheAdapter())
    primary = [local(),local(clock='21:52')]
    await discovery.discover(request(DAY,'20:00'), primary)
    calls = provider.search_routes.await_count
    await discovery.discover(request(DAY,'21:00'), primary)
    assert provider.search_routes.await_count == calls == 5
    assert {c.kwargs['date'] for c in provider.search_routes.await_args_list} == {DAY,NEXT}


@pytest.mark.asyncio
async def test_forward_probe_finds_later_today_occurrence_instead_of_misclassifying_as_exhausted():
    windows = coverage_windows()
    windows[(DAY,'18:01')] = [express(clock='18:10'), local(NEXT,'05:23')]
    provider = provider_for(windows)
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY,'17:00'), [local(clock='18:00')])
    assert len(result) == 1 and result[0].search_date == DAY
    assert result[0].departure_time == '18:10'
    assert all(c.kwargs['date'] == DAY for c in provider.search_routes.await_args_list)


@pytest.mark.asyncio
async def test_known_today_occurrence_replaces_later_day_sample_of_same_family():
    windows = coverage_windows()
    windows[(DAY,'12:16')] = [express(clock='18:10')]
    provider = provider_for(windows)
    result = await NextDayRouteDiscovery(provider, FakeCacheAdapter()).discover(
        request(DAY,'17:00'), [local(clock='17:28'),express(NEXT)])
    assert len(result) == 1 and result[0].departure_datetime == f'{DAY}T18:10:00+09:00'


@pytest.mark.asyncio
async def test_successful_empty_primary_fallback_survives_a_later_optional_window_failure():
    provider = provider_for({(NEXT,'05:00'):[local(NEXT,'05:23')],
                             (NEXT,'05:24'):ScraperException('HTTP 429')})
    result = await NextDayRouteDiscovery(provider,FakeCacheAdapter()).discover(request(DAY,'22:00'),[])
    assert len(result) == 1 and result[0].departure_datetime == f'{NEXT}T05:23:00+09:00'
    assert provider.search_routes.await_count == 2


@pytest.mark.asyncio
async def test_search_service_normal_daytime_does_not_reuse_old_unconditional_tomorrow_results():
    primary = [local(clock='18:00'),express(clock='18:10')]
    provider, cache, stations = provider_for({(DAY,'17:00'):primary}),FakeCacheAdapter(),AsyncMock()
    stations.search_stations.return_value = []
    service = SearchService(provider,cache,stations)
    req = request(DAY,'17:00')
    old_key = hashlib.md5(repr(('families-v6',('legacy-name','鳥取'),('legacy-name','岩美'),
                              '17:00',DAY)).encode()).hexdigest()
    await cache.set(old_key,[local(clock='18:00'),express(NEXT)])
    routes = await service.search(req)
    assert len(routes) == 2 and all(r.search_date == DAY for r in routes)
    assert provider.search_routes.await_count == 1
    assert await service.search(req) == routes
    assert provider.search_routes.await_count == 1
    provider.get_timetable.assert_not_awaited()
