"""Station selection is by identity, never result position or fuzzy name downstream."""
import json
import os
from urllib.parse import parse_qs, urlparse
import pytest
from tests.e2e.test_ui_workflow import page
from tests.factories import journey

pytestmark = pytest.mark.skipif(os.getenv('AUTOTRIP_E2E') != '1', reason='Opt-in station identity UI')


@pytest.mark.parametrize('long_name', ['Kashihara-jingu-mae', 'Kashihara-jingu-nishiguchi'])
def test_ambiguous_selection_metadata_overflow_and_collapsed_routes(page, long_name):
    stations = [{'id': 'osaka', 'english_name': long_name, 'japanese_name': '柏原(大阪)', 'region': 'Osaka', 'prefecture': '27', 'has_midori_office': True},
                {'id': 'hyogo', 'english_name': 'Kaibara', 'japanese_name': '柏原(兵庫)', 'region': 'Hyogo', 'has_midori_office': True},
                {'id': 'nara', 'english_name': 'Nara', 'japanese_name': '奈良', 'region': 'Nara', 'has_midori_office': True}]
    routes = [journey(['柏原(大阪)', '奈良'], ['JR大和路線'], id=f'family-{i}').model_dump(mode='json') for i in range(6)]
    requests = []
    def api(request):
        parsed = urlparse(request.request.url)
        if parsed.path.endswith('/stations/search'):
            data = stations
        elif parsed.path.endswith('/search'):
            requests.append(parse_qs(parsed.query)); data = routes
        else:
            request.abort(); return
        request.fulfill(status=200, content_type='application/json', body=json.dumps(data))
    page.route('**/api/v1/**', api)
    page.set_viewport_size({'width': 380, 'height': 900})
    page.goto('http://host.docker.internal:5174')
    box = page.get_by_role('textbox', name='Search stations'); box.fill('kashi')
    card = page.locator('[data-station-id="osaka"]')
    card.wait_for()
    assert 'Osaka' in card.inner_text()
    assert 'Hyogo' in page.locator('[data-station-id="hyogo"]').inner_text()
    assert card.evaluate('(e) => e.scrollWidth <= e.clientWidth')
    for child in (card.locator('.search-result-name'), card.get_by_text('Midori Office')):
        bounds, parent = child.bounding_box(), card.bounding_box()
        assert bounds['x'] >= parent['x'] and bounds['x'] + bounds['width'] <= parent['x'] + parent['width'] + 1
    page.locator('.search-container').screenshot(path=f'/tmp/autotrip-station-{long_name}.png')
    card.click()
    page.locator('[data-station-id="nara"]').click()
    page.locator('#route-departure-date').fill('2026-11-02')
    page.locator('#route-departure-time').fill('09:00')
    page.get_by_role('button', name='Search Routes', exact=True).click()
    cards = page.get_by_test_id('route-family-card')
    cards.first.wait_for()
    assert requests[0]['departure_station_id'] == ['osaka']
    assert requests[0]['arrival_station_id'] == ['nara']
    assert cards.count() == 3
    page.get_by_role('button', name='Show more', exact=True).click()
    assert cards.count() == 6
    page.get_by_role('button', name='Show less', exact=True).click()
    assert cards.count() == 3


def select_exact(page, query, station_id):
    page.get_by_role('textbox', name='Search stations').fill(query)
    card = page.locator(f'[data-station-id="{station_id}"]')
    card.wait_for()
    text = card.inner_text()
    card.click()
    return text


