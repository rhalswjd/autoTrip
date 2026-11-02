"""Manual-QA failures reproduced with deterministic provider structures."""
from unittest.mock import AsyncMock

import pytest

from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
from application.services.timetable_service import TimetableService
from application.ports.scraper_port import ScraperException
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from domain.timetable import Timetable, DepartureInfo
from tests.factories import journey
from application.services.search_service import SearchService
from domain.search import SearchRequest
from domain.movement import Movement
from domain.search import SearchContext
from api.schemas import LegSelection
from infrastructure.notion.notion_adapter import RealNotionAdapter
from infrastructure.notion.constants import NotionColumns
from infrastructure.notion.notion_mapper import NotionMapper
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository
import sqlite3
import httpx
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper


@pytest.mark.asyncio
async def test_provider_metrics_separate_yahoo_train_detail_from_station_table():
    scraper = YahooTimetableScraper()
    try:
        for path in ('/station/time/search', '/timetable/1/2', '/timetable/1/2/3'):
            await scraper._record_response(httpx.Response(200, request=httpx.Request('GET', 'https://example.com' + path)))
        assert scraper.statistics()['station'] == 1
        assert scraper.statistics()['timetable'] == 1
        assert scraper.statistics()['detail'] == 1
        assert scraper.statistics()['total'] == 3
    finally:
        await scraper.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('query', ['Bingo-Ochiai', 'Bingo Ochiai', 'bingo', '備後落合', 'bigo'])
async def test_station_romanization_boundaries_and_minor_typo(tmp_path, query):
    path = str(tmp_path / 'stations.db')
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE stations (id TEXT,name_en TEXT,name_jp TEXT,prefecture TEXT,railway_company TEXT,lat REAL,lng REAL,has_midori_office INTEGER)')
        conn.executemany('INSERT INTO stations VALUES (?,?,?,"","",0,0,0)',
            [('1', 'Bingochiai', '備後落合'), ('2', 'Unebigoryomae', '畝傍御陵前'), ('3', 'Bigo', 'Exact')])
    matches = await SqliteStationRepository(path).search_stations(query)
    assert any(s.name_jp == '備後落合' for s in matches)
    if query == 'bigo':
        assert matches[0].name == 'Bigo'


def test_fare_breakdown_uses_only_source_proven_components():
    fare = YahooTransitAdapter._fare_breakdown({
        'totalPrice': '4,700', 'totalPriceDetail': '（乗車券2,310円　特別料金2,390円）'},
        [{'priceInfo': {'expType': '指定席', 'expPrice': '2,390'}}, {'priceInfo': {'expType': '特急料金', 'expPrice': '0'}}])
    assert fare.base == 2310 and fare.surcharge == 2390 and fare.total == 4700
    assert fare.seat_basis == '指定席'
    assert fare.seat_supplement is None
    assert YahooTransitAdapter._fare_breakdown({}, []).total is None


@pytest.mark.parametrize(('provider_name', 'railway', 'expected'), [
    ('はるか1号', 'JR Limited Express Haruka', 'JR Limited Express Haruka 1'),
    ('かがやき502号', 'JR Shinkansen', 'JR Shinkansen Kagayaki 502'),
    ('新快速', 'JR Kyoto Line', 'Special Rapid'),
    ('普通', 'JR Kyoto Line', 'Local'),
    ('快速', 'JR Kyoto Line', 'Rapid'),
    ('普通', 'OsakaMetro Midosuji Line', 'OsakaMetro Midosuji Line'),
])
def test_notion_exact_transport_uses_english_without_losing_railway_identity(provider_name, railway, expected):
    leg = LegSelection(segment_index=0, departure_station='A', arrival_station='B', departure_time='08:00',
                       transport_name=provider_name, railway_name=railway)
    assert NotionMapper._resolve_leg_transport_type(leg) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('through', [False, True])
async def test_single_actual_ride_saves_exact_english_parent_without_child(through):
    route = journey(['A', 'B', 'C'] if through else ['A', 'C'],
                    ['JR Limited Express Thunderbird'] * (2 if through else 1),
                    through=[False, True] if through else [False]).model_copy(update={'fare_status': 'unknown'})
    movement = Movement(route=route, selected_departure_time='06:34', selected_arrival_time='07:54',
        search_context=SearchContext(departure_station='A', arrival_station='C', departure_time='06:00', departure_date='2026-10-31', search_mode='ROUTE_ONLY'))
    leg = LegSelection(segment_index=0, departure_station='A', arrival_station='C',
        departure_time='06:34', arrival_time='07:54', platform=4,
        transport_name='サンダーバード1号', railway_name='JR Limited Express Thunderbird')
    adapter = RealNotionAdapter()
    adapter.client = AsyncMock()
    adapter.client.post_page.return_value = {'id': 'parent', 'url': 'https://example.com/parent'}
    result = await adapter.save_movement(movement, target_page_id='test-page', legs=[leg])
    assert result['child_page_ids'] == []
    assert adapter.client.post_page.await_count == 1
    properties = adapter.client.post_page.await_args.kwargs['properties']
    assert properties[NotionColumns.TRANSPORT_TYPE]['select']['name'] == 'JR Limited Express Thunderbird 1'
    assert properties[NotionColumns.PLATFORM]['number'] == 4
    assert NotionColumns.FARE not in properties
    assert leg.transport_name == 'サンダーバード1号'


