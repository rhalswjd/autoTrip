import { api } from './client';
import type { Route, Timetable, MovementRequest, MovementResponse, StationSearchResult, SearchParams } from './types';

export function searchRoutes(params: SearchParams): Promise<Route[]> {
  const query = new URLSearchParams();
  query.set('departure_station', params.departure_station);
  query.set('arrival_station', params.arrival_station);
  if (params.departure_time) query.set('departure_time', params.departure_time);
  if (params.departure_date) query.set('departure_date', params.departure_date);
  return api.get<Route[]>(`/search?${query.toString()}`);
}

export function getTimetable(routeId: string): Promise<Timetable> {
  return api.get<Timetable>(`/routes/${routeId}/timetable`);
}

export function createMovement(data: MovementRequest): Promise<MovementResponse> {
  return api.post<MovementResponse>('/movements', data);
}

export function searchStations(query: string): Promise<StationSearchResult[]> {
  return api.get<StationSearchResult[]>(`/stations/search?q=${encodeURIComponent(query)}`);
}
