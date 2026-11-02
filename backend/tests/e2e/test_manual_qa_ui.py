"""Actual browser regressions; provider traffic is explicit opt-in and cached."""
import json
import os
from urllib.parse import urlparse, parse_qs

import pytest
from tests.e2e.test_ui_workflow import page, search
from tests.factories import journey
from domain.timetable import Timetable, DepartureInfo
from domain.journey import station_names_match

pytestmark = pytest.mark.skipif(os.getenv('AUTOTRIP_E2E') != '1', reason='Opt-in browser regression')


@pytest.mark.parametrize(('bus_first', 'status'), [(True, 'unsupported'), (False, 'unsupported'), (True, 'provider_error')])
def test_mixed_provider_navigation_never_blocks_supported_ride(page, bus_first, status):
    route = journey(['Station A', 'Station B', 'Station C'], ['Bus' if bus_first else 'JR新幹線', 'JR新幹線' if bus_first else 'Bus'])
    bus_index = 0 if bus_first else 1
    route = route.model_copy(update={'segments': [segment.model_copy(update={'segment_type': 'bus' if i == bus_index else 'train'}) for i, segment in enumerate(route.segments)]})
    def api(request):
        path = urlparse(request.request.url).path
        if path.endswith('/stations/search'):
            name = parse_qs(urlparse(request.request.url).query)['q'][0]
            data = [{'id': name, 'english_name': name, 'japanese_name': name}]
        elif path.endswith('/search'):
            data = [route.model_dump(mode='json')]
        elif '/timetable' in path:
            index = int(path.split('/legs/')[1].split('/')[0])
            data = Timetable(route_id=route.id, status=status if index == bus_index else 'available',
                selected_calendar='weekday', source='jr_odekake', weekday=[] if index == bus_index else [
                    DepartureInfo(id='exact', time='08:00', arrival_time='09:00', platform='14',
                        train_name='つるぎ', source='jr_odekake', operating_date='2026-11-02')]).model_dump(mode='json')
        else:
            request.abort()
            return
        request.fulfill(status=200, content_type='application/json', body=json.dumps(data))
    page.route('**/api/v1/**', api)
    search(page, 'Station A', 'Station C', '2026-11-02')
    page.get_by_test_id('route-family-card').click()
    nav = page.get_by_role('navigation', name='Passenger legs')
    nav.get_by_role('button').nth(bus_index).click()
    page.get_by_role('button', name='View Timetable').click()
    page.locator('[data-availability="UNSUPPORTED"], [data-availability="PROVIDER_ERROR"]').wait_for()
    nav.get_by_role('button').nth(1 - bus_index).click()
    page.get_by_role('button', name='View Timetable').click()
    page.get_by_test_id('departure-card').click()
    assert '08:00 → 09:00' in page.get_by_role('region', name='Selected itinerary').inner_text()
    # An unsupported ride is navigable, never fabricated or silently persisted.
    if bus_first:
        page.get_by_role('button', name='일정 확인', exact=True).click()
        assert page.get_by_role('button', name='Add to Notion', exact=True).is_disabled()


LIVE = pytest.mark.skipif(os.getenv('AUTOTRIP_LIVE_UI') != '1', reason='Opt-in bounded real providers')


