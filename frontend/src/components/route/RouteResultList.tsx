import { useState, useMemo, useEffect, type ReactNode } from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import type { Route } from '../../api/types';
import { RouteCard } from './RouteCard';
import { RouteExpansion } from './RouteExpansion';
import { RouteLoading } from './RouteLoading';
import { RouteEmpty } from './RouteEmpty';
import { sortRoutes, routeSections, type RouteSort } from '../../utils/routePresentation';
import '../../styles/railway.css';

export interface RouteResultListProps {
  routes: Route[] | undefined;
  isLoading: boolean;
  selectedRoute: Route | null;
  onSelectRoute: (route: Route) => void;
  renderDetail?: (route: Route) => ReactNode;
}

export function RouteResultList({ routes, isLoading, selectedRoute, onSelectRoute, renderDetail }: RouteResultListProps) {
  const [sortOption, setSortOption] = useState<RouteSort>('time');
  const [showAll, setShowAll] = useState(false);
  useEffect(() => setShowAll(false), [routes]);
  const sorted = useMemo(() => sortRoutes(routes || [], sortOption), [routes, sortOption]);
  const requested = sorted.filter(route => (route.result_kind || 'requested') === 'requested');
  const primary = (requested.length ? requested : sorted).slice(0, 3);
  const visible = showAll ? sorted : sorted.filter(route => primary.includes(route) || route.id === selectedRoute?.id);
  const hasMore = sorted.some(route => !primary.includes(route));
  if (isLoading) return <RouteLoading />;
  if (!routes) return null;
  if (!routes.length) return <RouteEmpty />;

  return <div className="rail-results rail-ui">
    <header className="rail-results-header">
      <div><span className="rail-eyebrow">PLAN YOUR JOURNEY</span><h2>Choose your route <span>{routes.length} {routes.length === 1 ? 'option' : 'options'}</span></h2></div>
      <label className="rail-sort">Sort by<select value={sortOption} onChange={event => setSortOption(event.target.value as RouteSort)}>
        <option value="time">Travel time</option><option value="transfers">Fewest transfers</option><option value="fare">Estimated fare</option>
      </select></label>
    </header>
    <div id="route-results" className={selectedRoute ? 'rail-results-selected' : ''}>
      {routeSections.map(section => {
        const items = visible.filter(route => (route.result_kind || 'requested') === section.kind);
        const count = sorted.filter(route => route.result_kind === section.kind).length;
        if (!items.length && !count) return null;
        return <section key={section.kind} data-result-kind={section.kind} className="rail-result-section">
          <h3 tabIndex={-1}>{section.title}</h3>
          {!items.length && <button type="button" className="rail-text-button" onClick={event => { event.currentTarget.closest('section')?.querySelector('h3')?.focus(); setShowAll(true); }}>Show {count} {section.kind === 'daily_alternative' ? 'other direct services' : 'later options'} <ArrowDown size={14} /></button>}
          <ul className="rail-route-list">{items.map(route => <li key={route.id} className={selectedRoute?.id === route.id ? 'is-active' : ''}>
            <RouteCard route={route} isSelected={selectedRoute?.id === route.id} onClick={onSelectRoute} />
            <RouteExpansion id={`route-detail-${route.id}`} expanded={selectedRoute?.id === route.id}>
              {renderDetail?.(route)}
            </RouteExpansion>
          </li>)}</ul>
        </section>;
      })}
    </div>
    {hasMore && <button type="button" className="rail-show-more" aria-expanded={showAll} aria-controls="route-results"
      onClick={() => setShowAll(value => !value)}>
      {showAll ? <>Show less <ArrowUp size={16} /></> : <>Show more routes <span>{sorted.length - primary.length}</span><ArrowDown size={16} /></>}
    </button>}
  </div>;
}
