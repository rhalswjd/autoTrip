"""Orthographic equivalence and display aliases never replace station identity."""
import sqlite3
from unittest.mock import AsyncMock

import pytest

from application.services.search_service import SearchService
from domain.exceptions import DomainException
from domain.journey import canonical_station, station_names_match
from domain.search import SearchRequest
from domain.station import Station
from domain.station_identity import station_comparison_name
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
from tests.factories import journey


@pytest.mark.parametrize(('canonical', 'provider'), [
    ('夕日ヶ浦木津温泉', '夕日ケ浦木津温泉'),
    ('茅ヶ崎', '茅ケ崎'), ('霞ヵ関', '霞カ関'),
    ('夕日ヶ浦木津温泉（京都）', '夕日ケ浦木津温泉(京都府)'),
])
def test_comparison_only_small_kana_equivalence(canonical, provider):
    assert station_names_match(canonical, provider)
    assert YahooTimetableScraper._station_names_match(canonical, provider)


@pytest.mark.parametrize(('left', 'right'), [
    ('夕日ヶ浦木津温泉(京都)', '夕日ケ浦木津温泉(兵庫)'),
    ('柏原(大阪)', '柏原(兵庫)'), ('柏原(大阪)', '柏原(滋賀)'),
    ('高田(奈良)', '高田(新潟)'), ('夕日ヶ浦木津温泉', '夕日ゲ浦木津温泉'),
    ('夕日ヶ浦木津温泉', '夕日カ浦木津温泉'), ('霞ヵ関', '霞ガ関'),
])
def test_no_fuzzy_identity_or_region_collapse(left, right):
    assert not station_names_match(left, right)
    assert not YahooTimetableScraper._station_names_match(left, right)


def test_provider_variant_binds_to_unchanged_selected_identity():
    selected = Station(id='9960914', name='Yuhigaurakitsuonsen',
                       name_jp='夕日ヶ浦木津温泉', prefecture='26')
    returned = Station(name_jp='夕日ケ浦木津温泉', provider_ids={'yahoo': 'source-code'})
    bound = SearchService._bind_station(selected, returned)
    assert bound.id == selected.id and bound.name_jp == selected.name_jp
    assert bound.prefecture == selected.prefecture and bound.name == selected.name
    assert bound.provider_ids == {'yahoo': 'source-code'}
    assert YahooTransitAdapter.station_alias(selected.name_jp) == selected.name_jp


@pytest.mark.parametrize('returned', [
    Station(name_jp='夕日ケ浦木津温泉', prefecture='28'),
    Station(name_jp='夕日ケ浦木津温泉(兵庫県)'),
])
def test_explicit_provider_region_conflict_rejected(returned):
    with pytest.raises(DomainException, match='identity mismatch'):
        SearchService._bind_station(Station(id='9960914', name_jp='夕日ヶ浦木津温泉', prefecture='26'), returned)


@pytest.mark.asyncio
async def test_verified_display_aliases_preserve_imported_names_ids_and_provider_inputs(tmp_path):
    path = str(tmp_path / 'stations.db')
    rows = [('1163907', 'Kiikatsura', '紀伊勝浦', '30'),
            ('9960914', 'Yuhigaurakitsuonsen', '夕日ヶ浦木津温泉', '26'),
            ('other', 'Already-Correct', '別駅', '26')]
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE stations(id TEXT,name_en TEXT,name_jp TEXT,prefecture TEXT,railway_company TEXT,lat REAL,lng REAL,has_midori_office INTEGER)')
        conn.executemany('INSERT INTO stations VALUES(?,?,?,?,"JR",0,0,0)', rows)
    repo = SqliteStationRepository(path)
    for row, display in zip(rows, ['Kii-Katsuura', 'Yuhigaura-Kitsuonsen', 'Already-Correct']):
        station = await repo.get_station_by_id(row[0])
        assert station.display_name_en == display
        assert station.name == row[1] and station.name_jp == row[2] and station.id == row[0]
        assert station.provider_aliases['yahoo'] == row[2]
        assert (await repo.search_stations(display))[0].id == row[0]
        cosmetic = station.model_copy(update={'display_name_en': 'Cosmetic only'})
        assert station.identity_key() == cosmetic.identity_key()
        service = SearchService(AsyncMock(), FakeCacheAdapter(), repo)
        req = SearchRequest(departure_station_id=station.id, arrival_station_id='target',
            departure_station=station.name, arrival_station='Target', departure_date='2026-11-02', departure_time='06:00')
        assert service._generate_cache_key(req) == service._generate_cache_key(req.model_copy(update={'departure_station': display}))
    assert station_comparison_name('夕日ヶ浦木津温泉') == station_comparison_name('夕日ケ浦木津温泉')
    assert canonical_station('夕日ヶ浦木津温泉') == '夕日ヶ浦木津温泉'


