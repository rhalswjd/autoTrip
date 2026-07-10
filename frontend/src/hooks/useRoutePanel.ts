import { useState, useCallback } from 'react';
import type { StationSearchResult, Route } from '../api/types';

export function useRoutePanel() {
  const [departureStation, setDepartureStation] = useState<StationSearchResult | null>(null);
  const [arrivalStation, setArrivalStation] = useState<StationSearchResult | null>(null);
  const [routes, setRoutes] = useState<Route[] | undefined>(undefined);
  const [routesLoading, setRoutesLoading] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);

  const handleStationSelect = useCallback(
    (station: StationSearchResult) => {
      if (!departureStation) {
        setDepartureStation(station);
      } else if (!arrivalStation) {
        setArrivalStation(station);
      } else {
        setArrivalStation(station);
      }
    },
    [departureStation, arrivalStation]
  );

  const handleRoutesLoaded = useCallback((loadedRoutes: Route[] | undefined, isLoading: boolean) => {
    setRoutes(loadedRoutes);
    setRoutesLoading(isLoading);
    if (loadedRoutes !== routes) {
      setSelectedRoute(null);
    }
  }, [routes]);

  const handleRouteSelect = useCallback((route: Route) => {
    setSelectedRoute((prev) => (prev?.id === route.id ? null : route));
  }, []);

  const clearSelection = useCallback(() => {
    setDepartureStation(null);
    setArrivalStation(null);
    setRoutes(undefined);
    setRoutesLoading(false);
    setSelectedRoute(null);
  }, []);

  return {
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
    clearSelection,
  };
}
