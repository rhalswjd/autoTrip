import { useEffect, useState } from 'react';
import type { Route, DepartureInfo } from '../../api/types';
import { useTimetable } from '../../hooks';
import { useToast } from '../../hooks';
import { TimetableCard } from './TimetableCard';
import { TimetableLoading } from './TimetableLoading';
import { TimetableEmpty } from './TimetableEmpty';
import { MovementDialog } from './MovementDialog';
import './Timetable.css';

export interface TimetableListProps {
  route: Route;
}

export function TimetableList({ route }: TimetableListProps) {
  const { data: timetable, isLoading, isError, error } = useTimetable(route.id);
  const { error: toastError } = useToast();
  
  const [selectedDeparture, setSelectedDeparture] = useState<DepartureInfo | null>(null);

  useEffect(() => {
    if (isError && error) {
      toastError('Timetable Error', error.message || 'Failed to load timetable.');
    }
  }, [isError, error, toastError]);

  const handleDepartureSelect = (departure: DepartureInfo) => {
    setSelectedDeparture(departure);
  };

  const closeDialog = () => {
    setSelectedDeparture(null);
  };

  if (isLoading) {
    return (
      <div className="timetable-container">
        <h3 className="timetable-title" style={{ marginBottom: '16px' }}>Timetable</h3>
        <TimetableLoading />
      </div>
    );
  }

  if (timetable?.departures.length === 0) {
    return (
      <div className="timetable-container">
        <h3 className="timetable-title" style={{ marginBottom: '16px' }}>Timetable</h3>
        <TimetableEmpty />
      </div>
    );
  }

  return (
    <div className="timetable-container">
      <div className="timetable-header">
        <h3 className="timetable-title">Timetable</h3>
        <span className="timetable-meta">
          {timetable?.departures.length} departures
        </span>
      </div>
      
      <div className="timetable-list" role="listbox" aria-label="Available departures">
        {timetable?.departures.map((departure, idx) => (
          <TimetableCard
            key={`${departure.time}-${idx}`}
            departure={departure}
            isSelected={selectedDeparture?.time === departure.time}
            onClick={handleDepartureSelect}
          />
        ))}
      </div>

      {selectedDeparture && (
        <MovementDialog
          route={route}
          departure={selectedDeparture}
          isOpen={!!selectedDeparture}
          onClose={closeDialog}
        />
      )}
    </div>
  );
}
