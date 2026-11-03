import { ArrowRight, Check, ExternalLink } from 'lucide-react';
import type { DepartureInfo, PassengerLeg } from '../../api/types';
import { PlatformInfo, SourceBadge, StationName } from '../railway/TrainInfo';
import '../../styles/railway.css';

export interface TimetableCardProps {
  departure: DepartureInfo;
  platform?: string | null;
  fare?: number | null;
  leg?: PassengerLeg;
  isSelected?: boolean;
  onClick: (departure: DepartureInfo) => void;
}

export function TimetableCard({ departure, platform, fare, leg, isSelected, onClick }: TimetableCardProps) {
  const unavailable = !departure.arrival_time;
  return <article className={`rail-departure ${isSelected ? 'is-selected' : ''} ${unavailable ? 'is-unavailable' : ''}`}
    data-testid="departure-card" data-departure-datetime={departure.departure_datetime} data-arrival-datetime={departure.arrival_datetime}>
    <div className="rail-departure-times">
      <div><strong>{departure.time}</strong>{leg && <StationName station={leg.departure_station} />}</div>
      <ArrowRight size={18} aria-hidden="true" />
      <div><strong>{departure.arrival_time || 'Unconfirmed'}</strong>{leg && <StationName station={leg.arrival_station} />}</div>
    </div>
    <div className="rail-departure-action"><button type="button" aria-pressed={Boolean(isSelected)} disabled={unavailable}
      aria-label={`${isSelected ? 'Selected' : 'Select'} ${departure.time} ${departure.train_name}`}
      onClick={() => onClick(departure)}>{isSelected ? <><Check size={16} aria-hidden="true" />Selected</> : 'Select train'}</button></div>
    <div className="rail-departure-service"><strong>{departure.train_name}</strong>{departure.train_number && <small>No. {departure.train_number}</small>}
      <small>{departure.operating_date || departure.departure_datetime?.slice(0, 10)}</small>
      {departure.arrival_datetime && departure.departure_datetime?.slice(0, 10) !== departure.arrival_datetime.slice(0, 10) && <small>Arrives {departure.arrival_datetime.slice(0, 10)}</small>}
      {departure.direction && <small>For {departure.direction}</small>}</div>
    <div className="rail-departure-meta">
      <PlatformInfo label="Departure platform" value={departure.platform || platform} status={departure.platform_status} source={departure.source} />
      <PlatformInfo label="Arrival platform" value={departure.arrival_platform} status={departure.arrival_platform_status} source={departure.source} />
      <SourceBadge source={departure.source} />
      {departure.source_url && <a href={departure.source_url} target="_blank" rel="noreferrer">Source <ExternalLink size={12} aria-hidden="true" /></a>}
      {fare != null && <small>Estimated fare ¥{fare.toLocaleString()}</small>}
    </div>
    {unavailable && <p className="rail-unavailable-note">Arrival time is not confirmed. Choose a train with a confirmed arrival to continue.</p>}
  </article>;
}
