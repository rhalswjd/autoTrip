"""Durable browser workflows. Opt in with AUTOTRIP_E2E=1 against local Vite."""
import json
import os
from urllib.parse import urlparse, parse_qs

import pytest

from domain.timetable import Timetable, DepartureInfo, calendar_type_for_date
from tests.factories import journey

pytestmark = pytest.mark.skipif(os.environ.get('AUTOTRIP_E2E') != '1', reason='Opt-in local browser integration')


@pytest.fixture
def page():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.set_default_timeout(45000)
        # Later test-specific routes may replace this with a mock response, but
        # no browser test may accidentally fall through to a real Notion save.
        page.route('**/api/v1/movements', lambda request: request.abort())
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        yield page
        assert errors == []
        browser.close()


def search(page, origin, destination, day, time='06:00'):
    page.goto(os.environ.get('AUTOTRIP_UI_URL', 'http://host.docker.internal:5174'))
    box = page.get_by_role('textbox', name='Search stations')
    box.fill(origin)
    page.locator('.search-result-item').filter(has=page.locator('.search-result-jp', has_text=origin)).first.click()
    box.fill(destination)
    page.locator('.search-result-item').filter(has=page.locator('.search-result-jp', has_text=destination)).first.click()
    page.locator('#route-departure-date').fill(day)
    page.locator('#route-departure-time').fill(time)
    with page.expect_response(lambda response: urlparse(response.url).path == '/api/v1/search') as searched:
        page.get_by_role('button', name='Search Routes', exact=True).click()
    page.get_by_test_id('route-family-card').first.wait_for()
    return searched.value.json()


@pytest.mark.parametrize('source', ['jr_odekake', 'yahoo'])
@pytest.mark.parametrize('status', ['SOURCE_NOT_PROVIDED', 'LOOKUP_FAILED'])
def test_platform_provenance_display_does_not_block_valid_save(page, source, status):
    route = journey(['Station A', 'Station B'], ['Rail']).model_copy(update={'search_date': '2026-11-02'})
    exact = DepartureInfo(id='platform-exact', time='08:00', arrival_time='09:00', train_name='Train', source=source,
        operating_date='2026-11-02', platform='31', platform_status='KNOWN', arrival_platform_status=status)
    def api(request):
        path = urlparse(request.request.url).path
        if path.endswith('/stations/search'):
            name = parse_qs(urlparse(request.request.url).query)['q'][0]
            data = [{'id': name, 'english_name': name, 'japanese_name': name}]
        elif path.endswith('/search'): data = [route.model_dump(mode='json')]
        elif '/timetable' in path: data = Timetable(route_id=route.id, weekday=[exact]).model_dump(mode='json')
        else:
            request.abort(); return
        request.fulfill(status=200, content_type='application/json', body=json.dumps(data))
    page.route('**/api/v1/**', api)
    search(page, 'Station A', 'Station B', '2026-11-02')
    page.get_by_test_id('route-family-card').first.click()
    page.get_by_role('button', name='View Timetable').click()
    card = page.get_by_test_id('departure-card').first
    card.wait_for()
    wording = '조회 실패' if status == 'LOOKUP_FAILED' else '공식 정보 미제공' if source == 'jr_odekake' else '출처 정보 미제공'
    assert '출발 플랫폼 31' in card.inner_text() and f'도착 플랫폼 {wording}' in card.inner_text()
    card.click()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()


