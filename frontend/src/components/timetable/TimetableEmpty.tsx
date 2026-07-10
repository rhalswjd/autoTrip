import { Clock } from 'lucide-react';
import './Timetable.css';

export function TimetableEmpty() {
  return (
    <div className="timetable-empty-state">
      <Clock className="timetable-empty-icon" />
      <div>
        <div className="timetable-empty-title">No Departures Found</div>
        <div className="timetable-empty-desc">
          There are no scheduled trains for this route at the moment.
        </div>
      </div>
    </div>
  );
}