@LIVE
@pytest.mark.parametrize(('origin', 'target', 'family', 'source'), [
    ('新大阪', '敦賀', 'Thunderbird', 'jr_odekake'),
    ('敦賀', '金沢', 'Shinkansen', 'jr_odekake'),
    ('京都', '関西空港', 'Haruka', 'jr_odekake'),
    ('新大阪', '名古屋', 'Shinkansen', 'yahoo'),
    ('餘部', '鳥取', 'Sanin', 'jr_odekake'),
    ('東舞鶴', '若狭本郷', 'Obama', 'jr_odekake'),
], ids=['thunderbird', 'tsuruga-shinkansen', 'haruka', 'nagoya-shinkansen', 'amarube', 'wakasa'])
def test_actual_supported_daily_timetable_and_exact_selection(page, origin, target, family, source):
    failures, saved = [], []
    page.on('response', lambda response: failures.append(response.status) if '/api/' in response.url and response.status >= 400 else None)
    def save(request):
        saved.append(request.request.post_data_json)
        request.fulfill(status=200, content_type='application/json', body=json.dumps({'notion_url': 'https://example.com/test-only'}))
    page.route('**/api/v1/movements', save)
    routes = search(page, origin, target, '2026-11-02')
    matching = [r for r in routes if family in r['railway_name'] and r['transfer_count'] == 0]
    assert matching
    if family == 'Thunderbird':
        assert len(matching) == 1
    chosen = matching[0]
    page.locator(f'[data-route-id="{chosen["id"]}"]').click()
    with page.expect_response(lambda r: '/legs/0/timetable' in r.url, timeout=120000) as response:
        page.get_by_role('button', name='View Timetable').click()
    payload = response.value.json()
    assert response.value.status == 200 and payload['status'] == 'available'
    assert payload['source'] == source
    departures = payload[payload['selected_calendar']]
    assert departures and all(d['operating_date'] == '2026-11-02' for d in departures)
    card = page.get_by_test_id('departure-card').first
    card.wait_for()
    exact_text = card.inner_text()
    assert '→' in exact_text
    href = card.get_by_role('link', name='원문 시간표').get_attribute('href')
    if source == 'jr_odekake':
        assert 'date=20261102' in href
    else:
        assert href.startswith('https://transit.yahoo.co.jp/') and 'ym=202611' in href and 'd=2' in href
    if family == 'Thunderbird':
        with page.expect_popup() as opened:
            card.get_by_role('link', name='원문 시간표').click()
        official = opened.value
        official.wait_for_load_state('domcontentloaded')
        text = official.locator('body').inner_text()
        assert origin in text and target in text and '07:54' in text
        official.close()
    card.click()
    page.locator('.route-summary').filter(has_text='선택 열차 운임 미확정').wait_for()
    if len(chosen['passenger_legs']) == 1:
        page.get_by_role('button', name='일정 확인', exact=True).click()
        page.get_by_role('button', name='Add to Notion', exact=True).click()
        page.get_by_role('region', name='Saved itinerary').wait_for()
        assert len(saved) == 1 and len(saved[0]['legs']) == 1
        assert 'base_fare' not in saved[0]['legs'][0]
    assert failures == []
    page.screenshot(path=f'/tmp/autotrip-manual-{family}.png', full_page=True)
    print(json.dumps({'ui': f'{origin} → {target}', 'family': family, 'source': source,
        'departures': len(departures), 'selected': exact_text, 'fare': chosen['fare_breakdown'],
        'save_payload_legs': len(saved[0]['legs']) if saved else 'walk connection retained', 'http_errors': failures}, ensure_ascii=False))


