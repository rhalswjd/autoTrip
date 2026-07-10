import { MapPin } from 'lucide-react';
import type { StationSearchResult } from '../../api/types';
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
    <div className={`route-station-field ${!station ? 'is-empty' : ''}`}>
      <MapPin className="route-station-icon" size={20} />
      <div className="route-station-content">
        <span className="route-station-label">{label}</span>
        <span className="route-station-name">
          {station ? station.english_name : 'Select from search'}
        </span>
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