@pytest.mark.parametrize('day', ['2026-10-31', '2026-11-02', '2026-11-01', '2026-11-03'])
def test_calendar_through_selection_and_safe_persistence_ui(page, day):
    route = journey(['敦賀', '福井', '大聖寺【乗換不要】', '金沢'],
        ['Rail 1', 'Rail 2', 'Rail 3'], [False, False, True]).model_copy(update={'search_date': day})
    saved = []
    searches = []
    def api(request):
        parsed = urlparse(request.request.url)
        if parsed.path.endswith('/stations/search'):
            name = parse_qs(parsed.query)['q'][0]
            data = [{'id': name, 'english_name': name, 'japanese_name': name, 'has_midori_office': False}]
        elif parsed.path.endswith('/search'):
            searches.append(parse_qs(parsed.query))
            data = [route.model_dump(mode='json')]
        elif '/timetable' in parsed.path:
            index = int(parsed.path.split('/legs/')[1].split('/')[0])
            leg = route.passenger_legs[index]
            calendar = calendar_type_for_date(day)
            data = Timetable(route_id=route.id, selected_calendar=calendar, source='jr_odekake',
                **{calendar.value: [DepartureInfo(id=f'exact-{index}', time='08:00' if index == 0 else '09:00',
                    arrival_time='08:50' if index == 0 else '10:30', train_name=f'Train {index + 1}',
                    platform='4', arrival_platform='31', source='jr_odekake', operating_date=day,
                    metadata={'stop_sequence': [leg.departure_station.name, leg.arrival_station.name]})]}).model_dump(mode='json')
        elif parsed.path.endswith('/movements'):
            saved.append(request.request.post_data_json)
            data = {'route_id': route.id, 'notion_url': 'https://notion.so/test-only'}
        else:
            request.abort()
            return
        request.fulfill(status=200, content_type='application/json', body=json.dumps(data))
    page.route('**/api/v1/**', api)
    search(page, '敦賀', '金沢', day)
    page.get_by_test_id('route-family-card').first.click()
    page.get_by_role('button', name='View Timetable').click()
    page.get_by_test_id('departure-card').first.click()
    page.get_by_role('button', name='다음 구간', exact=True).click()
    assert page.get_by_test_id('passenger-leg-heading').inner_text() == '福井 → 金沢'
    assert page.get_by_text('Remain on board: 大聖寺【乗換不要】').count() == 1
    page.get_by_role('button', name='View Timetable').click()
    page.get_by_test_id('departure-card').first.click()
    assert '09:00 → 10:30' in page.get_by_role('region', name='Selected itinerary').inner_text()
    page.locator('.route-summary').filter(has_text='선택 열차 운임 미확정').wait_for()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    page.get_by_role('button', name='Add to Notion', exact=True).click()
    page.get_by_role('region', name='Saved itinerary').wait_for()
    assert len(saved) == 1
    assert len(saved[0]['legs']) == 2
    assert saved[0]['legs'][1]['arrival_station'] == '金沢'
    assert saved[0]['search_date'] == day
    assert 'base_fare' not in saved[0]['legs'][1]
    assert len(searches) == 1
    assert searches[0]['departure_date'] == [day]
    assert searches[0]['departure_time'] == ['06:00']


@pytest.mark.skipif(os.environ.get('AUTOTRIP_LIVE_UI') != '1', reason='Opt-in bounded live-provider UI smoke')
def test_live_thunderbird_search_timetable_and_selection(page):
    # Never allow a real Notion mutation during live UI verification.
    page.route('**/api/v1/movements', lambda request: request.abort())
    failures = []
    page.on('response', lambda response: failures.append((response.status, response.url))
            if '/api/' in response.url and response.status >= 400 else None)
    search(page, '新大阪', '敦賀', '2026-10-31')
    thunderbird = page.get_by_test_id('route-family-card').filter(has_text='Thunderbird')
    assert thunderbird.count() == 1
    thunderbird.click()
    page.get_by_role('button', name='View Timetable').click()
    page.get_by_test_id('departure-card').first.wait_for()
    assert 'JR 오데카케 공식 시간표' in page.get_by_role('region', name='Passenger timetable').inner_text()
    card = page.get_by_test_id('departure-card').first
    assert '→' in card.inner_text()
    assert 'UNKNOWN' not in card.inner_text()
    assert page.get_by_test_id('departure-card').count() > 1
    href = card.get_by_role('link', name='원문 시간표').get_attribute('href')
    with page.expect_popup() as source_page:
        card.get_by_role('link', name='원문 시간표').click()
    official = source_page.value
    official.wait_for_load_state('domcontentloaded')
    assert official.url == href
    text = official.locator('body').inner_text()
    assert '新大阪' in text and '敦賀' in text and '07:54' in text
    official.close()
    for _ in range(3):
        more = page.get_by_role('button', name='다음 출발편 더 보기', exact=True)
        if not more.count():
            break
        with page.expect_response(lambda response: '/legs/0/timetable' in response.url):
            more.click()
        page.wait_for_function("() => [...document.querySelectorAll('button')].filter(b => b.textContent.includes('다음 출발편 더 보기')).every(b => !b.disabled)")
    print(json.dumps({'ui': 'Thunderbird daily timetable', 'departures': page.get_by_test_id('departure-card').count(),
                      'official_link_verified': href, 'http_failures': failures}, ensure_ascii=False))
    card.click()
    page.locator('.route-summary').filter(has_text='선택 열차 운임 미확정').wait_for()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()
    page.screenshot(path='/tmp/autotrip-live-thunderbird.png', full_page=True)
    assert failures == []


