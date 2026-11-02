"""Small-kana endpoint and display regressions, with bounded opt-in providers."""
import json
import os
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytest

from tests.e2e.test_ui_workflow import page
from tests.e2e.test_station_identity_ui import select_exact
from tests.factories import journey
from domain.station import Station
from domain.timetable import Timetable, DepartureInfo
from domain.chronology import stamp_departure

pytestmark = pytest.mark.skipif(os.getenv('AUTOTRIP_E2E') != '1', reason='Opt-in station orthography UI')
LIVE = pytest.mark.skipif(os.getenv('AUTOTRIP_LIVE_UI') != '1', reason='Bounded real provider validation')


def test_display_aliases_render_without_changing_search_or_fare(page):
    stations = [Station(id='1163907', name='Kiikatsura', name_jp='紀伊勝浦', display_name_en='Kii-Katsuura'),
                Station(id='9960914', name='Yuhigaurakitsuonsen', name_jp='夕日ヶ浦木津温泉', display_name_en='Yuhigaura-Kitsuonsen')]
    route = journey([s.name_jp for s in stations], ['Rail']).model_copy(update={'stations': stations, 'search_date': '2026-11-02'})
    calls = []
    def api(request):
        parsed = urlparse(request.request.url)
        if parsed.path.endswith('/stations/search'):
            data = [dict(id=s.id, english_name=s.name, japanese_name=s.name_jp,
                         display_name_en=s.display_name_en) for s in stations]
        elif parsed.path.endswith('/search'):
            calls.append(parse_qs(parsed.query)); data = [route.model_dump(mode='json')]
        elif '/timetable' in parsed.path:
            data = Timetable(route_id=route.id, search_date='2026-11-02', weekday=[stamp_departure(
                DepartureInfo(id='exact', time='06:00', arrival_time='12:00', train_name='Train'), '2026-11-02')]).model_dump(mode='json')
        else:
            request.abort(); return
        request.fulfill(status=200, content_type='application/json', body=json.dumps(data))
    page.route('**/api/v1/**', api)
    page.goto('http://host.docker.internal:5174')
    assert 'Kii-Katsuura' in select_exact(page, 'Kii', stations[0].id)
    assert 'Yuhigaura-Kitsuonsen' in select_exact(page, 'Yuhigaura', stations[1].id)
    assert 'Kii-Katsuura' in page.locator('[data-selected-station-id="1163907"]').inner_text()
    assert 'Yuhigaura-Kitsuonsen' in page.locator('[data-selected-station-id="9960914"]').inner_text()
    page.locator('#route-departure-date').fill('2026-11-02')
    page.get_by_role('button', name='Search Routes', exact=True).click()
    page.get_by_test_id('route-family-card').first.click()
    for region in [page.get_by_role('list', name='Route timeline'), page.get_by_role('navigation', name='Passenger legs')]:
        assert 'Kii-Katsuura' in region.inner_text() and 'Yuhigaura-Kitsuonsen' in region.inner_text()
    assert calls[0]['arrival_station_id'] == ['9960914']
    assert calls[0]['arrival_station'] == ['夕日ヶ浦木津温泉']
    page.get_by_role('button', name='View Timetable').click()
    page.get_by_test_id('departure-card').first.click()
    page.locator('.route-summary').filter(has_text='선택 열차 운임 미확정').wait_for()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()


def begin(page, origin_query, origin_id, target_query, target_id):
    page.route('**/api/v1/movements', lambda request: request.abort())
    page.goto('http://host.docker.internal:5174')
    labels = [select_exact(page, origin_query, origin_id), select_exact(page, target_query, target_id)]
    page.locator('#route-departure-date').fill('2026-11-02')
    page.locator('#route-departure-time').fill('06:00')
    with page.expect_response(lambda response: urlparse(response.url).path == '/api/v1/search', timeout=120000) as response:
        page.get_by_role('button', name='Search Routes', exact=True).click()
    assert response.value.status == 200
    routes = response.value.json()
    assert routes and all(r['stations'][0]['id'] == origin_id and r['stations'][-1]['id'] == target_id for r in routes)
    if page.get_by_role('button', name='Show more', exact=True).count():
        page.get_by_role('button', name='Show more', exact=True).click()
    return routes, labels


