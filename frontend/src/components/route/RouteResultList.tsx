import { useState, useEffect, useMemo } from 'react';
import type { Route } from '../../api/types';
import { RouteCard } from './RouteCard';
import { RouteLoading } from './RouteLoading';
import { RouteEmpty } from './RouteEmpty';
import { Button } from '../ui';
import './RouteTimeline.css';

export interface RouteResultListProps {
  routes: Route[] | undefined;
  isLoading: boolean;
  selectedRoute: Route | null;
  onSelectRoute: (route: Route) => void;
}

type SortOption = 'best' | 'transfers' | 'walking' | 'fare';

export function RouteResultList({
  routes,
  isLoading,
  selectedRoute,
  onSelectRoute,
}: RouteResultListProps) {
  const [showAll, setShowAll] = useState(false);
  const [sortOption, setSortOption] = useState<SortOption>('best');

  useEffect(() => {
    setShowAll(false);
    setSortOption('best');
  }, [routes]);

  const sortedRoutes = useMemo(() => {
    if (!routes) return [];
    if (sortOption === 'best') return routes;
    
    return [...routes].sort((a, b) => {
      if (sortOption === 'transfers') {
        return a.transfer_count - b.transfer_count;
      }
      if (sortOption === 'fare') {
        return a.total_fare - b.total_fare;
      }
      if (sortOption === 'walking') {
        const walkA = (a.polyline.match(/Walk/g) || []).length;
        const walkB = (b.polyline.match(/Walk/g) || []).length;
        return walkA - walkB;
      }
      return 0;
    });
  }, [routes, sortOption]);

  if (isLoading) {
    return <RouteLoading />;
  }

  if (routes && routes.length === 0) {
    return <RouteEmpty />;
  }

  if (!routes) {
    return null;
  }

  const visibleRoutes = showAll ? sortedRoutes : sortedRoutes.slice(0, 3);
  const hasMore = routes.length > 3;

  return (
    <div>
      <div className="route-result-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span className="route-result-header-title">Routes</span>
          <span className="route-result-header-count" style={{ marginLeft: '8px' }}>
            {routes.length} {routes.length === 1 ? 'result' : 'results'}
          </span>
        </div>
        <select 
          value={sortOption}
          onChange={(e) => setSortOption(e.target.value as SortOption)}
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
          <option value="best">Best Route</option>
          <option value="transfers">Least Transfers</option>
          <option value="walking">Least Walking</option>
          <option value="fare">Lowest Fare</option>
        </select>
      </div>
      <div className="route-result-items" role="listbox" id="route-results" aria-live="polite" style={{ maxHeight: showAll ? '600px' : 'none', overflowY: showAll ? 'auto' : 'visible' }}>
        {visibleRoutes.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            isSelected={selectedRoute?.id === route.id}
            onClick={onSelectRoute}
          />
        ))}
      </div>
      
      {hasMore && (
        <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'center' }}>
          <Button 
            variant="secondary" 
            onClick={() => setShowAll(!showAll)}
            style={{ width: '100%', maxWidth: '300px' }}
          >
            {showAll ? 'Show Less' : 'Show More Routes'}
          </Button>
        </div>
      )}
    </div>
  );
}