@pytest.mark.skipif(os.getenv('AUTOTRIP_LOCAL_UI') != '1', reason='Opt-in real local autocomplete without provider traffic')
def test_fuzzy_autocomplete_selection_sends_exact_id(page):
    captured = []
    def route_search(request):
        captured.append(parse_qs(urlparse(request.request.url).query))
        request.fulfill(status=200, content_type='application/json', body='[]')
    page.route('**/api/v1/search?**', route_search)
    page.goto('http://host.docker.internal:5174')
    for query in ('Bingo-Ochiai', 'Bingo Ochiai', 'bingo', 'bigo', '備後落合'):
        page.get_by_role('textbox', name='Search stations').fill(query)
        page.locator('[data-station-id="1170618"]').wait_for()
    select_exact(page, 'bigo', '1170618')
    select_exact(page, 'Nara', '1160704')
    assert page.locator('[data-selected-station-id="1170618"]').count() == 1
    page.get_by_role('button', name='Search Routes', exact=True).click()
    page.get_by_text('No Routes Found', exact=True).wait_for()
    assert captured[0]['departure_station_id'] == ['1170618']
    assert captured[0]['arrival_station_id'] == ['1160704']


LIVE = pytest.mark.skipif(os.getenv('AUTOTRIP_LIVE_UI') != '1', reason='Opt-in bounded providers')


@LIVE
@pytest.mark.parametrize(('origin_query', 'origin_id', 'target_query', 'target_id', 'region'), [
    ('Kashiwara', '1160712', 'Nara', '1160704', 'Osaka'),
    ('Kaibara', '1163005', 'Fukuchiyama', '1161514', 'Hyogo'),
    ('Kashiwabara', '1150309', '近江長岡', '1150310', 'Shiga'),
    ('Takada', '1163606', 'Sakurai', '1163710', 'Nara'),
    ('福井', '100917', '加賀温泉', '100915', 'Fukui'),
])
def test_real_selected_station_is_preserved_through_route_and_timetable(page, origin_query, origin_id, target_query, target_id, region):
    page.route('**/api/v1/movements', lambda r: r.abort())
    page.goto('http://host.docker.internal:5174')
    origin_card = select_exact(page, origin_query, origin_id)
    assert region in origin_card
    target_card = select_exact(page, target_query, target_id)
    selected = page.locator('.route-fields-wrapper').inner_text()
    assert region in selected
    page.locator('#route-departure-date').fill('2026-11-02')
    page.locator('#route-departure-time').fill('09:00')
    with page.expect_response(lambda r: urlparse(r.url).path == '/api/v1/search', timeout=120000) as response:
        page.get_by_role('button', name='Search Routes', exact=True).click()
    assert response.value.status == 200
    request = parse_qs(urlparse(response.value.url).query)
    assert request['departure_station_id'] == [origin_id] and request['arrival_station_id'] == [target_id]
    routes = response.value.json()
    assert routes and all(r['stations'][0]['id'] == origin_id and r['stations'][-1]['id'] == target_id for r in routes)
    if origin_id == '1160712':
        assert all('こうのとり' not in s['railway_name_jp'] for r in routes for s in r['segments'])
        # Some Yahoo ordering pages omit stationCode; retain it wherever published.
        assert any(r['stations'][0]['provider_ids'].get('yahoo') == '25868' for r in routes)
    cards = page.get_by_test_id('route-family-card')
    cards.first.click()
    with page.expect_response(lambda r: '/legs/0/timetable' in r.url, timeout=120000) as timetable:
        page.get_by_role('button', name='View Timetable').click()
    data = timetable.value.json()
    assert timetable.value.status == 200 and data['availability'] != 'PROVIDER_ERROR'
    if origin_id in ('1160712', '1163005', '1163606'):
        assert data['availability'] == 'SUPPORTED'
        assert data[data['selected_calendar']] or not data['complete']
    if origin_id == '1163606':
        page.screenshot(path='/tmp/autotrip-station-takada.png', full_page=True)
    print(json.dumps({'identity_ui': [origin_id,target_id], 'cards':[origin_card,target_card],
        'query':request,'route':routes[0]['railway_name'],'duration':routes[0]['total_duration'],
        'stations':[(s['id'],s['name_jp'],s.get('provider_ids')) for s in routes[0]['stations']],
        'timetable':data['availability'],'departures':len(data[data['selected_calendar']])}, ensure_ascii=False))
