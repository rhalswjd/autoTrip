import type { Route } from '../../api/types';
import { RouteCard } from './RouteCard';
import { RouteLoading } from './RouteLoading';
import { RouteEmpty } from './RouteEmpty';
import './RouteTimeline.css';

export interface RouteResultListProps {
  routes: Route[] | undefined;
  isLoading: boolean;
  selectedRoute: Route | null;
  onSelectRoute: (route: Route) => void;
}

export function RouteResultList({
  routes,
  isLoading,
  selectedRoute,
  onSelectRoute,
}: RouteResultListProps) {
  if (isLoading) {
    return <RouteLoading />;
  }

  if (routes && routes.length === 0) {
    return <RouteEmpty />;
  }

  if (!routes) {
    return null;
  }

  return (
    <div>
      <div className="route-result-header">
        <span className="route-result-header-title">Routes</span>
        <span className="route-result-header-count">
          {routes.length} {routes.length === 1 ? 'result' : 'results'}
        </span>
      </div>
      <div className="route-result-items" role="listbox" id="route-results" aria-live="polite">
        {routes.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            isSelected={selectedRoute?.id === route.id}
            onClick={onSelectRoute}
          />
        ))}
      </div>
    </div>
  );
}
