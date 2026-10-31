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
          <span className="route-summary-value">{route.total_duration || '열차 선택 후 확정'}</span>
          {route.timing_status === 'includes_estimated_walking' && <small>도보·연결시간은 검색 시 추정 포함</small>}
        </div>
        {route.onboard_duration && (
          <div className="route-summary-item">
            <span className="route-summary-label">Onboard</span>
            <span className="route-summary-value">{route.onboard_duration}</span>
          </div>
        )}
        {route.non_riding_duration && (
          <div className="route-summary-item">
            <span className="route-summary-label">Non-riding</span>
            <span className="route-summary-value">{route.non_riding_duration}</span>
          </div>
        )}
        {route.waiting_duration && <div className="route-summary-item">
          <span className="route-summary-label">Waiting</span>
          <span className="route-summary-value">{route.waiting_duration}</span>
        </div>}
        <div className="route-summary-item">
          <span className="route-summary-label">Fare</span>
          <span className="route-summary-value mono">{route.fare_status === 'unknown' ? '선택 열차 운임 미확정' : `${route.fare_status === 'exact' ? '' : '검색 시 예상 '}${formatFare(route.total_fare)}`}</span>
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
