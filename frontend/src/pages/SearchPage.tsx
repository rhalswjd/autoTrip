import { useState, useCallback } from 'react';
import { Sidebar } from '../layouts/Sidebar';
import { SearchBar, SearchResultList } from '../components/search';
import { RouteSearchForm, RouteResultList, RouteTimeline, RouteSummary } from '../components/route';
import { TimetableList } from '../components/timetable';
import { Divider } from '../components/ui';
import { useStationSearch, useRoutePanel } from '../hooks';

export function SearchPage() {
  const [searchQuery, setSearchQuery] = useState('');
  
  const {
    departureStation,
    setDepartureStation,
    arrivalStation,
    setArrivalStation,
    routes,
    routesLoading,
    selectedRoute,
    handleStationSelect,
    handleRoutesLoaded,
    handleRouteSelect,
  } = useRoutePanel();

  const { data, isLoading, error, refetch } = useStationSearch(searchQuery);

  const handleEscape = useCallback(() => {
    setSearchQuery('');
  }, []);

  return (
    <div className="split-view">
      <Sidebar>
        <div className="search-container">
          <SearchBar value={searchQuery} onChange={setSearchQuery} autoFocus />
          <SearchResultList
            query={searchQuery}
            results={data}
            isLoading={isLoading}
            error={error}
            selectedStationId={
              departureStation?.id === arrivalStation?.id
                ? null
                : arrivalStation?.id || departureStation?.id || null
            }
            onSelect={handleStationSelect}
            onRetry={() => refetch()}
            onEscape={handleEscape}
          />
        </div>
      </Sidebar>

      <main className="detail-panel">
        <div className="route-detail-section">
          <RouteSearchForm
            departure={departureStation}
            arrival={arrivalStation}
            onDepartureChange={setDepartureStation}
            onArrivalChange={setArrivalStation}
            onRoutesLoaded={handleRoutesLoaded}
          />

          {(routes || routesLoading) && (
            <>
              <Divider />
              <RouteResultList
                routes={routes}
                isLoading={routesLoading}
                selectedRoute={selectedRoute}
                onSelectRoute={handleRouteSelect}
              />
            </>
          )}

          {selectedRoute && (
            <>
              <Divider />
              <RouteTimeline route={selectedRoute} />
              <RouteSummary route={selectedRoute} />
              
              <Divider style={{ margin: '16px 0' }} />
              <TimetableList route={selectedRoute} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
