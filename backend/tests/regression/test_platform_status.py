"""Platform absence provenance is independent of exact-train/save eligibility."""
import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from api.schemas import LegSelection
from application.services.movement_service import MovementService
from application.services.timetable_service import exact_option_key
from domain.timetable import DepartureInfo
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.notion.notion_mapper import NotionMapper
from infrastructure.notion.constants import NotionColumns as C
from infrastructure.scrapers.timetable.odekake_parser import JROdekakeParser
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
from tests.factories import journey
from tests.regression.test_odekake_integration import TRAIN_PAGE


@pytest.mark.parametrize(('departure', 'arrival', 'dep_status', 'arr_status'), [
    ('4', '31', 'KNOWN', 'KNOWN'), ('4', '', 'KNOWN', 'SOURCE_NOT_PROVIDED'),
    ('', '31', 'SOURCE_NOT_PROVIDED', 'KNOWN'), ('', '', 'SOURCE_NOT_PROVIDED', 'SOURCE_NOT_PROVIDED'),
])
def test_successful_official_exact_train_platform_sides_are_independent(departure, arrival, dep_status, arr_status):
    html = TRAIN_PAGE.replace('<td>4</td>', f'<td>{departure}</td>').replace('<td>31</td>', f'<td>{arrival}</td>')
    exact = JROdekakeParser().parse_train(html, '新大阪', '敦賀')
    assert exact['platform_status'] == dep_status and exact['arrival_platform_status'] == arr_status
    assert exact['platform'] == departure and exact['arrival_platform'] == arrival
    assert exact['arrival_time'] == '07:54'


def test_verified_train_with_malformed_platform_cell_is_lookup_failed():
    html = TRAIN_PAGE.replace('</td><td>31</td>', '</td>')
    exact = JROdekakeParser().parse_train(html, '新大阪', '敦賀')
    assert exact['arrival_platform_status'] == 'LOOKUP_FAILED'
    assert exact['platform_status'] == 'KNOWN'


@pytest.mark.asyncio
@pytest.mark.parametrize('failed', [False, True])
async def test_yahoo_successful_missing_and_failed_detail_remain_distinct(failed):
    scraper = YahooTimetableScraper(); await scraper.client.aclose(); scraper.client = AsyncMock()
    if failed:
        scraper.client.get.side_effect = RuntimeError('Detail retrieval failed')
    else:
        stops = [{'stationName': 'A', 'departureTime': '0800'}, {'stationName': 'B', 'arrivalTime': '0900'}]
        data = {'props': {'pageProps': {'timetableStationTrainResult': {'timetable': {'displayName': 'Train', 'stopStation': stops}}}}}
        scraper.client.get.return_value.text = '<script id="__NEXT_DATA__">' + json.dumps(data) + '</script>'
    exact = await scraper._fetch_train_details('/timetable/1/2/3', 'A', 'B', asyncio.Semaphore(1))
    assert exact['platform_status'] == ('LOOKUP_FAILED' if failed else 'SOURCE_NOT_PROVIDED')
    assert exact['arrival_platform_status'] == ('LOOKUP_FAILED' if failed else 'SOURCE_NOT_PROVIDED')


@pytest.mark.parametrize(('source', 'status', 'wording'), [
    ('jr_odekake', 'SOURCE_NOT_PROVIDED', '공식 정보 미제공'),
    ('yahoo', 'SOURCE_NOT_PROVIDED', '출처 정보 미제공'),
    ('jr_odekake', 'LOOKUP_FAILED', '조회 실패'), ('yahoo', 'LOOKUP_FAILED', '조회 실패'),
])
@pytest.mark.parametrize('as_parent', [False, True])
def test_notion_uses_truthful_missing_platform_wording(source, status, wording, as_parent):
    leg = LegSelection(segment_index=0, departure_station='A', arrival_station='B', departure_time='08:00',
        arrival_time='09:00', source=source, platform_status=status, arrival_platform_status=status)
    if as_parent:
        from domain.movement import Movement
        from domain.search import SearchContext
        from domain.enums import SearchMode
        movement = Movement(route=journey(['A', 'B'], ['Rail']), selected_departure_time='08:00', selected_arrival_time='09:00',
            search_context=SearchContext(departure_station='A', arrival_station='B', search_mode=SearchMode.ROUTE_ONLY,
                departure_time=None, departure_date=None))
        props = NotionMapper.map_parent_movement(movement, leg)
    else:
        props = NotionMapper.map_leg(leg, 'test-parent', 'Parent item')
    assert wording in props[C.DEPARTURE_TIME]['rich_text'][0]['text']['content']
    assert wording in props[C.ARRIVAL_TIME]['rich_text'][0]['text']['content']
    assert C.PLATFORM not in props


