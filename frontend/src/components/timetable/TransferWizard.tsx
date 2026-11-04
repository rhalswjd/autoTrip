import { useEffect, useRef, useState } from 'react';
import { stationDisplayName } from '../../utils/stationDisplay';
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
import '../../styles/railway.css';
import { ItineraryReview, SavedItinerary } from './ItineraryReview';
import { JourneyProgress } from './JourneyProgress';
import { SelectedDepartureSummary, SourceBadge, StationName, ThroughBoundary } from '../railway/TrainInfo';

export interface TransferWizardProps {
  route: Route;
  requestedLeg?: { index: number; requestId: number };
  onItineraryChange?: (route: Route) => void;
}

export function TransferWizard({ route, onItineraryChange, requestedLeg }: TransferWizardProps) {
  const legs = route.passenger_legs || [];
  const [currentStep, setCurrentStep] = useState(0);
  const [clearedLegs, setClearedLegs] = useState<number[]>([]);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const reviewRef = useRef<HTMLButtonElement>(null);
  const summaryRef = useRef<HTMLHeadingElement>(null);
  const focusRequested = useRef<'leg' | 'review' | 'summary' | null>(null);
  const focusStep = useRef(0);
  const navigate = (index: number, open = false) => {
    focusStep.current = index;
    focusRequested.current = index === legs.length ? 'summary' : 'leg';
    setCurrentStep(index);
    setOpened(open);
  };
  const [selectedLegs, setSelectedLegs] = useState<Record<number, DepartureInfo>>({});
  const [selectedSeats, setSelectedSeats] = useState<Record<number, SeatPreference>>({});
  const [opened, setOpened] = useState(false);
  const openTimetable = () => { focusStep.current = currentStep; focusRequested.current = 'leg'; setOpened(true); };
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
    setClearedLegs([]);
    reset();
  }, [route.id, reset]);

  useEffect(() => {
    onItineraryChange?.(Object.keys(selectedLegs).length ? itineraryPreview(route, selectedLegs) : route);
  }, [route, selectedLegs, onItineraryChange]);

  useEffect(() => {
    if (requestedLeg) {
      focusStep.current = requestedLeg.index;
      focusRequested.current = 'leg';
      setCurrentStep(requestedLeg.index);
      setOpened(true);
    }
  }, [requestedLeg]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      if (!focusRequested.current || focusStep.current !== currentStep) return;
      const target = focusRequested.current === 'review' ? reviewRef.current
        : focusRequested.current === 'summary' ? summaryRef.current : headingRef.current;
      target?.focus({ preventScroll: true });
      target?.scrollIntoView({ block: 'nearest', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
      focusRequested.current = null;
    });
    return () => cancelAnimationFrame(frame);
  }, [currentStep, opened, requestedLeg]);

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
    setClearedLegs(Object.keys(selectedLegs).map(Number).filter(index => index > currentStep));
    setSelectedLegs(previous => selectExactDeparture(previous,currentStep,departure));
    if (departure.arrival_time && currentStep < legs.length - 1) navigate(currentStep + 1, true);
    else { focusStep.current = currentStep; focusRequested.current = 'review'; setOpened(false); }
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
  if (isSuccess) return <SavedItinerary notionUrl={data?.notion_url} />;

  return <section className="timetable-container rail-wizard rail-ui" aria-label="Passenger timetable">
    <header className="rail-section-heading"><div><span className="rail-eyebrow">BUILD YOUR JOURNEY</span>
      <h3 ref={summaryRef} tabIndex={-1}>{isSummary ? '선택 일정 확인' : 'Choose your trains'}</h3></div>
      <span>{Object.keys(selectedLegs).length} / {legs.filter(item => item.segment_type !== 'walk').length} rides selected</span></header>
    <JourneyProgress legs={legs} currentStep={currentStep} selected={selectedLegs} cleared={clearedLegs} onNavigate={navigate} />
    {clearedLegs.length > 0 && <p role="status" className="rail-info-message" key={clearedLegs.join(',')}>
      Your later train selections were cleared because the connection time changed.
      <button type="button" className="rail-text-button" onClick={() => setClearedLegs([])} aria-label="Dismiss connection update">Dismiss</button>
    </p>}
    {!isSummary && leg && <div className="rail-current-leg" key={leg.index}>
      <header className="rail-station-sign">
        <span className="rail-eyebrow">{isWalk ? 'WALKING CONNECTION' : `LEG ${leg.index + 1} · ${queryDate || 'Travel date'}`}</span>
        <h4 ref={headingRef} tabIndex={-1} data-testid="passenger-leg-heading"><StationName station={leg.departure_station} /><span aria-hidden="true">→</span><StationName station={leg.arrival_station} /></h4>
        <p>{leg.railway_names.join(' / ')}</p>
      </header>
      <ThroughBoundary leg={leg} />
      {previousArrival !== undefined && <div className="rail-connection-context">
        <span>Previous train arrives{previousRide ? ` at ${stationDisplayName(previousRide.arrival_station)}` : ''}<strong>{displayDateTime(previousArrival)}</strong></span>
        <span>Available departures from<strong>{displayDateTime(previousArrival + walkMinutes * 60000)}</strong></span>
        <small>Check that you have enough time to change platforms{walkMinutes > 0 ? ' and complete the walk' : ''}.</small>
      </div>}
      {isWalk ? <p className="rail-state">Walking connection · {leg.duration || 'Duration not provided'}</p> : <>
        {selected && !opened && <SelectedDepartureSummary departure={selected} onChange={openTimetable} />}
        {!opened && !selected && <div className="rail-timetable-prompt"><p>Choose an exact departure for this ride.</p><Button onClick={openTimetable}>View timetable</Button></div>}
        {opened && query.isPending && <TimetableLoading />}
        {opened && query.isError && <div role="alert" className="rail-state is-error">
          <strong>Could not retrieve timetable information.</strong><p>Try again, or explore another leg while this source is unavailable.</p>
          <Button variant="secondary" loading={query.isFetching} onClick={() => query.refetch()}>Retry</Button>
        </div>}
        {opened && timetable && !query.isError && <>
          <div className="rail-timetable-meta"><SourceBadge source={timetable.source} /><span>{queryDate} · {selectedTimetableBucket(timetable).label}</span>{query.isFetching && !query.isFetchingNextPage && <span role="status">Updating departures…</span>}</div>
          {timetable.status !== 'available' && <div role="status" className={`rail-state ${timetable.status === 'provider_error' ? 'is-error' : ''}`} data-availability={timetable.availability}>
            <strong>{timetable.status === 'unsupported' ? 'Detailed timetable unavailable for this segment.' : 'Could not retrieve timetable information.'}</strong>
            <p>You can still view the other legs of your journey.</p>
            {timetable.status === 'provider_error' && <Button variant="secondary" loading={query.isFetching} onClick={() => query.refetch()}>Retry</Button>}
          </div>}
          {!unavailable && <div className="rail-departures" aria-label="Available departures" aria-busy={query.isFetching}>
            {available.map(departure => <TimetableCard key={departure.id} departure={departure} leg={leg}
              isSelected={selected?.id === departure.id} onClick={selectDeparture} />)}
          </div>}
          {!unavailable && available.length === 0 && <p role="status" className="rail-state">{query.hasNextPage ? 'No matching departures on this page. Load more trains to continue.' : previousArrival !== undefined ? 'No compatible departures after the previous connection.' : 'No departures found for this date and journey.'}</p>}
          {query.hasNextPage && !unavailable && <Button variant="secondary" loading={query.isFetchingNextPage} onClick={() => query.fetchNextPage()}>Show more departures</Button>}
        </>}
        {leg.has_seat_selection && <label className="rail-seat-preference">Seat preference <select aria-label="Seat preference"
          value={selectedSeats[currentStep] || SeatPreference.RESERVED}
          onChange={event => setSelectedSeats(previous => ({ ...previous, [currentStep]: event.target.value as SeatPreference }))}>
          <option value={SeatPreference.RESERVED}>Reserved</option>
          <option value={SeatPreference.NON_RESERVED}>Non-Reserved</option>
          <option value={SeatPreference.GREEN}>Green</option>
        </select></label>}
      </>}
    </div>}
    {isSummary && Object.keys(selectedLegs).length > 0 && <ItineraryReview route={route} selected={selectedLegs} />}
    {isSummary && <section className="rail-notion-action" aria-label="Save journey to Notion">
      <div><span className="rail-eyebrow">KEEP YOUR JOURNEY</span><h4>Save to Notion</h4><p>선택한 열차와 플랫폼 정보를 함께 저장합니다.</p></div>
      <div className="rail-notion-fields">
        <Input id={`notion-page-url-${route.id}`} label="Notion page URL (optional)" placeholder="https://www.notion.so/…" type="url" value={notionUrl} onChange={event => { setNotionUrl(event.target.value); setFormError(''); }} />
        {(formError || saveError) && <p role="alert" className="rail-save-error">{formError || 'Could not save your journey. Please try again.'}</p>}
        <Button disabled={!ready} loading={isPending} onClick={submit}>Add to Notion</Button>
      </div>
    </section>}
    <div className="rail-wizard-actions">
      {currentStep > 0 && <Button variant="secondary" onClick={() => navigate(currentStep - 1)}>이전 구간</Button>}
      {!isSummary && <Button ref={reviewRef} disabled={!isWalk && !unavailable && !selected?.arrival_time} onClick={() => navigate(currentStep + 1)}>
        {currentStep === legs.length - 1 ? '일정 확인' : '다음 구간'}
      </Button>}
    </div>
  </section>;
}