@pytest.mark.skipif(os.environ.get('AUTOTRIP_LIVE_UI') != '1', reason='Opt-in bounded live-provider UI matrix')
@pytest.mark.parametrize(('origin', 'destination', 'family', 'source', 'through'), [
    ('新大阪', '敦賀', 'Special Rapid', 'jr_odekake', False),
    ('新大阪', '名古屋', 'Shinkansen', 'yahoo', False),
    ('京都', '関西空港', 'Haruka', 'jr_odekake', False),
    ('福井', '金沢', 'Hapirain Fukui', 'yahoo', True),
    ('東舞鶴', '若狭本郷', 'Obama', 'jr_odekake', False),
    ('梅田', '新大阪', 'OsakaMetro Midosuji Line', 'yahoo', False),
])
def test_live_representative_ui(page, origin, destination, family, source, through):
    page.route('**/api/v1/movements', lambda request: request.abort())
    failures = []
    page.on('response', lambda response: failures.append(response.status)
            if '/api/' in response.url and response.status >= 400 else None)
    routes = search(page, origin, destination, '2026-10-31')
    more = page.get_by_role('button', name='Show more', exact=True)
    if more.count():
        more.click()
    cards = page.get_by_test_id('route-family-card').filter(has_text=family)
    assert cards.count() >= 1
    cards.first.click()
    panel = page.get_by_role('region', name='Passenger timetable')
    if through:
        assert '1개 탑승 구간' in panel.inner_text()
        matching = next(route for route in routes if family in route['railway_name'])
        if any(segment['is_through'] for segment in matching['segments']):
            assert 'Remain on board' in panel.inner_text()
    page.get_by_role('button', name='View Timetable').click()
    page.get_by_test_id('departure-card').first.wait_for()
    assert ('JR 오데카케 공식 시간표' if source == 'jr_odekake' else 'Yahoo 시간표') in panel.inner_text()
    if family == 'OsakaMetro Midosuji Line':
        initial_count = page.get_by_test_id('departure-card').count()
        more_departures = page.get_by_role('button', name='다음 출발편 더 보기', exact=True)
        assert more_departures.count() == 1
        with page.expect_response(lambda response: '/legs/0/timetable' in response.url) as later:
            more_departures.click()
        assert later.value.status == 200
        page.wait_for_function('(count) => document.querySelectorAll(\'[data-testid="departure-card"]\').length > count', arg=initial_count)
        print(json.dumps({'ui': 'non-JR later departures', 'before': initial_count,
                          'after': page.get_by_test_id('departure-card').count()}, ensure_ascii=False))
    # Some early metadata candidates may terminate short. Later pages remain reachable.
    card = page.get_by_test_id('departure-card').first
    train_text = card.inner_text()
    assert '→' in train_text
    if source == 'jr_odekake':
        href = card.get_by_role('link', name='원문 시간표').get_attribute('href')
        assert href.startswith('https://timetable.jr-odekake.net/train-timetable/')
        assert 'date=20261031' in href
    card.click()
    page.locator('.route-summary').filter(has_text='선택 열차 운임 미확정').wait_for()
    assert page.get_by_role('region', name='Selected itinerary').count() == 1
    print(json.dumps({'ui': f'{origin} -> {destination}', 'family': family, 'source': source,
                      'through': through, 'selected': train_text, 'http_failures': failures}, ensure_ascii=False))
    assert failures == []


