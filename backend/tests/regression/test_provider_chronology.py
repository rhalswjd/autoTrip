from unittest.mock import AsyncMock
import pytest
from domain.station import Station
from domain.timetable import Timetable, DepartureInfo
from infrastructure.adapters.transport_scraper import TransportScraperAdapter
from application.services.movement_service import MovementService
from application.services.timetable_service import exact_option_key
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from tests.factories import journey
from api.schemas import LegSelection
from domain.exceptions import DomainException


@pytest.mark.asyncio
async def test_jr_central_tokaido_record_uses_honest_yahoo_fallback_not_odekake():
    official, other = AsyncMock(), AsyncMock()
    other.get_timetable.return_value = Timetable(route_id='r')
    adapter = TransportScraperAdapter(AsyncMock(), official, other)
    result = await adapter.get_timetable('r', '柏原(滋賀県)', '米原', railway_name_jp='JR東海道本線',
        search_date='2026-11-03', station_context=(Station(id='1150309',name_jp='柏原(滋賀)',prefecture='25'), Station(name_jp='米原')))
    official.get_timetable.assert_not_awaited()
    assert result.source == 'yahoo' and result.availability == 'SUPPORTED'


@pytest.mark.asyncio
@pytest.mark.parametrize('service',['JR特急サンダーバード','JR特急こうのとり','JR大阪環状線外回り'])
async def test_verified_west_corridor_keeps_official_provider(service):
    official, other = AsyncMock(), AsyncMock()
    official.get_timetable.return_value = Timetable(route_id='r', source='jr_odekake', weekday=[
        DepartureInfo(id='published', time='06:34', arrival_time='07:54', train_name=service)])
    result = await TransportScraperAdapter(AsyncMock(), official, other).get_timetable('r','新大阪','敦賀',
        railway_name_jp=service,search_date='2026-11-03')
    assert result.source == 'jr_odekake'
    other.get_timetable.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(('previous_arrival','next_day','next_time','valid'), [
    ('07:57','2026-11-01','00:03',False),('07:57','2026-11-01','08:10',True),
    ('23:55','2026-11-02','00:10',True),('23:55','2026-11-01','23:40',False)])
async def test_server_revalidates_full_chronology_before_notion(previous_arrival,next_day,next_time,valid):
    route=journey(['A','B','C'],['JR線','Other']).model_copy(update={'search_date':'2026-11-01'})
    cache, notion=FakeCacheAdapter(),AsyncMock()
    await cache.set(route.id,route)
    exacts=[DepartureInfo(id='one',time='06:29',arrival_time=previous_arrival,operating_date='2026-11-01',train_name='One'),
            DepartureInfo(id='two',time=next_time,arrival_time='08:30' if next_time=='08:10' else '00:18',operating_date=next_day,train_name='Two')]
    selections=[]
    for i,e in enumerate(exacts):
        await cache.set(exact_option_key(route.id,i,e.id,e.operating_date),e)
        selections.append(LegSelection(segment_index=i,departure_station='untrusted',arrival_station='untrusted',departure_time=e.time,
            exact_departure_id=e.id,timetable_date=e.operating_date))
    call=MovementService(cache,notion).create_movement(route.id,'A','C',None,None,'06:29','00:18',legs=selections)
    if valid:
        await call
        notion.save_movement.assert_awaited_once()
    else:
        with pytest.raises(DomainException,match='chronolog'):
            await call
        notion.save_movement.assert_not_awaited()


def test_jr_midnight_is_proven_by_source_stop_order_not_a_four_am_cutoff():
    from infrastructure.scrapers.timetable.odekake_parser import JROdekakeParser
    html='<table><tbody class="time-details"><tr><td>A</td><td>23:56着 00:03発</td><td>2</td></tr><tr><td>B</td><td>00:18着</td><td>3</td></tr></tbody></table>'
    result=JROdekakeParser().parse_train(html,'A','B','2026-11-01')
    assert result['departure_datetime']=='2026-11-02T00:03:00+09:00'
    assert result['arrival_datetime']=='2026-11-02T00:18:00+09:00'


@pytest.mark.asyncio
async def test_unknown_jr_ownership_is_not_evidence_for_odekake():
    official,other=AsyncMock(),AsyncMock()
    other.get_timetable.return_value=Timetable(route_id='r')
    result=await TransportScraperAdapter(AsyncMock(),official,other).get_timetable('r','A','B',railway_name_jp='JR未登録線',search_date='2026-11-01')
    official.get_timetable.assert_not_awaited()
    assert result.source=='yahoo'


@pytest.mark.asyncio
async def test_continuation_date_and_boundary_reach_provider_without_reusing_previous_date():
    from application.services.timetable_service import TimetableService
    route=journey(['A','B'],['JR線']).model_copy(update={'search_date':'2026-11-01'})
    cache,provider=FakeCacheAdapter(),AsyncMock();await cache.set(route.id,route)
    provider.get_timetable.return_value=Timetable(route_id=route.id,weekday=[
        DepartureInfo(id='next',time='00:10',arrival_time='00:30',train_name='Train',operating_date='2026-11-02')])
    result=await TimetableService(provider,cache).get_leg_timetable(route.id,0,service_date='2026-11-02',not_before='2026-11-01T23:55:00+09:00')
    assert provider.get_timetable.await_args.kwargs['search_date']=='2026-11-02'
    assert provider.get_timetable.await_args.kwargs['not_before']=='2026-11-01T23:55:00+09:00'
    assert result.search_date=='2026-11-02' and result.weekday[0].departure_datetime=='2026-11-02T00:10:00+09:00'
    assert (await cache.get(route.id)).search_date=='2026-11-01'


@pytest.mark.asyncio
async def test_jr_cheap_boundary_prioritization_keeps_existing_detail_budget():
    from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
    from tests.regression.test_odekake_integration import STATION_PAGE, TRAIN_PAGE
    early=''.join(STATION_PAGE.replace('/100?',f'/{i}?').replace('06:34','05:00') for i in range(24))
    later=STATION_PAGE.replace('/100?','/later?').replace('06:34','08:00')
    downloader=AsyncMock();downloader.fetch_html.side_effect=[early+later,
        TRAIN_PAGE.replace('06:34','08:00').replace('06:33','07:59').replace('07:54','08:30')]+[TRAIN_PAGE]*23
    result=await JROdekakeTimetableScraper(downloader).get_timetable('r','新大阪','敦賀',timetable_id='tab',
        railway_name_jp='JR特急サンダーバード',search_date='2026-10-31',not_before='2026-10-31T07:57:00+09:00')
    assert result.saturday[0].time=='08:00'
    assert '/later?' in downloader.fetch_html.await_args_list[1].args[0]
    assert downloader.fetch_html.await_count==25