@pytest.mark.asyncio
async def test_transfer_children_do_not_depend_on_explicit_target_page():
    route = journey(['A', 'B', 'C'], ['Rail 1', 'Rail 2'])
    movement = Movement(route=route, selected_departure_time='08:00', selected_arrival_time='10:00',
        search_context=SearchContext(departure_station='A', arrival_station='C', departure_time='06:00', departure_date='2026-10-31', search_mode='ROUTE_ONLY'))
    legs = [LegSelection(segment_index=i, departure_station=a, arrival_station=b, departure_time='08:00')
            for i, (a, b) in enumerate([('A', 'B'), ('B', 'C')])]
    adapter = RealNotionAdapter()
    adapter.client = AsyncMock()
    adapter.client.get_parent_item_property.return_value = 'Parent item'
    adapter.client.post_page.return_value = {'id': 'page', 'url': 'https://example.com/page'}
    result = await adapter.save_movement(movement, legs=legs)
    assert adapter.client.post_page.await_count == 3
    assert len(result['child_page_ids']) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(('origin', 'reading'), [('敦賀', 'つるが'), ('京都', 'きょうと'), ('新大阪', 'しんおおさか')])
async def test_official_station_results_match_name_not_furigana(origin, reading):
    downloader = AsyncMock()
    downloader.fetch_html.side_effect = [
        f'<a href="/top?id=wrong">西{origin}（にし{reading}）</a>'
        f'<a href="/top?id=right">{origin}（{reading}）</a>',
        '<a href="https://timetable.jr-odekake.net/railway-index">時刻表</a>',
        '<table><tr><th>新幹線</th><td><a href="/station-timetable/corridor">方面</a></td></tr></table>',
    ]
    result = await JROdekakeTimetableScraper(downloader)._station_index(origin)
    assert 'station-timetable/corridor' in result
    assert downloader.fetch_html.await_args_list[1].args[0].endswith('/top?id=right')


@pytest.mark.asyncio
@pytest.mark.parametrize('failure_status', ['unsupported', 'provider_error'])
async def test_each_passenger_leg_has_independent_provider_availability(failure_status):
    route = journey(['A', 'B', 'C'], ['Bus', 'JR新幹線つるぎ'])
    route = route.model_copy(update={'segments': [route.segments[0].model_copy(update={'segment_type': 'bus'}), route.segments[1]]})
    cache, provider = FakeCacheAdapter(), AsyncMock()
    await cache.set(route.id, route)
    provider.get_timetable.side_effect = [
        ScraperException('provider offline') if failure_status == 'provider_error' else
        Timetable(route_id=route.id, status='unsupported'),
        Timetable(route_id=route.id, saturday=[DepartureInfo(id='jr-exact', time='08:00',
            arrival_time='09:00', train_name='つるぎ', metadata={'stop_sequence': ['B', 'C']})]),
    ]
    service = TimetableService(provider, cache)
    failed = await service.get_leg_timetable(route.id, 0)
    assert failed.availability == ('UNSUPPORTED' if failure_status == 'unsupported' else 'PROVIDER_ERROR')
    supported = await service.get_leg_timetable(route.id, 1)
    assert supported.availability == 'SUPPORTED'
    assert supported.saturday[0].id == 'jr-exact'


@pytest.mark.asyncio
async def test_jr_train_may_stop_at_bus_transfer_even_when_it_continues_to_final_city():
    route = journey(['敦賀', '福井', '金沢'], ['JR新幹線つるぎ', 'Bus'])
    route = route.model_copy(update={'segments': [route.segments[0], route.segments[1].model_copy(update={'segment_type': 'bus'})]})
    cache, provider = FakeCacheAdapter(), AsyncMock()
    await cache.set(route.id, route)
    provider.get_timetable.return_value = Timetable(route_id=route.id, saturday=[
        DepartureInfo(id='jr-calls-at-transfer', time='08:00', arrival_time='08:20', train_name='つるぎ',
            metadata={'stop_sequence': ['敦賀', '福井', '金沢']})])
    result = await TimetableService(provider, cache).get_leg_timetable(route.id, 0)
    assert result.saturday[0].id == 'jr-calls-at-transfer'


