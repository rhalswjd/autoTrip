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
      data-testid="route-family-card"
      data-route-id={route.id}
    >
      <strong className="route-card-service">{route.passenger_legs?.filter(leg => leg.segment_type !== 'walk').map(leg => leg.railway_names.join(' / ')).join(' → ') || route.railway_name}</strong>
      <div className="route-card-context">{route.search_date} · {route.departure_time || '—'} → {route.arrival_time || '—'}</div>
      <div className="route-card-header">
        <span className="route-card-duration">{route.total_duration} <small>elapsed</small></span>
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
      {route.alternative_reason && <p className="route-card-reason">{route.alternative_reason}</p>}
      <div className="route-card-footer">
        <span className="route-card-route-name">{route.categories?.map(category => <Badge key={category} variant="default">{category.replaceAll('_', ' ')}</Badge>)}</span>
        <span className="route-card-fare">{route.fare_status === 'unknown' || !route.total_fare ? 'Fare unavailable' : `${route.fare_status === 'exact' ? 'Fare' : 'Estimated fare'} ${formatFare(route.total_fare)}`}</span>
      </div>
      {isSelected && route.fare_status !== 'unknown' && route.fare_breakdown && <div className="route-card-context">
        {route.fare_breakdown.base !== null && `Base ¥${route.fare_breakdown.base.toLocaleString()} `}
        {route.fare_breakdown.surcharge !== null && `+ surcharge ¥${route.fare_breakdown.surcharge.toLocaleString()} `}
        {route.fare_breakdown.seat_basis && `(${route.fare_breakdown.seat_basis})`}
      </div>}
      <div className="route-card-context">Daily timetable: source confirmed per passenger leg{route.segments.some(s => s.segment_type === 'bus') && ' · bus detail unavailable'}</div>
    </Card>
  );
}
