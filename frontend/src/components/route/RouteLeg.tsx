import './RouteTimeline.css';

export interface RouteLegProps {
  railwayName: string;
  duration?: string;
}

export function RouteLeg({ railwayName, duration }: RouteLegProps) {
  const isWalk = railwayName === 'Walk';
  
  return (
    <div className={`route-leg ${isWalk ? 'route-leg-walk' : ''}`}>
      <div className={`route-leg-line ${isWalk ? 'route-leg-line-dashed' : ''}`} aria-hidden="true" />
      <div className="route-leg-info">
        <span className="route-leg-railway">{railwayName}</span>
        {duration && (
          <span className="route-leg-detail">
            {duration}
          </span>
        )}
      </div>
    </div>
  );
}
