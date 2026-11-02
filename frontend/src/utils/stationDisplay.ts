import type { Route, Station, StationSearchResult } from '../api/types';

/** Presentation only. Search and persistence must retain canonical identity fields. */
export function stationDisplayName(station: Station | StationSearchResult): string {
  return station.display_name_en || ('english_name' in station ? station.english_name : station.name);
}

export function routeEndpointDisplayName(route: Route, endpoint: 'departure' | 'arrival'): string {
  const station = endpoint === 'departure' ? route.stations[0] : route.stations.at(-1);
  return (station && stationDisplayName(station)) || route[`${endpoint}_station`];
}