@LIVE
def test_actual_hapi_direct_transfer_and_mixed_sections(page):
    routes = search(page, '敦賀', '金沢', '2026-11-02', '13:00')
    if page.get_by_role('button', name='Show more', exact=True).count():
        page.get_by_role('button', name='Show more', exact=True).click()
    direct = [r for r in routes if 'Hapirain' in r['railway_name'] and r['transfer_count'] == 0]
    transfer = [r for r in routes if 'Hapirain' in r['railway_name'] and r['transfer_count'] == 1 and any(station_names_match(leg['arrival_station']['name_jp'], '福井') for leg in r['passenger_legs']) and all(leg['segment_type'] != 'bus' for leg in r['passenger_legs'])]
    assert direct and transfer and direct[0]['family_key'] != transfer[0]['family_key']
    assert direct[0]['result_kind'] == 'daily_alternative'
    page.locator(f'[data-route-id="{direct[0]["id"]}"]').click()
    page.get_by_role('button', name='View Timetable').click()
    page.get_by_test_id('departure-card').first.wait_for(timeout=120000)
    assert '06:05' in page.get_by_test_id('departure-card').first.inner_text()
    page.locator(f'[data-route-id="{transfer[0]["id"]}"]').click()
    assert len(transfer[0]['passenger_legs']) == 2
    for leg in transfer[0]['passenger_legs']:
        page.get_by_role('navigation', name='Passenger legs').get_by_role('button').nth(leg['index']).click()
        page.get_by_role('button', name='View Timetable').click()
        page.get_by_test_id('departure-card').first.wait_for(timeout=120000)
        page.get_by_test_id('departure-card').first.click()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()
    print(json.dumps({'ui': 'Hapi direct vs transfer', 'direct': direct[0]['departure_time'], 'transfer_legs': len(transfer[0]['passenger_legs'])}))
    for route in routes:
        if not any(leg['segment_type'] == 'bus' for leg in route['passenger_legs']):
            continue
        jr = next((leg for leg in route['passenger_legs'] if any('新幹線' in n for n in leg['railway_names_jp'])), None)
        if jr is None:
            continue
        page.locator(f'[data-route-id="{route["id"]}"]').click()
        nav = page.get_by_role('navigation', name='Passenger legs')
        bus = next(leg for leg in route['passenger_legs'] if leg['segment_type'] == 'bus')
        nav.get_by_role('button').nth(bus['index']).click()
        page.get_by_role('button', name='View Timetable').click()
        page.locator('[data-availability="UNSUPPORTED"]').wait_for()
        nav.get_by_role('button').nth(jr['index']).click()
        page.get_by_role('button', name='View Timetable').click()
        page.get_by_test_id('departure-card').first.wait_for(timeout=120000)
        print('REAL_MIXED_JR_INDEPENDENT', jr['index'], bus['index'])
        break


@LIVE
def test_actual_late_options_and_station_autocomplete(page):
    routes = search(page, '京都', '関西空港', '2026-11-02', '23:00')
    if page.get_by_role('button', name='Show more', exact=True).count():
        page.get_by_role('button', name='Show more', exact=True).click()
    assert any(r['result_kind'] == 'requested' for r in routes)
    later = [r for r in routes if r['result_kind'] == 'later_practical' and 'Haruka' in r['railway_name']]
    assert later and later[0]['search_date'] == '2026-11-03'
    assert '286m shorter' in later[0]['alternative_reason']
    assert page.locator('[data-result-kind="requested"]').count() == 1
    assert page.locator('[data-result-kind="later_practical"]').count() == 1
    shortcut = page.get_by_role('navigation', name='Alternative service shortcuts').get_by_role('button', name='Later, simpler option:')
    assert shortcut.is_visible()
    assert page.get_by_role('combobox', name='Sort by').input_value() == 'time'
    page.get_by_role('combobox', name='Sort by').select_option('fare')
    page.screenshot(path='/tmp/autotrip-manual-late.png', full_page=True)
    shortcut.click()
    with page.expect_response(lambda r: '/legs/0/timetable' in r.url, timeout=120000) as response:
        page.get_by_role('button', name='View Timetable').click()
    data = response.value.json()
    assert response.value.status == 200 and data['selected_calendar'] == 'holiday'
    assert data['holiday'] and all(d['operating_date'] == '2026-11-03' for d in data['holiday'])
    for query in ('Bingo-Ochiai', 'Bingo Ochiai', 'bingo', '備後落合', 'bigo'):
        page.get_by_role('textbox', name='Search stations').fill(query)
        page.locator('.search-result-item').filter(has=page.locator('.search-result-jp', has_text='備後落合')).first.wait_for()
    print('LATE_STRICT_AND_HARUKA_VISIBLE; STATION_EXACT_NORMALIZED_TYPO_PASS')