@pytest.mark.asyncio
@pytest.mark.parametrize(('names', 'railways'), [
    (['敦賀', '福井', '金沢'], ['ハピラインふくい', 'IRいしかわ鉄道']),
    (['餘部', '浜坂', '鳥取'], ['JR山陰本線', 'JR山陰本線']),
])
async def test_missing_direct_family_requires_exact_full_destination_evidence(names, railways):
    transfer = journey(names, railways)
    provider, cache, stations = AsyncMock(), FakeCacheAdapter(), AsyncMock()
    stations.search_stations.return_value = []
    provider.search_routes.return_value = [transfer]
    provider.get_timetable.return_value = Timetable(route_id=transfer.id, saturday=[
        DepartureInfo(id='verified-direct', time='06:05', arrival_time='08:30', train_name='Local',
                      operating_date='2026-10-31', source_url='https://example.com/public-train',
                      metadata={'stop_sequence': names})])
    routes = await SearchService(provider, cache, stations).search(SearchRequest(
        departure_station=names[0], arrival_station=names[-1], departure_date='2026-10-31', departure_time='13:00'))
    assert any(r.transfer_count == 1 for r in routes)
    direct = next(r for r in routes if r.transfer_count == 0)
    assert len(direct.passenger_legs) == 1
    assert direct.result_kind == 'daily_alternative'
    assert direct.fare_status == 'unknown'
    assert direct.search_date == '2026-10-31'
    assert provider.get_timetable.await_count == 1
    assert provider.get_timetable.await_args.args[1:3] == (names[0], names[-1])


@pytest.mark.asyncio
async def test_short_terminating_train_cannot_be_promoted_to_direct_family():
    transfer = journey(['A', 'B', 'C'], ['Rail', 'Rail'])
    provider, stations = AsyncMock(), AsyncMock()
    provider.search_routes.return_value = [transfer]
    stations.search_stations.return_value = []
    provider.get_timetable.return_value = Timetable(route_id=transfer.id, saturday=[
        DepartureInfo(id='short', time='06:05', arrival_time='07:00', train_name='Local',
                      operating_date='2026-10-31', metadata={'stop_sequence': ['A', 'B']})])
    routes = await SearchService(provider, FakeCacheAdapter(), stations).search(SearchRequest(
        departure_station='A', arrival_station='C', departure_date='2026-10-31', departure_time='13:00'))
    assert len(routes) == 1 and routes[0].transfer_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('bad_wait', [True, False])
async def test_practical_alternative_keeps_strict_results_and_avoids_unnecessary_next_day(bad_wait):
    strict = journey(['A', 'B', 'C'], ['JR特急One', 'JR特急Two']).model_copy(update={
        'total_duration': '6h' if bad_wait else '1h', 'onboard_duration': '1h',
        'non_riding_duration': '5h' if bad_wait else '0m', 'departure_time': '23:15', 'arrival_time': '05:15'})
    direct = journey(['A', 'C'], ['JR特急One']).model_copy(update={
        'total_duration': '1h', 'onboard_duration': '1h', 'non_riding_duration': '0m',
        'departure_time': '06:00', 'arrival_time': '07:00'})
    provider, stations = AsyncMock(), AsyncMock()
    provider.search_routes.side_effect = [[strict], [direct]]
    stations.search_stations.return_value = []
    service = SearchService(provider, FakeCacheAdapter(), stations)
    request = SearchRequest(departure_station='A', arrival_station='C', departure_date='2026-11-02', departure_time='23:00')
    results = await service.search(request)
    assert any(r.id == strict.id and r.result_kind == 'requested' for r in results)
    later = [r for r in results if r.result_kind == 'later_practical']
    assert bool(later) == bad_wait
    assert provider.search_routes.await_count == (2 if bad_wait else 1)
    if bad_wait:
        assert later[0].search_date == '2026-11-03'
        assert later[0].search_time == '04:00'
        assert '300m shorter' in later[0].alternative_reason
    await service.search(request)
    assert provider.search_routes.await_count == (2 if bad_wait else 1)


@pytest.mark.asyncio
@pytest.mark.parametrize('onboard_night', [False, True])
async def test_valid_late_direct_or_genuine_overnight_does_not_trigger_later_probe(onboard_night):
    route = journey(['A', 'C'], ['JR特急Night']).model_copy(update={
        'total_duration': '6h' if onboard_night else '1h',
        'onboard_duration': '6h' if onboard_night else '1h', 'non_riding_duration': '0m',
        'departure_time': '23:00', 'arrival_time': '05:00' if onboard_night else '00:00'})
    provider, stations = AsyncMock(), AsyncMock()
    provider.search_routes.return_value = [route]
    stations.search_stations.return_value = []
    result = await SearchService(provider, FakeCacheAdapter(), stations).search(SearchRequest(
        departure_station='A', arrival_station='C', departure_date='2026-11-02', departure_time='23:00'))
    assert len(result) == 1 and result[0].result_kind == 'requested'
    assert result[0].departure_time == '23:00'
    assert provider.search_routes.await_count == 1
