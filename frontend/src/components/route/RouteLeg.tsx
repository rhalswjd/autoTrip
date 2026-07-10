import './RouteTimeline.css';

export interface RouteLegProps {
  railwayName: string;
  stationCount: number;
  duration?: string;
}

export function RouteLeg({ railwayName, stationCount, duration }: RouteLegProps) {
  return (
    <div className="route-leg">
      <div className="route-leg-line" aria-hidden="true" />
      <div className="route-leg-info">
        <span className="route-leg-railway">{railwayName}</span>
        <span className="route-leg-detail">
          {stationCount} {stationCount === 1 ? 'stop' : 'stops'} {duration ? `• ${duration}` : ''}
        </span>
      </div>
    </div>
  );
}
