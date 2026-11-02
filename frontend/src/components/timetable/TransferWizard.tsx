import { useEffect, useState } from 'react';
import { stationDisplayName } from '../../utils/stationDisplay';
import { platformLabel } from '../../utils/platform';
import type { Route, DepartureInfo } from '../../api/types';
import { SeatPreference } from '../../api/types';
import { useMovement } from '../../hooks';
import { usePassengerTimetable } from '../../hooks/useTimetable';
import { Button, Input } from '../ui';
import { TimetableCard } from './TimetableCard';
import { TimetableLoading } from './TimetableLoading';
import { selectedTimetableBucket } from '../../utils/timetable';
import { itineraryPreview, selectedPassengerLegs } from '../../utils/itinerary';
import { exactTimes, compatibleDeparture, chronologicalJourney, selectExactDeparture, walkDuration, jstDate, displayDateTime } from '../../utils/chronology';
import './Timetable.css';

export interface TransferWizardProps {
  route: Route;
  onItineraryChange?: (route: Route) => void;
}

export function TransferWizard({ route, onItineraryChange }: TransferWizardProps) {
  const legs = route.passenger_legs || [];
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedLegs, setSelectedLegs] = useState<Record<number, DepartureInfo>>({});
  const [selectedSeats, setSelectedSeats] = useState<Record<number, SeatPreference>>({});
  const [opened, setOpened] = useState(false);
  const [continuedDate, setContinuedDate] = useState('');
  const [notionUrl, setNotionUrl] = useState('');
  const [formError, setFormError] = useState('');
  const { mutate, isPending, isSuccess, data, error: saveError, reset } = useMovement();
  const leg = legs[currentStep];
  const isWalk = leg?.segment_type === 'walk';
  const isSummary = currentStep === legs.length;
  const previousRide = [...legs.slice(0, currentStep)].reverse().find(item => item.segment_type !== 'walk');
  const previousExact = previousRide ? selectedLegs[previousRide.index] : undefined;
  const previousArrival = previousExact ? exactTimes(previousExact,route.search_date).arrival : undefined;
  const walkMinutes = legs.slice(previousRide ? previousRide.index + 1 : 0,currentStep)
    .filter(item => item.segment_type === 'walk').reduce((sum,item) => sum + walkDuration(item),0);
  const baseDate = previousArrival !== undefined && Number.isFinite(previousArrival) ? jstDate(previousArrival + walkMinutes * 60000) : route.search_date;
  const queryDate = continuedDate || baseDate;
  const boundary = previousArrival !== undefined && Number.isFinite(previousArrival) ? new Date(previousArrival + walkMinutes * 60000).toISOString() : undefined;
  const query = usePassengerTimetable(route.id, currentStep, queryDate, Boolean(leg && !isWalk && opened), boundary);
  useEffect(() => setContinuedDate(''), [route.id,currentStep,previousArrival]);

  useEffect(() => {
    setCurrentStep(0);
    setSelectedLegs({});
    setSelectedSeats({});
    setOpened(false);
    setFormError('');
    reset();
  }, [route.id, reset]);

  useEffect(() => {
    onItineraryChange?.(Object.keys(selectedLegs).length ? itineraryPreview(route, selectedLegs) : route);
  }, [route, selectedLegs, onItineraryChange]);

  const timetable = query.data?.pages[0];
  const unavailable = timetable?.status === 'unsupported' || timetable?.status === 'provider_error' || query.isError;
  const departures = query.data?.pages.flatMap(page => selectedTimetableBucket(page).departures) || [];
  const unique = [...new Map(departures.map(item => [item.id, item])).values()];
  const available = unique.filter(item => compatibleDeparture(item,previousArrival,walkMinutes,queryDate))
    .sort((a,b) => exactTimes(a,queryDate).departure - exactTimes(b,queryDate).departure);
  const selected = selectedLegs[currentStep];
  const ready = chronologicalJourney(route,selectedLegs);
  useEffect(() => {
    if (opened && previousArrival !== undefined && query.isSuccess && !query.isFetching && !query.hasNextPage
        && !unavailable && available.length === 0 && !continuedDate && baseDate) {
      setContinuedDate(jstDate(Date.parse(`${baseDate}T00:00:00+09:00`) + 86400000));
    }
  }, [opened,previousArrival,query.isSuccess,query.isFetching,query.hasNextPage,unavailable,available.length,continuedDate,baseDate]);

  const selectDeparture = (departure: DepartureInfo) => {
    if (!compatibleDeparture(departure,previousArrival,walkMinutes,queryDate)) return;
    // Changing an earlier train invalidates every later selection.
    setSelectedLegs(previous => selectExactDeparture(previous,currentStep,departure));
  };

  const submit = () => {
    if (!ready) return;
    if (notionUrl) {
      try {
        const url = new URL(notionUrl);
        if (!['notion.so', 'www.notion.so', 'notion.site', 'app.notion.com'].includes(url.hostname) && !url.hostname.endsWith('.notion.site')) throw new Error();
      } catch {
        setFormError('올바른 Notion 페이지 링크를 입력해 주세요.');
        return;
      }
    }
    const selections = selectedPassengerLegs(route, selectedLegs).map(item => ({
      ...item, selected_seat: legs[item.passenger_leg_index!].has_seat_selection
        ? selectedSeats[item.passenger_leg_index!] || SeatPreference.RESERVED : SeatPreference.NOT_APPLICABLE,
    }));
    mutate({
      route_id: route.id, departure_station: route.departure_station, arrival_station: route.arrival_station,
      selected_departure_time: selections[0].departure_time,
      selected_arrival_time: selections.at(-1)!.arrival_time!,
      search_date: route.search_date, search_time: route.search_time,
      notion_page_url: notionUrl || undefined, legs: selections,
    });
  };

  if (!legs.length) return <div role="alert">경로의 탑승 구간 정보가 없습니다. 경로를 다시 검색해 주세요.</div>;
  if (isSuccess) return <section aria-label="Saved itinerary"><p>Notion에 저장되었습니다.</p>
    {data?.notion_url && <a href={data.notion_url} target="_blank" rel="noreferrer">Open Notion</a>}</section>;

  return <section className="timetable-container" aria-label="Passenger timetable">
    <h3>{isSummary ? '선택 일정 확인' : '구간별 시간표'}</h3>
    <p>{route.search_date} · {legs.filter(item => item.segment_type !== 'walk').length}개 탑승 구간</p>
    <nav aria-label="Passenger legs" className="passenger-leg-nav">
      {legs.map(item => <button key={item.index} type="button" aria-current={currentStep === item.index ? 'step' : undefined}
        onClick={() => { setCurrentStep(item.index); setOpened(false); }}>
        {item.index + 1}. {stationDisplayName(item.departure_station)} → {stationDisplayName(item.arrival_station)}
        {item.segment_type === 'bus' ? ' · Bus' : item.segment_type === 'walk' ? ' · Walk' : ''}
      </button>)}
    </nav>
    {!isSummary && leg && <>
      <h4 data-testid="passenger-leg-heading">{stationDisplayName(leg.departure_station)} → {stationDisplayName(leg.arrival_station)}</h4>
      <p>{leg.railway_names.join(' / ')}</p>
      {leg.through_boundaries.length > 0 && <p>Remain on board: {leg.through_boundaries.map(stationDisplayName).join(', ')}</p>}
      {isWalk ? <p>도보 이동 · {leg.duration || '시간 미확인'}</p> : <>
        {!opened && <Button onClick={() => setOpened(true)}>View Timetable</Button>}
        {opened && query.isPending && <TimetableLoading />}
        {opened && query.isError && <div role="alert">
          <p>시간표 조회 실패: {query.error.message}</p>
          <Button variant="secondary" onClick={() => query.refetch()}>다시 조회</Button>
        </div>}
        {opened && timetable && !query.isError && <>
          <p>{timetable.source === 'jr_odekake' ? 'JR 오데카케 공식 시간표' : 'Yahoo 시간표'} · {queryDate} · {selectedTimetableBucket(timetable).label}</p>
          {timetable.status !== 'available' && <p role="status" data-availability={timetable.availability}>
            {timetable.status === 'unsupported' ? 'Detailed timetable unavailable — ' : 'Provider error — '}
            {timetable.message || '이 구간의 시간표 공급자가 지원되지 않습니다.'}</p>}
          {timetable.status === 'provider_error' && <Button variant="secondary" onClick={() => query.refetch()}>다시 조회</Button>}
          {previousArrival !== undefined && <p>이전 구간 도착 {displayDateTime(previousArrival)} 이후의 출발편 · 환승 여유시간을 확인해 주세요.</p>}
          <div role="listbox" aria-label="Available departures">
            {available.map(departure => <TimetableCard key={departure.id} departure={departure}
              isSelected={selected?.id === departure.id} onClick={selectDeparture} />)}
          </div>
          {!unavailable && available.length === 0 && <p role="status">{query.hasNextPage ? '이 페이지에는 목적지에 정차하는 출발편이 없습니다. 다음 출발편을 조회할 수 있습니다.' : '선택한 날짜와 구간에 맞는 출발편을 찾지 못했습니다.'}</p>}
          {query.hasNextPage && <Button variant="secondary" loading={query.isFetchingNextPage} onClick={() => query.fetchNextPage()}>다음 출발편 더 보기</Button>}
        </>}
        {leg.has_seat_selection && <label>Seat preference <select aria-label="Seat preference"
          value={selectedSeats[currentStep] || SeatPreference.RESERVED}
          onChange={event => setSelectedSeats(previous => ({ ...previous, [currentStep]: event.target.value as SeatPreference }))}>
          <option value={SeatPreference.RESERVED}>Reserved</option>
          <option value={SeatPreference.NON_RESERVED}>Non-Reserved</option>
          <option value={SeatPreference.GREEN}>Green</option>
        </select></label>}
      </>}
    </>}
    {Object.keys(selectedLegs).length > 0 && <section aria-label="Selected itinerary">
      <h4>선택한 일정</h4>
      {legs.filter(item => selectedLegs[item.index]).map(item => {
        const departure = selectedLegs[item.index];
        return <div key={item.index}>
          <p>{stationDisplayName(item.departure_station)} → {stationDisplayName(item.arrival_station)}: {departure.time} → {departure.arrival_time}</p>
          <small>{displayDateTime(exactTimes(departure,route.search_date).departure)} → {displayDateTime(exactTimes(departure,route.search_date).arrival)}</small>
          <p>{departure.train_name} · 출발 플랫폼 {platformLabel(departure.platform, departure.platform_status, departure.source)} · 도착 플랫폼 {platformLabel(departure.arrival_platform, departure.arrival_platform_status, departure.source)}</p>
        </div>;
      })}
      <p>선택 열차 운임은 확인되지 않은 경우 미확정으로 표시됩니다.</p>
    </section>}
    {isSummary && <>
      <Input label="Notion page URL (optional)" value={notionUrl} onChange={event => setNotionUrl(event.target.value)} />
      {(formError || saveError) && <p role="alert">{formError || saveError?.message}</p>}
      <Button disabled={!ready} loading={isPending} onClick={submit}>Add to Notion</Button>
    </>}
    <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
      {currentStep > 0 && <Button variant="secondary" onClick={() => { setCurrentStep(step => step - 1); setOpened(false); }}>이전 구간</Button>}
      {!isSummary && <Button disabled={!isWalk && !unavailable && !selected?.arrival_time} onClick={() => { setCurrentStep(step => step + 1); setOpened(false); }}>
        {currentStep === legs.length - 1 ? '일정 확인' : '다음 구간'}
      </Button>}
    </div>
  </section>;
}
