import { BusFront, Footprints, TrainFront } from 'lucide-react';
import type { Route } from '../../../api/types';
import { StationName, ThroughBoundary } from '../../railway/TrainInfo';
import '../../../styles/railway.css';

export interface RouteTimelineV2Props { route: Route; onViewTimetable?: (index: number) => void }

export function RouteTimelineV2({ route, onViewTimetable }: RouteTimelineV2Props) {
  return <section className="rail-timeline" aria-label="Route timeline">
    <div className="rail-section-heading"><h3>Route overview</h3><span>Search schedule · choose exact trains below</span></div>
    <ol>{route.passenger_legs.map((leg, index) => <li key={leg.index} className={leg.segment_type === 'walk' ? 'is-walk' : ''}>
      {index > 0 && leg.segment_type !== 'walk' && route.passenger_legs[index - 1].segment_type !== 'walk' && <div className="rail-transfer">Transfer · change {leg.segment_type === 'bus' ? 'to bus' : 'train'}</div>}
      <div className="rail-leg-stations"><span className="rail-leg-clock">{leg.departure_time || '—'}</span><StationName station={leg.departure_station} /></div>
      <div className="rail-leg-service">
        {leg.segment_type === 'walk' ? <Footprints size={17} aria-hidden="true" /> : leg.segment_type === 'bus' ? <BusFront size={17} aria-hidden="true" /> : <TrainFront size={17} aria-hidden="true" />}
        <div><strong>{leg.segment_type === 'walk' ? 'Walk' : leg.railway_names.join(' / ')}</strong>{leg.duration && <small>{leg.duration}{leg.segment_type === 'walk' ? ' · search estimate' : ''}</small>}</div>
        {leg.segment_type !== 'walk' && onViewTimetable && <button type="button" className="rail-text-button" onClick={() => onViewTimetable(leg.index)}>View timetable →</button>}
      </div>
      <ThroughBoundary leg={leg} />
      <div className="rail-leg-stations"><span className="rail-leg-clock">{leg.arrival_time || '—'}</span><StationName station={leg.arrival_station} /></div>
    </li>)}</ol>
  </section>;
}
