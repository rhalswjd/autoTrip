import type { Route } from '../../api/types';
import './RouteTimeline.css';

export interface RouteSummaryProps {
  route: Route;
}

function formatFare(fare: number): string {
  return `¥${fare.toLocaleString()}`;
}

export function RouteSummary({ route }: RouteSummaryProps) {
  return (
    <div className="route-summary">
      <span className="route-summary-title">Summary</span>
      <div className="route-summary-grid">
        <div className="route-summary-item">
          <span className="route-summary-label">Duration</span>
          <span className="route-summary-value">{route.total_duration}</span>
        </div>
        <div className="route-summary-item">
          <span className="route-summary-label">Fare</span>
          <span className="route-summary-value mono">{formatFare(route.total_fare)}</span>
        </div>
        <div className="route-summary-item">
          <span className="route-summary-label">Transfers</span>
          <span className="route-summary-value">
            {route.transfer_count === 0 ? 'Direct' : `${route.transfer_count} transfer${route.transfer_count > 1 ? 's' : ''}`}
          </span>
        </div>
        <div className="route-summary-item">
          <span className="route-summary-label">Railway</span>
          <span className="route-summary-value">{route.railway_name}</span>
        </div>
        <div className="route-summary-item">
          <span className="route-summary-label">From</span>
          <span className="route-summary-value">{route.departure_station}</span>
        </div>
        <div className="route-summary-item">
          <span className="route-summary-label">To</span>
          <span className="route-summary-value">{route.arrival_station}</span>
        </div>
      </div>
    </div>
  );
}
