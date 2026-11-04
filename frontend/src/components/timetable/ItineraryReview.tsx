import { ArrowRight, Check, ExternalLink } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { DepartureInfo, Route } from '../../api/types';
import { exactTimes, displayDateTime } from '../../utils/chronology';
import { StationName, PlatformInfo, SourceBadge } from '../railway/TrainInfo';
import { TrainSilhouette } from '../railway/TrainSilhouette';

/** Presentation of already selected departures. Selection and saving stay in the wizard. */
export function ItineraryReview({ route, selected }: { route: Route; selected: Record<number, DepartureInfo> }) {
  return <section className="rail-review" aria-label="Selected itinerary">
    <div className="rail-review-heading"><span className="rail-review-check"><Check size={18} /></span><div><h4>선택한 일정</h4><p>Your trains, ready for the journey.</p></div></div>
    <ol>{route.passenger_legs.filter(leg => selected[leg.index]).map(leg => {
      const departure = selected[leg.index];
      const times = exactTimes(departure, route.search_date);
      return <li key={leg.index}>
        <div className="rail-review-service"><TrainSilhouette size={19} /><strong>{departure.train_name}</strong>{departure.train_number && <span>{departure.train_number}</span>}</div>
        <div className="rail-review-route"><div><strong>{departure.time}</strong><StationName station={leg.departure_station} /><small>{displayDateTime(times.departure)}</small></div><ArrowRight size={20} aria-hidden="true" /><div><strong>{departure.arrival_time || 'Arrival unconfirmed'}</strong><StationName station={leg.arrival_station} /><small>{displayDateTime(times.arrival)}</small></div></div>
        <div className="rail-review-platforms"><PlatformInfo label="Departure platform" value={departure.platform} status={departure.platform_status} source={departure.source} /><PlatformInfo label="Arrival platform" value={departure.arrival_platform} status={departure.arrival_platform_status} source={departure.source} /><SourceBadge source={departure.source} /></div>
      </li>;
    })}</ol>
    <p className="rail-review-note">선택 열차 운임은 확인되지 않은 경우 미확정으로 표시됩니다.</p>
  </section>;
}

export function SavedItinerary({ notionUrl }: { notionUrl?: string | null }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => { ref.current?.focus({ preventScroll: true }); }, []);
  return <section ref={ref} tabIndex={-1} className="rail-saved rail-ui" aria-label="Saved itinerary">
    <span className="rail-saved-mark" aria-hidden="true"><Check size={26} /></span>
    <div role="status"><span className="rail-eyebrow">JOURNEY SAVED</span><h3>Notion에 저장되었습니다.</h3><p>Your selected journey is ready to revisit.</p></div>
    {notionUrl && <a className="rail-notion-link" href={notionUrl} target="_blank" rel="noreferrer">Open Notion <ExternalLink size={15} aria-hidden="true" /></a>}
  </section>;
}
