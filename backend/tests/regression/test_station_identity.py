"""Selected station identity must never be replaced by an ambiguous name match."""
from unittest.mock import AsyncMock
import pytest
from api.dependencies import get_cache_port, get_scraper_port, get_station_repository_port
from domain.station import Station
from domain.search import SearchRequest
from domain.exceptions import DomainException
from domain.journey import canonical_station, station_names_match
from application.services.search_service import SearchService
from application.services.timetable_service import TimetableService
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
from domain.timetable import Timetable
from tests.factories import journey
import sqlite3
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository

STATIONS = [Station(id='1160712', name='Kashiwara', name_jp='柏原(大阪)', prefecture='27'),
            Station(id='1163005', name='Kaibara', name_jp='柏原(兵庫)', prefecture='28'),
            Station(id='1150309', name='Kashiwabara', name_jp='柏原(滋賀)', prefecture='25')]
TARGET = Station(id='nara', name='Nara', name_jp='奈良', prefecture='29')


@pytest.mark.parametrize(('selected', 'alias'), list(zip(STATIONS, ['柏原(大阪府)', '柏原(兵庫県)', '柏原(滋賀県)'])))
def test_geographic_variants_are_equivalent_but_other_regions_never_are(selected, alias):
    assert canonical_station(selected.name_jp) == canonical_station(alias)
    assert all(not station_names_match(selected.name_jp, s.name_jp) for s in STATIONS if s.id != selected.id)
    assert YahooTransitAdapter.station_alias(selected.name_jp) == alias


@pytest.mark.parametrize('selected', STATIONS)
def test_yahoo_timetable_lookup_uses_same_scoped_region_alias_as_route_search(selected):
    assert YahooTimetableScraper._canonical_station_name(selected.name_jp) == canonical_station(selected.name_jp)


def repository():
    repo = AsyncMock()
    repo.get_station_by_id.side_effect = lambda identity: next((s for s in STATIONS + [TARGET] if s.id == identity), None)
    repo.search_stations.return_value = []
    return repo


@pytest.mark.asyncio
@pytest.mark.parametrize('selected', STATIONS)
async def test_selected_id_not_display_text_drives_provider_and_cached_route(selected):
    repo, provider, cache = repository(), AsyncMock(), FakeCacheAdapter()
    raw = journey([canonical_station(selected.name_jp), '奈良'], ['JR線'])
    raw = raw.model_copy(update={'stations': [Station(id='provider-code', name_jp=canonical_station(selected.name_jp), provider_ids={'yahoo': 'provider-code'}), TARGET]})
    provider.search_routes.return_value = [raw]
    request = SearchRequest(departure_station='misleading display', arrival_station='Nara',
        departure_station_id=selected.id, arrival_station_id=TARGET.id, departure_date='2026-11-02', departure_time='09:00')
    result = await SearchService(provider, cache, repo).search(request)
    assert provider.search_routes.await_args.kwargs['departure'] == selected.name_jp
    repo.search_stations.assert_not_awaited()
    assert result[0].stations[0].id == selected.id
    assert result[0].stations[0].name_jp == selected.name_jp
    assert result[0].stations[0].provider_ids['yahoo'] == 'provider-code'
    assert result[0].passenger_legs[0].departure_station.id == selected.id
    assert (await cache.get(result[0].id)).stations[0].id == selected.id


@pytest.mark.asyncio
async def test_provider_wrong_region_is_rejected_not_relabelled_as_selected_station():
    provider = AsyncMock()
    provider.search_routes.return_value = [journey(['柏原(兵庫県)', '奈良'], ['JR特急こうのとり'])]
    req = SearchRequest(departure_station='Kashiwara', arrival_station='Nara', departure_station_id=STATIONS[0].id,
        arrival_station_id=TARGET.id, departure_date='2026-11-02', departure_time='09:00')
    with pytest.raises(DomainException, match='identity'):
        await SearchService(provider, FakeCacheAdapter(), repository()).search(req)


def test_search_cache_uses_ids_even_if_display_text_is_identical():
    service = SearchService(AsyncMock(), FakeCacheAdapter(), repository())
    requests = [SearchRequest(departure_station='柏原', arrival_station='Nara', departure_station_id=s.id,
        arrival_station_id=TARGET.id, departure_date='2026-11-02', departure_time='09:00') for s in STATIONS]
    assert len({service._generate_cache_key(r) for r in requests}) == 3
    assert service._generate_cache_key(requests[0]) == service._generate_cache_key(
        requests[0].model_copy(update={'departure_station': 'a different display label'}))


@pytest.mark.asyncio
async def test_repository_exact_identity_and_provider_aliases_survive_ambiguous_autocomplete(tmp_path):
    path = str(tmp_path / 'stations.db')
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE stations(id TEXT,name_en TEXT,name_jp TEXT,prefecture TEXT,railway_company TEXT,lat REAL,lng REAL,has_midori_office INTEGER)')
        conn.executemany('INSERT INTO stations VALUES(?,?,?,?,"",0,0,0)',
            [(s.id, s.name, s.name_jp, s.prefecture) for s in STATIONS])
    repo = SqliteStationRepository(path)
    found = await repo.search_stations('柏原')
    assert {s.id for s in found} == {s.id for s in STATIONS}
    for expected in STATIONS:
        station = await repo.get_station_by_id(expected.id)
        assert station.name_jp == expected.name_jp and station.prefecture == expected.prefecture
        assert station.provider_aliases['yahoo'] == canonical_station(expected.name_jp)
        assert station.provider_aliases['jr_odekake'] == '柏原'


