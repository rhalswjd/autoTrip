import { Check, Footprints } from 'lucide-react';
import type { DepartureInfo, PassengerLeg } from '../../api/types';
import { stationDisplayName } from '../../utils/stationDisplay';
import { SelectedDepartureSummary } from '../railway/TrainInfo';

interface JourneyProgressProps {
  legs: PassengerLeg[];
  currentStep: number;
  selected: Record<number, DepartureInfo>;
  cleared: number[];
  onNavigate: (index: number, open: boolean) => void;
}

export function JourneyProgress({ legs, currentStep, selected, cleared, onNavigate }: JourneyProgressProps) {
  return <nav aria-label="Passenger legs" className="rail-progress"><ol>
    {legs.map(leg => <li key={leg.index} className={`${currentStep === leg.index ? 'is-current' : ''} ${selected[leg.index] ? 'is-complete' : ''} ${cleared.includes(leg.index) ? 'was-cleared' : ''}`}>
      <button type="button" aria-current={currentStep === leg.index ? 'step' : undefined} onClick={() => onNavigate(leg.index, false)}>
        <span className="rail-step-number">{selected[leg.index] ? <Check size={15} aria-label="Completed" /> : leg.segment_type === 'walk' ? <Footprints size={15} aria-label="Walk" /> : leg.index + 1}</span>
        <span>{stationDisplayName(leg.departure_station)}<span className="rail-progress-arrow"> → </span>{stationDisplayName(leg.arrival_station)}</span>
        <small>{currentStep === leg.index ? 'Current' : selected[leg.index] ? 'Selected' : leg.segment_type === 'walk' ? 'Walk' : 'Choose train'}</small>
      </button>
      {selected[leg.index] && currentStep !== leg.index && <SelectedDepartureSummary departure={selected[leg.index]} onChange={() => onNavigate(leg.index, true)} />}
    </li>)}
  </ol></nav>;
}