@pytest.mark.parametrize('value', [31, '4A', '①'])
def test_notion_keeps_known_numeric_or_text_platform(value):
    leg = LegSelection(segment_index=0, departure_station='A', arrival_station='B', departure_time='08:00',
        arrival_time='09:00', platform=value, platform_status='KNOWN', arrival_platform='12', arrival_platform_status='KNOWN')
    props = NotionMapper.map_leg(leg, 'test-parent', 'Parent item')
    if isinstance(value, int): assert props[C.PLATFORM]['number'] == value
    else: assert str(value) in props[C.DEPARTURE_TIME]['rich_text'][0]['text']['content']
    assert '12' in props[C.ARRIVAL_TIME]['rich_text'][0]['text']['content']


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['KNOWN', 'SOURCE_NOT_PROVIDED', 'LOOKUP_FAILED'])
async def test_server_uses_cached_platform_provenance_and_allows_valid_save(status):
    route = journey(['A', 'B'], ['Rail']).model_copy(update={'search_date': '2026-11-02'})
    cache, notion = FakeCacheAdapter(), AsyncMock(); await cache.set(route.id, route)
    exact = DepartureInfo(id='exact', time='08:00', arrival_time='09:00', train_name='Train', operating_date=route.search_date,
        platform='4A' if status == 'KNOWN' else '', platform_status=status,
        arrival_platform_status='SOURCE_NOT_PROVIDED', source='jr_odekake')
    await cache.set(exact_option_key(route.id, 0, exact.id, route.search_date), exact)
    forged = LegSelection(segment_index=0, departure_station='Injected', arrival_station='Injected', departure_time='00:00',
        exact_departure_id='exact', timetable_date=route.search_date, platform=999, platform_status='KNOWN',
        arrival_platform=999, arrival_platform_status='KNOWN', source='yahoo')
    await MovementService(cache, notion).create_movement(route.id, 'A', 'B', None, None, '00:00', '00:00', legs=[forged])
    validated = notion.save_movement.await_args.kwargs['legs'][0]
    assert validated.platform == ('4A' if status == 'KNOWN' else None)
    assert validated.platform_status == status and validated.arrival_platform_status == 'SOURCE_NOT_PROVIDED'
    assert validated.source == 'jr_odekake'
    assert validated.departure_station == 'A' and validated.departure_time == '08:00'
    assert validated.arrival_time == '09:00'
    notion.save_movement.assert_awaited_once()


