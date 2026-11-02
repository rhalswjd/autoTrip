import type { SearchParams, StationSearchResult } from '../api/types';

export function selectedSearchParams(origin: StationSearchResult, target: StationSearchResult,
  date: string, time: string): SearchParams {
  return { departure_station_id: origin.id, arrival_station_id: target.id,
    departure_station: origin.japanese_name, arrival_station: target.japanese_name,
    departure_date: date, departure_time: time };
}