@pytest.mark.asyncio
async def test_timetable_cache_uses_station_ids_not_only_same_display_text():
    cache, provider = FakeCacheAdapter(), AsyncMock()
    provider.get_timetable.side_effect = [Timetable(route_id=str(i)) for i in range(3)]
    service = TimetableService(provider, cache)
    for station in STATIONS:
        route = journey(['柏原', '奈良'], ['JR線'], id=station.id)
        route = route.model_copy(update={'stations': [station.model_copy(update={'name_jp': '柏原'}), TARGET]})
        await cache.set(route.id, route)
        await service.get_leg_timetable(route.id, 0)
    assert provider.get_timetable.await_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(('selected', 'expected'), [(STATIONS[0], 'osaka'), (STATIONS[1], 'hyogo')])
async def test_jr_result_preserves_region_and_removes_only_reading(selected, expected):
    downloader = AsyncMock()
    downloader.fetch_html.side_effect = [
        '<a href="/top?id=hyogo">柏原（兵庫県）（かいばら）</a><a href="/top?id=osaka">柏原（大阪府）（かしわら）</a>',
        '<a href="https://timetable.jr-odekake.net/index">時刻表</a>', 'station-index']
    await JROdekakeTimetableScraper(downloader)._station_index(selected.name_jp)
    assert downloader.fetch_html.await_args_list[1].args[0].endswith('id=' + expected)
    assert 'keyword=%E6%9F%8F%E5%8E%9F' in downloader.fetch_html.await_args_list[0].args[0]


def test_generic_conventional_direction_can_contain_express_without_dedicated_express_heading():
    html = '<table><tr><th>福知山線</th><td><a href="javascript:void(0)" onclick="link(123)">福知山方面</a></td></tr></table>'
    tabs = JROdekakeTimetableScraper(AsyncMock())._tabs(html, 'JR特急こうのとり1号', '福知山')
    assert tabs == ['https://timetable.jr-odekake.net/station-timetable/123']


def test_dedicated_express_direction_is_preferred_without_fanning_out_to_generic_tables():
    html = '<table><tr><th>本線</th><td><a href="/station-timetable/generic">方面</a></td></tr><tr><th>特急</th><td><a href="/station-timetable/express">方面</a></td></tr></table>'
    assert JROdekakeTimetableScraper(AsyncMock())._tabs(html, 'JR特急Named', 'Target') == [
        'https://timetable.jr-odekake.net/station-timetable/express']


@pytest.mark.asyncio
async def test_bare_ambiguous_legacy_name_is_rejected_before_provider():
    repo, provider = repository(), AsyncMock()
    repo.search_stations.return_value = [s.model_copy(update={'name': 'Same'}) for s in STATIONS]
    with pytest.raises(DomainException, match='Ambiguous station identity'):
        await SearchService(provider, FakeCacheAdapter(), repo).search(SearchRequest(
            departure_station='Same', arrival_station='Nara', departure_date='2026-11-02', departure_time='09:00'))
    provider.search_routes.assert_not_awaited()


@pytest.mark.asyncio
async def test_bare_japanese_homonym_without_id_is_not_a_provider_default_selection():
    repo, provider = repository(), AsyncMock()
    repo.search_stations.return_value = STATIONS
    with pytest.raises(DomainException, match='Ambiguous station identity'):
        await SearchService(provider, FakeCacheAdapter(), repo).search(SearchRequest(
            departure_station='柏原', arrival_station='Nara', departure_date='2026-11-02', departure_time='09:00'))
    provider.search_routes.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_selected_id_never_falls_back_to_fuzzy_name():
    repo, provider = repository(), AsyncMock()
    with pytest.raises(DomainException, match='identity'):
        await SearchService(provider, FakeCacheAdapter(), repo).search(SearchRequest(
            departure_station='Kashiwara', arrival_station='Nara', departure_station_id='unknown',
            departure_date='2026-11-02', departure_time='09:00'))
    repo.search_stations.assert_not_awaited()
    provider.search_routes.assert_not_awaited()


def test_selected_identity_survives_api_query_and_response(client):
    repo, provider = repository(), AsyncMock()
    provider.search_routes.return_value = [journey(['柏原(大阪府)', '奈良'], ['JR大和路線'])]
    client.app.dependency_overrides.update({get_station_repository_port: lambda: repo,
        get_scraper_port: lambda: provider, get_cache_port: lambda: FakeCacheAdapter()})
    try:
        response = client.get('/api/v1/search', params={'departure_station': 'Kashiwara', 'arrival_station': 'Nara',
            'departure_station_id': STATIONS[0].id, 'arrival_station_id': TARGET.id,
            'departure_date': '2026-11-02', 'departure_time': '09:00'})
        assert response.status_code == 200
        assert response.json()[0]['stations'][0]['id'] == STATIONS[0].id
        assert provider.search_routes.await_args.kwargs['departure'] == '柏原(大阪)'
    finally:
        client.app.dependency_overrides.clear()
