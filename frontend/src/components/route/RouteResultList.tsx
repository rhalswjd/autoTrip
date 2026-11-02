import { useState, useMemo, useEffect } from 'react';
import type { Route } from '../../api/types';
import { RouteCard } from './RouteCard';
import { RouteLoading } from './RouteLoading';
import { RouteEmpty } from './RouteEmpty';
import { sortRoutes, routeSections } from '../../utils/routePresentation';
import type { RouteSort } from '../../utils/routePresentation';
import { Button } from '../ui';
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
  const [sortOption, setSortOption] = useState<RouteSort>('time');
  const [showAll, setShowAll] = useState(false);
  useEffect(() => setShowAll(false), [routes]);
  const sortedRoutes = useMemo(() => sortRoutes(routes || [], sortOption), [routes, sortOption]);
  const requested = sortedRoutes.filter(route => (route.result_kind || 'requested') === 'requested');
  const visibleRoutes = showAll ? sortedRoutes : (requested.length ? requested : sortedRoutes).slice(0, 3);

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
      <div className="route-result-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span className="route-result-header-title">Routes</span>
          <span className="route-result-header-count" style={{ marginLeft: '8px' }}>
            {routes.length} {routes.length === 1 ? 'result' : 'results'}
          </span>
        </div>
        <label>Sort by: <select aria-label="Sort by"
          value={sortOption}
          onChange={(e) => setSortOption(e.target.value as RouteSort)}
          style={{
            padding: '4px 8px',
            borderRadius: '4px',
            border: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-surface)',
            color: 'var(--text-primary)',
            fontSize: '14px',
            cursor: 'pointer'
          }}
        >
          <option value="time">Travel time</option>
          <option value="transfers">Fewest transfers</option>
          <option value="fare">Lowest estimated fare</option>
        </select></label>
      </div>
      <nav aria-label="Alternative service shortcuts" className="route-alternative-shortcuts">
        {routeSections.filter(section => section.kind !== 'requested').map(section => {
          const alternative = sortRoutes(routes.filter(route => route.result_kind === section.kind), 'time')[0];
          return alternative && <button key={section.kind} type="button" onClick={() => onSelectRoute(alternative)}>
            <strong>{section.title}: {alternative.railway_name}</strong>
            <span>{alternative.search_date} · {alternative.departure_time} → {alternative.arrival_time} · {alternative.total_duration}</span>
            <small>{alternative.alternative_reason}</small>
          </button>;
        })}
      </nav>
      <div className="route-result-items" id="route-results" aria-live="polite">
        {routeSections.map(section => {
          const items = visibleRoutes.filter(route => (route.result_kind || 'requested') === section.kind);
          return items.length > 0 && <section key={section.kind} data-result-kind={section.kind}>
            <h3 className="route-section-title">{section.title}</h3>
            <div role="listbox" aria-label={section.title} className="route-result-items">
        {items.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            isSelected={selectedRoute?.id === route.id}
            onClick={onSelectRoute}
          />
        ))}</div></section>;
        })}
      </div>
      {routes.length > 3 && <Button variant="secondary" aria-expanded={showAll} aria-controls="route-results"
        onClick={() => setShowAll(value => !value)}>{showAll ? 'Show less' : 'Show more'}</Button>}
    </div>
  );
}
