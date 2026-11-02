import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
from unittest.mock import AsyncMock
import pytest
from tests.e2e.test_ui_workflow import page, search
from tests.e2e.test_station_identity_ui import select_exact
from tests.factories import journey
from domain.timetable import Timetable, DepartureInfo
from domain.chronology import stamp_departure

pytestmark=pytest.mark.skipif(os.getenv('AUTOTRIP_E2E')!='1',reason='Opt-in chronology browser tests')


@pytest.mark.parametrize('overnight',[False,True])
def test_date_filter_clearing_and_notion_eligibility(page,overnight):
    route=journey(['Station A','Station B','Station C'],['Rail','Rail']).model_copy(update={'search_date':'2026-11-01'})
    calls=[]
    def api(request):
        parsed=urlparse(request.request.url); params=parse_qs(parsed.query)
        if parsed.path.endswith('/stations/search'):
            name=params['q'][0]; data=[{'id':name,'english_name':name,'japanese_name':name}]
        elif parsed.path.endswith('/search'):data=[route.model_dump(mode='json')]
        elif '/timetable' in parsed.path:
            index=int(parsed.path.split('/legs/')[1].split('/')[0]); day=params.get('date',['2026-11-01'])[0]
            calls.append((index,day))
            times=([('23:30','23:55')] if overnight else [('06:29','07:57'),('08:00','09:00')]) if index==0 else (
                [('00:10','00:30')] if day=='2026-11-02' else [('23:40','23:50')] if overnight else [('00:03','00:18'),('08:10','08:30'),('10:00','10:30')])
            entries=[stamp_departure(DepartureInfo(id=f'{index}-{time}',time=time,arrival_time=arr,operating_date=day,train_name='Train'),day) for time,arr in times]
            data=Timetable(route_id=route.id,selected_calendar='holiday' if day=='2026-11-01' else 'weekday',
                search_date=day,**{('holiday' if day=='2026-11-01' else 'weekday'):entries}).model_dump(mode='json')
        else:
            request.abort();return
        request.fulfill(status=200,content_type='application/json',body=json.dumps(data))
    page.route('**/api/v1/**',api)
    search(page,'Station A','Station C','2026-11-01')
    page.get_by_test_id('route-family-card').click()
    nav=page.get_by_role('navigation',name='Passenger legs')
    if not overnight:
        nav.get_by_role('button').nth(1).click();page.get_by_role('button',name='View Timetable').click()
        page.get_by_test_id('departure-card').filter(has_text='08:10').click()
        page.get_by_role('button',name='일정 확인',exact=True).click()
        assert page.get_by_role('button',name='Add to Notion',exact=True).is_disabled()
        nav.get_by_role('button').nth(0).click()
    page.get_by_role('button',name='View Timetable').click()
    page.get_by_test_id('departure-card').first.click()
    page.get_by_role('button',name='다음 구간',exact=True).click()
    page.get_by_role('button',name='View Timetable').click()
    expected='00:10' if overnight else '08:10'
    page.get_by_test_id('departure-card').filter(has_text=expected).wait_for()
    assert page.get_by_test_id('departure-card').filter(has_text='00:03' if not overnight else '23:40').count()==0
    assert '2026-11-01' in page.get_by_role('region',name='Passenger timetable').inner_text()
    page.get_by_test_id('departure-card').filter(has_text=expected).click()
    page.get_by_role('button',name='일정 확인',exact=True).click()
    assert page.get_by_role('button',name='Add to Notion',exact=True).is_enabled()
    if overnight:
        assert calls.count((1,'2026-11-02'))==1
        assert '2026-11-02 00:10' in page.get_by_role('region',name='Selected itinerary').inner_text()
    else:
        nav.get_by_role('button').nth(0).click();page.get_by_role('button',name='View Timetable').click()
        page.get_by_test_id('departure-card').filter(has_text='08:00').click()
        assert '08:10' not in page.get_by_role('region',name='Selected itinerary').inner_text()
        nav.get_by_role('button').nth(1).click();page.get_by_role('button',name='View Timetable').click()
        page.get_by_test_id('departure-card').filter(has_text='10:00').wait_for()
        assert page.get_by_test_id('departure-card').filter(has_text='08:10').count()==0


LIVE=pytest.mark.skipif(os.getenv('AUTOTRIP_LIVE_UI')!='1',reason='Bounded real provider smoke')


def begin(page,target_id,target_query):
    page.goto('http://host.docker.internal:5174')
    select_exact(page,'Kashiwabara','1150309');select_exact(page,target_query,target_id)
    page.locator('#route-departure-date').fill('2026-11-01')
    page.locator('#route-departure-time').fill('23:57')
    with page.expect_response(lambda r:urlparse(r.url).path=='/api/v1/search',timeout=120000) as response:
        page.get_by_role('button',name='Search Routes',exact=True).click()
    assert response.value.status==200
    more=page.get_by_role('button',name='Show more',exact=True)
    if more.count():more.click()
    return response.value.json()