@pytest.mark.skipif(os.environ.get('AUTOTRIP_LIVE_UI') != '1', reason='Opt-in live transfer topology')
def test_live_direct_and_transfer_families_and_all_actual_selections(page):
    page.route('**/api/v1/movements', lambda request: request.abort())
    routes = search(page, '敦賀', '金沢', '2026-10-31')
    direct = [r for r in routes if r['transfer_count'] == 0 and 'Hapirain' in r['railway_name']]
    transfers = [r for r in routes if r['transfer_count'] == 1
                 and any('福井' in leg['arrival_station']['name_jp'] for leg in r['passenger_legs'])
                 and 'Hapirain' in r['railway_name']]
    assert direct and transfers
    assert direct[0]['family_key'] != transfers[0]['family_key']
    chosen = transfers[0]
    more = page.get_by_role('button', name='Show more', exact=True)
    if more.count():
        more.click()
    page.locator(f'[data-route-id="{chosen["id"]}"]').click()
    records = []
    for leg in chosen['passenger_legs']:
        if leg['segment_type'] == 'walk':
            page.get_by_role('button', name='다음 구간', exact=True).click()
            continue
        with page.expect_response(lambda response: f'/legs/{leg["index"]}/timetable' in response.url) as timetable:
            page.get_by_role('button', name='View Timetable').click()
        payload = timetable.value.json()
        assert timetable.value.status == 200
        if leg['index'] == 0:
            assert all('金沢' not in item.get('metadata', {}).get('stop_sequence', [])
                       for item in payload[payload['selected_calendar']])
        card = page.get_by_test_id('departure-card').first
        card.wait_for()
        records.append(card.inner_text())
        card.click()
        if leg['index'] < len(chosen['passenger_legs']) - 1:
            page.get_by_role('button', name='다음 구간', exact=True).click()
        else:
            page.get_by_role('button', name='일정 확인', exact=True).click()
    assert len(records) == 2
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()
    print(json.dumps({'ui': '敦賀 -> 金沢 via actual transfer', 'selections': records,
                      'passenger_legs': len(records), 'raw_segments': len(chosen['segments'])}, ensure_ascii=False))


@pytest.mark.skipif(os.environ.get('AUTOTRIP_LIVE_UI') != '1', reason='Opt-in real official calendar smoke')
@pytest.mark.parametrize(('day', 'calendar'), [('2026-11-02', 'weekday'), ('2026-11-03', 'holiday')])
def test_live_official_calendar_ui(page, day, calendar):
    page.route('**/api/v1/movements', lambda request: request.abort())
    search(page, '新大阪', '敦賀', day)
    page.get_by_test_id('route-family-card').filter(has_text='Thunderbird').click()
    with page.expect_response(lambda response: '/legs/0/timetable' in response.url) as response:
        page.get_by_role('button', name='View Timetable').click()
    data = response.value.json()
    assert response.value.status == 200
    assert data['source'] == 'jr_odekake'
    assert data['selected_calendar'] == calendar
    assert data[calendar]
    assert all(option['operating_date'] == day for option in data[calendar])
    page.get_by_test_id('departure-card').first.wait_for()
    assert 'Weekday' in page.get_by_role('region', name='Passenger timetable').inner_text() if calendar == 'weekday' else 'Sunday / Holiday' in page.get_by_role('region', name='Passenger timetable').inner_text()
    print(json.dumps({'calendar_ui': day, 'calendar': calendar, 'departures': len(data[calendar])}, ensure_ascii=False))