@LIVE
@pytest.mark.parametrize('ride_count', [2, 3])
def test_real_kii_katsuura_yuhigaura_complete_journey(page, ride_count):
    routes, labels = begin(page, 'Kii-Katsuura', '1163907', 'Yuhigaura-Kitsuonsen', '9960914')
    assert 'Kii-Katsuura' in labels[0] and 'Yuhigaura-Kitsuonsen' in labels[1]
    candidates = [r for r in routes if len(r['passenger_legs']) == ride_count
                  and all(l['segment_type'] == 'train' for l in r['passenger_legs'])]
    chosen = min(candidates, key=lambda r: (len(r['passenger_legs']), r['departure_time']))
    assert chosen['stations'][-1]['name_jp'] == '夕日ヶ浦木津温泉'
    page.locator(f'[data-route-id="{chosen["id"]}"]').click()
    assert 'Yuhigaura-Kitsuonsen' in page.get_by_role('navigation', name='Passenger legs').inner_text()
    records = []; previous = None
    for leg in chosen['passenger_legs']:
        page.get_by_role('navigation', name='Passenger legs').get_by_role('button').nth(leg['index']).click()
        with page.expect_response(lambda response: f'/legs/{leg["index"]}/timetable' in response.url, timeout=120000) as response:
            page.get_by_role('button', name='View Timetable').click()
        data = response.value.json()
        assert response.value.status == 200 and data['availability'] == 'SUPPORTED', data
        if ride_count == 2:
            assert data['source'] == 'jr_odekake'
        else:
            assert data['source'] == ('yahoo' if leg['index'] == 2 else 'jr_odekake')
        cards = page.get_by_test_id('departure-card')
        cards.first.wait_for(timeout=120000)
        card = cards.first
        departure, arrival = card.get_attribute('data-departure-datetime'), card.get_attribute('data-arrival-datetime')
        start, end = datetime.fromisoformat(departure), datetime.fromisoformat(arrival)
        assert end >= start and (previous is None or start >= previous)
        previous = end
        records.append({'from': leg['departure_station']['name_jp'], 'to': leg['arrival_station']['name_jp'],
                        'departure': departure, 'arrival': arrival, 'provider': data['source']})
        print('EXACT_LEG', json.dumps(records[-1], ensure_ascii=False), flush=True)
        card.click()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()
    assert page.locator('[data-selected-station-id="9960914"]').count() == 1
    page.screenshot(path='/tmp/autotrip-orthography-real.png', full_page=True)
    print('ORTHOGRAPHY_REAL', json.dumps({'http': 200, 'destination_id': chosen['stations'][-1]['id'],
        'legs': records, 'notion_eligible': True}, ensure_ascii=False))


@LIVE
@pytest.mark.parametrize(('origin_query', 'origin_id', 'target_query', 'target_id', 'provider'), [
    ('Kashiwabara', '1150309', '米原', '100215', 'yahoo'),
    ('天橋立', '9960908', '福知山', '1161514', 'yahoo'),
])
def test_real_fallback_identity(page, origin_query, origin_id, target_query, target_id, provider):
    routes, _ = begin(page, origin_query, origin_id, target_query, target_id)
    chosen = next(r for r in routes if r['transfer_count'] == 0)
    page.locator(f'[data-route-id="{chosen["id"]}"]').click()
    with page.expect_response(lambda response: '/legs/0/timetable' in response.url, timeout=120000) as response:
        page.get_by_role('button', name='View Timetable').click()
    data = response.value.json()
    assert response.value.status == 200 and data['availability'] == 'SUPPORTED' and data['source'] == provider
    page.get_by_test_id('departure-card').first.wait_for(timeout=120000)
    print('FALLBACK_REAL', origin_id, target_id, provider, len(data[data['selected_calendar']]))
