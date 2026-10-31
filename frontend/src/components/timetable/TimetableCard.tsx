import type { DepartureInfo } from '../../api/types';
import { Card, Badge } from '../ui';
import './Timetable.css';

export interface TimetableCardProps {
  departure: DepartureInfo;
  platform?: string | null;
  fare?: number | null;
  isSelected?: boolean;
  onClick: (departure: DepartureInfo) => void;
}

export function TimetableCard({ departure, platform, fare, isSelected, onClick }: TimetableCardProps) {
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
      data-testid="departure-card"
    >
      <div className="timetable-time-info">
        <span className="timetable-time">{departure.time}</span>
        <span className="timetable-time">→ {departure.arrival_time || '도착시각 미확인'}</span>
        <span className="timetable-train-name">{departure.train_name}</span>
        {departure.train_number && <small>열차번호 {departure.train_number}</small>}
        {departure.direction && <span>{departure.direction} 방면</span>}
      </div>
      <div className="timetable-status" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
        <Badge variant="success">{departure.source === 'jr_odekake' ? 'JR 공식' : '시간표'}</Badge>
        <span>출발 플랫폼 {departure.platform || platform || 'UNKNOWN'}</span>
        <span>도착 플랫폼 {departure.arrival_platform || 'UNKNOWN'}</span>
        {departure.source_url && <a href={departure.source_url} target="_blank" rel="noreferrer" onClick={event => event.stopPropagation()}>원문 시간표</a>}
        {fare !== undefined && fare !== null && <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>¥{fare.toLocaleString()}</span>}
      </div>
    </Card>
  );
}
