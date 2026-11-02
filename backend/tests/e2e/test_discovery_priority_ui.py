"""Official named-service discovery; all real Notion writes are blocked."""
import os
from datetime import datetime
from urllib.parse import urlparse

import pytest

from tests.e2e.test_ui_workflow import page, search
from tests.e2e.test_station_identity_ui import select_exact

pytestmark = pytest.mark.skipif(os.getenv('AUTOTRIP_E2E') != '1' or os.getenv('AUTOTRIP_LIVE_UI') != '1',
                                reason='Opt-in bounded provider/browser regression')


def test_official_hashidate_one_ride_exact_selection_and_source(page):
    page.route('**/api/v1/movements', lambda request: request.abort())
    page.goto('http://host.docker.internal:5174')
    select_exact(page, '京都', '100216')
    select_exact(page, 'Yuhigaura-Kitsuonsen', '9960914')
    page.locator('#route-departure-date').fill('2026-11-02')
    page.locator('#route-departure-time').fill('11:30')
    with page.expect_response(lambda response: urlparse(response.url).path == '/api/v1/search', timeout=120000) as response:
        page.get_by_role('button', name='Search Routes', exact=True).click()
    assert response.value.status == 200
    routes = response.value.json()
    chosen = next(r for r in routes if len(r['passenger_legs']) == 1 and 'Hashidate' in r['railway_name'])
    leg = chosen['passenger_legs'][0]
    assert leg['arrival_station']['id'] == '9960914' and leg['through_boundaries'] == []
    assert [s['name_jp'] for s in chosen['stations']] == ['京都', '夕日ヶ浦木津温泉']
    more = page.get_by_role('button', name='Show more', exact=True)
    if more.count(): more.click()
    page.locator(f'[data-route-id="{chosen["id"]}"]').click()
    with page.expect_response(lambda response: '/legs/0/timetable' in response.url, timeout=120000) as response:
        page.get_by_role('button', name='View Timetable').click()
    data = response.value.json()
    assert response.value.status == 200 and data['availability'] == 'SUPPORTED' and data['source'] == 'jr_odekake'
    entries = data[data['selected_calendar']]
    exact = next(e for e in entries if '7号' in e['train_name'])
    assert exact['time'] == '12:25' and exact['arrival_time'] == '15:11'
    assert '福知山' in exact['metadata']['stop_sequence']
    assert '夕日ヶ浦木津温泉' in exact['metadata']['stop_sequence']
    assert datetime.fromisoformat(exact['departure_datetime']) < datetime.fromisoformat(exact['arrival_datetime'])
    card = page.get_by_test_id('departure-card').filter(has_text=exact['time']).first
    with page.expect_popup() as opened:
        card.get_by_role('link', name='원문 시간표').click()
    official = opened.value; official.wait_for_load_state('domcontentloaded')
    text = official.locator('body').inner_text()
    assert '京都' in text and '夕日ヶ浦木津温泉' in text and '15:11' in text
    official.close(); card.click()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()
    page.screenshot(path='/tmp/autotrip-official-hashidate.png', full_page=True)
    print('HASHIDATE_OFFICIAL_UI',exact['time'],exact['arrival_time'],'platform',exact['platform'],
          'one_leg',len(chosen['passenger_legs']),'source',exact['source_url'],'notion_eligible',True)


def test_retained_special_rapid_direct_timetable(page):
    page.route('**/api/v1/movements', lambda request: request.abort())
    routes = search(page, '新大阪', '敦賀', '2026-11-02')
    chosen = next(r for r in routes if len(r['passenger_legs']) == 1
                  and any('新快速' in name for name in r['passenger_legs'][0]['railway_names_jp']))
    more = page.get_by_role('button', name='Show more', exact=True)
    if more.count(): more.click()
    page.locator(f'[data-route-id="{chosen["id"]}"]').click()
    with page.expect_response(lambda response: '/legs/0/timetable' in response.url, timeout=120000) as response:
        page.get_by_role('button', name='View Timetable').click()
    data = response.value.json()
    assert response.value.status == 200 and data['availability'] == 'SUPPORTED' and data['source'] == 'jr_odekake'
    departures = data[data['selected_calendar']]
    assert departures and all('敦賀' in d['metadata']['stop_sequence'] for d in departures)
    page.get_by_test_id('departure-card').first.wait_for()
    page.get_by_test_id('departure-card').first.click()
    page.get_by_role('button', name='일정 확인', exact=True).click()
    assert page.get_by_role('button', name='Add to Notion', exact=True).is_enabled()
    print('RETAINED_SPECIAL_RAPID',[(d['time'],d['arrival_time']) for d in departures],data['complete'])
