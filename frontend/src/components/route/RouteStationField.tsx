import { MapPin } from 'lucide-react';
import type { StationSearchResult } from '../../api/types';
import { stationDisplayName } from '../../utils/stationDisplay';
import { IconButton } from '../ui';
import { X } from 'lucide-react';
import './Route.css';

export interface RouteStationFieldProps {
  label: string;
  station: StationSearchResult | null;
  onClear: () => void;
}

export function RouteStationField({ label, station, onClear }: RouteStationFieldProps) {
  return (
    <div className={`route-station-field ${!station ? 'is-empty' : ''}`} data-selected-station-id={station?.id}>
      <MapPin className="route-station-icon" size={20} />
      <div className="route-station-content">
        <span className="route-station-label">{label}</span>
        <span className="route-station-name">
          {station ? stationDisplayName(station) : 'Select from search'}
        </span>
        {station && <small>{station.japanese_name}{station.region ? ` · ${station.region}` : ''}</small>}
      </div>
      {station && (
        <IconButton
          size="sm"
          icon={<X />}
          onClick={onClear}
          aria-label={`Clear ${label}`}
        />
      )}
    </div>
  );
}
