import { api } from './client';
import type { Route, Timetable, MovementRequest, MovementResponse, StationSearchResult, SearchParams } from './types';

export function searchRoutes(params: SearchParams): Promise<Route[]> {
  const query = new URLSearchParams();
  query.set('departure_station', params.departure_station);
  query.set('arrival_station', params.arrival_station);
  if (params.departure_station_id) query.set('departure_station_id', params.departure_station_id);
  if (params.arrival_station_id) query.set('arrival_station_id', params.arrival_station_id);
  query.set('departure_time', params.departure_time);
  query.set('departure_date', params.departure_date);
  return api.get<Route[]>(`/search?${query.toString()}`);
}

export function getTimetable(routeId: string): Promise<Timetable> {
  return api.get<Timetable>(`/routes/${routeId}/timetable`);
}

export function getSegmentTimetable(routeId: string, segmentIndex: number): Promise<Timetable> {
  return api.get<Timetable>(`/routes/${routeId}/segments/${segmentIndex}/timetable`);
}

export function getPassengerTimetable(routeId: string, legIndex: number, cursor = 0, date?: string, notBefore?: string): Promise<Timetable> {
  return api.get<Timetable>(`/routes/${routeId}/legs/${legIndex}/timetable?cursor=${cursor}${date ? `&date=${encodeURIComponent(date)}` : ''}${notBefore ? `&not_before=${encodeURIComponent(notBefore)}` : ''}`);
}

export function getSegmentPlatform(routeId: string, segmentIndex: number, time: string, trainName: string, date?: string): Promise<{ platform: string | null }> {
  const query = new URLSearchParams();
  query.set('time', time);
  query.set('train_name', trainName);
  if (date) query.set('date', date);
  return api.get<{ platform: string | null }>(`/routes/${routeId}/segments/${segmentIndex}/platform?${query.toString()}`);
}

export function createMovement(data: MovementRequest): Promise<MovementResponse> {
  return api.post<MovementResponse>('/movements', data);
}

export function searchStations(query: string): Promise<StationSearchResult[]> {
  return api.get<StationSearchResult[]>(`/stations/search?q=${encodeURIComponent(query)}`);
}