@LIVE
def test_real_central_fallback_and_complete_takada_journey(page):
    from application.services.movement_service import MovementService
    from api.dependencies import get_cache_port
    from api.schemas import LegSelection
    saved=[]
    def save(request):
        payload=request.request.post_data_json; saved.append(payload)
        notion=AsyncMock();notion.save_movement.return_value={'notion_url':'https://example.com/mock-only'}
        async def validate():
            return await MovementService(get_cache_port(),notion).create_movement(payload['route_id'],payload['departure_station'],payload['arrival_station'],
                payload.get('search_time'),payload.get('search_date'),payload['selected_departure_time'],payload['selected_arrival_time'],
                legs=[LegSelection.model_validate(leg) for leg in payload['legs']])
        with ThreadPoolExecutor(max_workers=1) as worker:
            _,result=worker.submit(lambda:asyncio.run(validate())).result()
        assert notion.save_movement.await_count==1
        request.fulfill(status=200,content_type='application/json',body=json.dumps(result))
    page.route('**/api/v1/movements',save)
    routes=begin(page,'1163606','高田(奈良)')
    chosen=next(r for r in routes if any(l['departure_station']['name_jp']=='大阪' and l['arrival_station']['name_jp']=='鶴橋' for l in r['passenger_legs'])
                and any(l['arrival_station']['name_jp']=='大和高田' for l in r['passenger_legs']))
    assert chosen['stations'][-1]['id']=='1163606'
    page.locator(f'[data-route-id="{chosen["id"]}"]').click()
    records=[]; previous=None
    for leg in chosen['passenger_legs']:
        page.get_by_role('navigation',name='Passenger legs').get_by_role('button').nth(leg['index']).click()
        if leg['segment_type']=='walk':
            assert '도보' in page.get_by_role('region',name='Passenger timetable').inner_text()
            continue
        with page.expect_response(lambda r:f'/legs/{leg["index"]}/timetable' in r.url,timeout=120000) as response:
            page.get_by_role('button',name='View Timetable').click()
        data=response.value.json(); assert response.value.status==200 and data['availability']=='SUPPORTED'
        cards=page.get_by_test_id('departure-card');cards.first.wait_for(timeout=120000)
        if leg['index']==1:
            wanted=cards.filter(has_text='06:29')
            card=wanted.first if wanted.count() else cards.first
        else:card=cards.first
        departure=card.get_attribute('data-departure-datetime');arrival=card.get_attribute('data-arrival-datetime')
        assert departure and arrival
        from datetime import datetime
        start,end=datetime.fromisoformat(departure),datetime.fromisoformat(arrival)
        assert end>=start and (previous is None or start>=previous)
        previous=end
        if leg['index']==0:
            assert data['source']=='yahoo'
            assert 'Yahoo 시간표' in page.get_by_role('region',name='Passenger timetable').inner_text()
        records.append({'origin':leg['departure_station']['name_jp'],'destination':leg['arrival_station']['name_jp'],
                        'departure':departure,'arrival':arrival,'source':data['source']})
        card.click()
    page.get_by_role('button',name='일정 확인',exact=True).click()
    assert page.get_by_role('button',name='Add to Notion',exact=True).is_enabled()
    page.get_by_role('button',name='Add to Notion',exact=True).click()
    page.get_by_role('region',name='Saved itinerary').wait_for()
    assert len(saved[0]['legs'])==len(records)
    print('REAL_FULL_JOURNEY',json.dumps(records,ensure_ascii=False))
    print('DESTINATION',chosen['stations'][-1]['id'],[(l['departure_station']['name_jp'],l['arrival_station']['name_jp']) for l in chosen['passenger_legs'] if l['segment_type']=='walk'])


@LIVE
def test_real_kashiwabara_maibara_yahoo(page):
    routes=begin(page,'100215','米原')
    route=next(r for r in routes if r['transfer_count']==0)
    page.locator(f'[data-route-id="{route["id"]}"]').click()
    with page.expect_response(lambda r:'/legs/0/timetable' in r.url,timeout=120000) as response:
        page.get_by_role('button',name='View Timetable').click()
    data=response.value.json()
    assert response.value.status==200 and data['source']=='yahoo' and data['availability']=='SUPPORTED'
    page.get_by_test_id('departure-card').first.wait_for()
    page.get_by_test_id('departure-card').first.click()
    print('CENTRAL_FALLBACK',len(data[data['selected_calendar']]),data['source'])