@pytest.mark.asyncio
async def test_cold_sqlite_cache_does_not_reuse_legacy_missing_platform_results(tmp_path):
    import hashlib
    from application.services.timetable_service import TimetableService
    from domain.journey import service_family
    from domain.timetable import Timetable
    from infrastructure.cache.sqlite_cache import SqliteCacheAdapter
    route = journey(['A', 'B'], ['Rail']).model_copy(update={'search_date': '2026-11-02'})
    cache = SqliteCacheAdapter(str(tmp_path / 'cold.db')); await cache.set(route.id, route)
    leg = route.passenger_legs[0]
    old_key = 'leg-timetable-v9:' + hashlib.sha256(repr((leg.departure_station.identity_key(),
        leg.arrival_station.identity_key(), service_family(route.segments[0].railway_name_jp), route.search_date, 0, None)).encode()).hexdigest()
    await cache.set(old_key, Timetable(route_id=route.id, status='unsupported'))
    exact = DepartureInfo(id='fresh', time='08:00', arrival_time='09:00', train_name='Train',
        source='jr_odekake', platform_status='SOURCE_NOT_PROVIDED', arrival_platform_status='SOURCE_NOT_PROVIDED')
    provider = AsyncMock(); provider.get_timetable.return_value = Timetable(route_id=route.id, weekday=[exact])
    result = await TimetableService(provider, cache).get_leg_timetable(route.id, 0)
    assert result.availability == 'SUPPORTED' and result.selected_departures()[0].platform_status == 'SOURCE_NOT_PROVIDED'
    provider.get_timetable.assert_awaited_once()
    again = await TimetableService(provider, cache).get_leg_timetable(route.id, 0)
    assert again.selected_departures()[0].platform_status == 'SOURCE_NOT_PROVIDED'
    provider.get_timetable.assert_awaited_once()


@pytest.mark.asyncio
async def test_pre_provenance_exact_cache_cannot_authorize_a_new_save():
    import hashlib
    from domain.exceptions import DomainException
    route = journey(['A', 'B'], ['Rail']).model_copy(update={'search_date': '2026-11-02'})
    cache, notion = FakeCacheAdapter(), AsyncMock(); await cache.set(route.id, route)
    old_key = 'exact-option-v2:' + hashlib.sha256(repr((route.id, 0, 'old', route.search_date)).encode()).hexdigest()
    await cache.set(old_key, DepartureInfo(id='old', time='08:00', arrival_time='09:00', train_name='Train'))
    selection = LegSelection(segment_index=0, departure_station='A', arrival_station='B', departure_time='08:00',
        exact_departure_id='old', timetable_date=route.search_date)
    with pytest.raises(DomainException, match='expired'):
        await MovementService(cache, notion).create_movement(route.id, 'A', 'B', None, None, '08:00', '09:00', legs=[selection])
    notion.save_movement.assert_not_awaited()


def test_platform_status_serialization_and_frontend_enum_contract():
    from pathlib import Path
    from api.schemas import DepartureInfoSchema
    schema = DepartureInfoSchema.model_json_schema()
    expected = {'KNOWN', 'SOURCE_NOT_PROVIDED', 'LOOKUP_FAILED'}
    assert set(schema['$defs']['PlatformStatus']['enum']) == expected
    exact = DepartureInfo(id='new', time='08:00', train_name='Train', platform_status='LOOKUP_FAILED')
    assert exact.model_dump(mode='json')['platform_status'] == 'LOOKUP_FAILED'
    legacy = DepartureInfo.model_validate({'id': 'old', 'time': '08:00', 'train_name': 'Train', 'platform': '31'})
    assert legacy.platform_status == 'KNOWN' and legacy.arrival_platform_status == 'LOOKUP_FAILED'
    path = Path(__file__).resolve().parents[3] / 'frontend/src/api/types.ts'
    if path.exists():
        import re
        declaration = re.search(r'export type PlatformStatus = ([^;]+);', path.read_text()).group(1)
        assert set(re.findall(r"'([^']+)'", declaration)) == expected


@pytest.mark.asyncio
async def test_unstructured_legacy_route_cannot_bypass_cached_platform_verification():
    from domain.exceptions import DomainException
    route = journey(['A', 'B'], ['Rail']).model_copy(update={'stations': [], 'segments': []})
    cache, notion = FakeCacheAdapter(), AsyncMock(); await cache.set(route.id, route)
    forged = LegSelection(segment_index=0, departure_station='A', arrival_station='B', departure_time='08:00',
        platform=999, platform_status='KNOWN', source='jr_odekake')
    with pytest.raises(DomainException, match='verifiable passenger legs'):
        await MovementService(cache, notion).create_movement(route.id, 'A', 'B', None, None, '08:00', '09:00', legs=[forged])
    notion.save_movement.assert_not_awaited()