def test_display_alias_is_scoped_by_id_name_and_region():
    # A reused name or an inconsistent imported row must never inherit an alias.
    for row in [('different-id', 'Other', '紀伊勝浦', '30'),
                ('1163907', 'Other', '別駅', '30'), ('1163907', 'Other', '紀伊勝浦', '28')]:
        station = SqliteStationRepository._station((*row, '', 0, 0, 0))
        assert station.display_name_en == 'Other'


@pytest.mark.asyncio
async def test_cached_route_refreshes_display_without_a_new_provider_query():
    origin = Station(id='1163907', name='Kiikatsura', name_jp='紀伊勝浦', prefecture='30', display_name_en='Kii-Katsuura')
    target = Station(id='9960914', name='Yuhigaurakitsuonsen', name_jp='夕日ヶ浦木津温泉', prefecture='26', display_name_en='Yuhigaura-Kitsuonsen')
    repo, provider, cache = AsyncMock(), AsyncMock(), FakeCacheAdapter()
    repo.get_station_by_id.side_effect = lambda identity: origin if identity == origin.id else target
    service = SearchService(provider, cache, repo)
    request = SearchRequest(departure_station_id=origin.id, arrival_station_id=target.id,
        departure_station=origin.name, arrival_station=target.name, departure_date='2026-11-02', departure_time='06:00')
    old = journey([origin.name_jp, '夕日ケ浦木津温泉'], ['Rail']).model_copy(update={
        'stations': [origin.model_copy(update={'display_name_en': ''}), target.model_copy(update={'display_name_en': ''})]})
    await cache.set(service._generate_cache_key(request), [old])
    refreshed = (await service.search(request))[0]
    assert refreshed.stations[0].display_name_en == 'Kii-Katsuura'
    assert refreshed.passenger_legs[-1].arrival_station.display_name_en == 'Yuhigaura-Kitsuonsen'
    assert (await cache.get(refreshed.id)).stations[-1].id == '9960914'
    provider.search_routes.assert_not_awaited()


def test_autocomplete_api_keeps_imported_and_display_names_separate(client):
    from api.dependencies import get_station_service
    service = AsyncMock()
    service.search.return_value = [SqliteStationRepository._station(('1163907', 'Kiikatsura', '紀伊勝浦', '30', 'JR', 0, 0, 0))]
    client.app.dependency_overrides[get_station_service] = lambda: service
    try:
        response = client.get('/api/v1/stations/search', params={'q': 'Kii-Katsuura'})
        assert response.status_code == 200
        station = response.json()[0]
        assert station['english_name'] == 'Kiikatsura'
        assert station['display_name_en'] == 'Kii-Katsuura'
        assert station['display_label'] == 'Kii-Katsuura · Wakayama'
        assert station['id'] == '1163907' and station['provider_aliases']['yahoo'] == '紀伊勝浦'
    finally:
        client.app.dependency_overrides.clear()
