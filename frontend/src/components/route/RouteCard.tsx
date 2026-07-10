import type { Route } from '../../api/types';
import { Card, Badge } from '../ui';
import './RouteTimeline.css';

export interface RouteCardProps {
  route: Route;
  isSelected: boolean;
  onClick: (route: Route) => void;
}

function formatFare(fare: number): string {
  return `¥${fare.toLocaleString()}`;
}

export function RouteCard({ route, isSelected, onClick }: RouteCardProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(route);
    }
  };

  return (
    <Card
      className="route-card"
      hoverable
      clickable
      selected={isSelected}
      onClick={() => onClick(route)}
      onKeyDown={handleKeyDown}
      aria-selected={isSelected}
    >
      <div className="route-card-header">
        <span className="route-card-duration">{route.total_duration}</span>
        <div className="route-card-meta">
          {route.transfer_count === 0 ? (
            <Badge variant="success">Direct</Badge>
          ) : (
            <Badge variant="default">
              {route.transfer_count} transfer{route.transfer_count > 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </div>
      <div className="route-card-footer">
        <span className="route-card-route-name">{route.railway_name}</span>
        <span className="route-card-fare">{formatFare(route.total_fare)}</span>
      </div>
    </Card>
  );
}
