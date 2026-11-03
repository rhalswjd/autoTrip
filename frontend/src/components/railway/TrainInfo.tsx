import type { DepartureInfo, PassengerLeg, PlatformStatus, Station } from '../../api/types';
import { stationDisplayName } from '../../utils/stationDisplay';
import { platformLabel } from '../../utils/platform';
import { ArrowDown, Check } from 'lucide-react';
import '../../styles/railway.css';

export function StationName({ station }: { station: Station }) {
  const name = stationDisplayName(station);
  return <span className="rail-station-name"><span>{name}</span>{station.name_jp && station.name_jp !== name && <small lang="ja">{station.name_jp}</small>}</span>;
}

export function SourceBadge({ source }: { source: string }) {
  return <span className={`rail-source ${source === 'jr_odekake' ? 'is-official' : ''}`}>
    {source === 'jr_odekake' ? 'JR Odekake · Official' : source === 'yahoo' ? 'Yahoo · Timetable' : source ? 'Other timetable source' : 'Source not provided'}
  </span>;
}

export function PlatformInfo({ value, status, source, label }: { value?: string | null; status?: PlatformStatus; source: string; label: string }) {
  return <span className="rail-platform"><span>{label}</span><strong>{platformLabel(value, status, source)}</strong></span>;
}

export function ThroughBoundary({ leg }: { leg: PassengerLeg }) {
  if (!leg.through_boundaries.length) return null;
  return <div className="rail-through"><ArrowDown size={14} aria-hidden="true" /><span><strong>Remain onboard</strong> · {leg.through_boundaries.map(stationDisplayName).join(', ')}
    <small>{leg.railway_names.join(' → ')}</small></span></div>;
}

export function SelectedDepartureSummary({ departure, onChange }: { departure: DepartureInfo; onChange: () => void }) {
  return <div className="rail-selected-summary">
    <div><span className="rail-complete"><Check size={14} aria-hidden="true" />Selected</span><strong className="rail-summary-time">{departure.time} → {departure.arrival_time || 'Arrival unconfirmed'}</strong>
      <span>{departure.train_name}{departure.train_number ? ` · ${departure.train_number}` : ''}</span>
      <small>{departure.operating_date || departure.departure_datetime?.slice(0, 10)}
        {departure.arrival_datetime && departure.arrival_datetime.slice(0, 10) !== (departure.operating_date || departure.departure_datetime?.slice(0, 10)) && ` · Arrives ${departure.arrival_datetime.slice(0, 10)}`}</small></div>
    <div className="rail-summary-platforms"><PlatformInfo label="Departure platform" value={departure.platform} status={departure.platform_status} source={departure.source} />
      <PlatformInfo label="Arrival platform" value={departure.arrival_platform} status={departure.arrival_platform_status} source={departure.source} /><SourceBadge source={departure.source} /></div>
    <button type="button" className="rail-text-button" onClick={onChange}>Change</button>
  </div>;
}
