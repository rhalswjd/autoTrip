import { Skeleton, Card } from '../ui';
import './Timetable.css';

export function TimetableLoading() {
  return (
    <div className="timetable-loading-items">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i} className="timetable-loading-card">
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <Skeleton variant="text" style={{ width: '60px', height: '24px' }} />
            <Skeleton variant="text" style={{ width: '100px' }} />
          </div>
          <Skeleton variant="text" style={{ width: '70px', borderRadius: '9999px' }} />
        </Card>
      ))}
    </div>
  );
}
