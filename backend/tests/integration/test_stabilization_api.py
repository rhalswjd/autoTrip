import re
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from api.dependencies import get_cache_port, get_scraper_port, get_notion_port, get_station_repository_port
from api.schemas import RouteResponseSchema, RouteSegmentSchema, DepartureInfoSchema, TimetableResponseSchema, StationSearchResponseSchema, StationSchema, SearchRequestSchema, LegSelection
from domain.timetable import DepartureInfo, Timetable
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.notion.notion_mapper import NotionMapper
from infrastructure.notion.constants import NotionColumns
from tests.factories import journey


@pytest.fixture
def through_api(client):
    cache = FakeCacheAdapter()
    scraper = AsyncMock()
    route = journey(['敦賀', '福井', '大聖寺【乗換不要】', '金沢'],
        ['ハピラインふくい', 'ハピラインふくい', 'IRいしかわ鉄道'], [False, False, True])
    scraper.search_routes.return_value = [route]
    async def timetable(route_id, departure, arrival, **kwargs):
        return Timetable(route_id=route_id, selected_calendar='saturday', source='test',
            saturday=[DepartureInfo(id=f'{departure}:{arrival}', time='08:00' if departure == '敦賀' else '09:00',
                arrival_time='08:50' if departure == '敦賀' else '10:30', train_name='Local',
                operating_date=kwargs['search_date'],
                metadata={'stop_sequence': [departure, arrival]})])
    scraper.get_timetable.side_effect = timetable
    notion = AsyncMock()
    station_repo = AsyncMock()
    station_repo.search_stations.return_value = []
    notion.save_movement.return_value = {'notion_url': 'https://notion.so/test-only'}
    client.app.dependency_overrides.update({get_cache_port: lambda: cache,
        get_scraper_port: lambda: scraper, get_notion_port: lambda: notion,
        get_station_repository_port: lambda: station_repo})
    yield client, scraper, notion
    client.app.dependency_overrides.clear()


def test_real_api_pipeline_uses_passenger_legs_and_safe_notion_mapping(through_api):
    client, scraper, notion = through_api
    response = client.get('/api/v1/search', params={'departure_station': '敦賀', 'arrival_station': '金沢',
        'departure_date': '2026-10-31', 'departure_time': '06:00'})
    assert response.status_code == 200
    # Unified duration ordering can put the independently proven direct family
    # first. Select the transfer topology this persistence regression exercises.
    route = next(r for r in response.json() if len(r['passenger_legs']) == 2)
    assert len(route['passenger_legs']) == 2
    assert route['transfer_count'] == 1
    options = []
    for index in range(2):
        timetable = client.get(f"/api/v1/routes/{route['id']}/legs/{index}/timetable")
        assert timetable.status_code == 200
        options.append(timetable.json()['saturday'][0])
    # Candidate discovery may independently probe the full destination first.
    # Exact selection must still fetch precisely the two actual passenger legs.
    assert [call.args[1:3] for call in scraper.get_timetable.await_args_list[-2:]] == [
        ('敦賀', '福井'), ('福井', '金沢')]
    legs = [{
        'passenger_leg_index': index, 'segment_index': route['passenger_legs'][index]['raw_segment_indices'][0],
        'exact_departure_id': item['id'], 'departure_station': 'untrusted', 'arrival_station': 'untrusted',
        'departure_time': item['time'], 'arrival_time': item['arrival_time'],
        'base_fare': 99999, 'express_fare': 99999,
    } for index, item in enumerate(options)]
    saved = client.post('/api/v1/movements', json={
        'route_id': route['id'], 'departure_station': '敦賀', 'arrival_station': '金沢',
        'selected_departure_time': '08:00', 'selected_arrival_time': '10:30', 'legs': legs})
    assert saved.status_code == 200
    movement = notion.save_movement.await_args.args[0]
    persisted = notion.save_movement.await_args.kwargs['legs']
    assert len(persisted) == 2
    assert persisted[1].arrival_station == '金沢'
    assert persisted[1].base_fare is None
    assert NotionColumns.FARE not in NotionMapper.map_parent_movement(movement)
    assert NotionColumns.FARE not in NotionMapper.map_leg(persisted[1], 'parent', 'Parent item')


def test_frontend_contract_exposes_every_public_timetable_and_route_field():
    types_path = Path(__file__).resolve().parents[3] / 'frontend/src/api/types.ts'
    # Docker mounts the backend; the identical frontend source is checked by its
    # TypeScript build on the host, and the local contract test runs when available.
    if not types_path.exists():
        pytest.skip('Frontend is not mounted in this Docker test environment; run the host contract check')
    source = types_path.read_text()
    for name, schema in [('Route', RouteResponseSchema), ('RouteSegment', RouteSegmentSchema),
                          ('DepartureInfo', DepartureInfoSchema), ('Timetable', TimetableResponseSchema),
                          ('StationSearchResult', StationSearchResponseSchema), ('Station', StationSchema),
                          ('SearchParams', SearchRequestSchema), ('LegSelection', LegSelection)]:
        interface = re.search(r'export interface ' + name + r' \{(.*?)\n\}', source, re.S)
        assert interface
        fields = set(re.findall(r'^\s+(\w+)\??:', interface[1], re.M))
        assert set(schema.model_fields) <= fields, (name, set(schema.model_fields) - fields)
