import { Skeleton, Card } from '../ui';
import './RouteTimeline.css';

export function RouteLoading() {
  return (
    <div className="route-loading-items">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i} className="route-loading-card">
          <div className="route-loading-row">
            <Skeleton variant="text" style={{ width: '30%' }} />
            <Skeleton variant="text" style={{ width: '60px' }} />
          </div>
          <div className="route-loading-row">
            <Skeleton variant="text" style={{ width: '50%' }} />
            <Skeleton variant="text" style={{ width: '80px' }} />
          </div>
        </Card>
      ))}
    </div>
  );
}
