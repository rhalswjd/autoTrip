import type { DepartureInfo } from '../../api/types';
import { Card, Badge } from '../ui';
import './Timetable.css';

export interface TimetableCardProps {
  departure: DepartureInfo;
  isSelected?: boolean;
  onClick: (departure: DepartureInfo) => void;
}

export function TimetableCard({ departure, isSelected, onClick }: TimetableCardProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(departure);
    }
  };

  return (
    <Card
      className="timetable-card"
      hoverable
      clickable
      selected={isSelected}
      onClick={() => onClick(departure)}
      onKeyDown={handleKeyDown}
      aria-selected={isSelected}
    >
      <div className="timetable-time-info">
        <span className="timetable-time">{departure.time}</span>
        <span className="timetable-train-name">{departure.train_name}</span>
      </div>
      <div className="timetable-status">
        <Badge variant="success">Available</Badge>
      </div>
    </Card>
  );
}
