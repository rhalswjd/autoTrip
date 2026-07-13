export interface Station {
  id?: string;
  name: string;
  name_jp?: string;
  lat: number;
  lng: number;
  platform: string | null;
  has_midori_office: boolean;
}

export interface RouteSegment {
  segment_type: 'train' | 'bus' | 'walk';
  railway_name: string;
  duration: string;
  is_through: boolean;
}

export interface Route {
  id: string;
  departure_station: string;
  arrival_station: string;
  railway_name: string;
  total_duration: string;
  total_fare: number;
  transfer_count: number;
  polyline: string;
  stations: Station[];
  segments: RouteSegment[];
}

export interface DepartureInfo {
  time: string;
  train_name: string;
}

export interface Timetable {
  route_id: string;
  first_train: string;
  last_train: string;
  departures: DepartureInfo[];
}

export interface MovementRequest {
  route_id: string;
  selected_departure_time: string;
  selected_arrival_time: string;
  departure_station: string;
  arrival_station: string;
  search_time?: string;
  search_date?: string;
}

export interface MovementResponse {
  route_id: string;
  departure_station: string;
  arrival_station: string;
  selected_departure_time: string;
  selected_arrival_time: string;
  search_mode: string;
  status: string;
  notion_url: string;
}

export interface StationSearchResult {
  id: string;
  english_name: string;
  japanese_name: string;
  has_midori_office: boolean;
}

export interface SearchParams {
  departure_station: string;
  arrival_station: string;
  departure_time?: string;
  departure_date?: string;
}
