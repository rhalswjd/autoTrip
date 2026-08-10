import { useState, useCallback } from 'react';
import { Sidebar } from '../layouts/Sidebar';
import { SearchBar, SearchResultList } from '../components/search';
import { RouteSearchForm, RouteResultList, RouteTimelineV2, RouteSummary } from '../components/route';
import { TimetableList, TransferWizard } from '../components/timetable';
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

  console.log("SearchPage data:", data);
  console.log("SearchPage data.weekday:", (data as any)?.weekday);
  console.log("SearchPage data.data:", (data as any)?.data);

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
              <RouteTimelineV2 route={selectedRoute} />
              <RouteSummary route={selectedRoute} />
              
              <Divider style={{ margin: '16px 0' }} />
              {selectedRoute.segments.length > 1 ? (
                <TransferWizard route={selectedRoute} />
              ) : (
                <TimetableList route={selectedRoute} />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
