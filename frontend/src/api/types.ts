export interface Station {
  id?: string;
  name: string;
  name_jp?: string;
  lat: number;
  lng: number;
  platform: string | null;
  has_midori_office: boolean;
}

export interface ScheduleCandidate {
  candidate_id: string;
  departure_time: string;
  arrival_time: string;
  train_name: string;
  train_type: string;
  direction: string;
  is_current: boolean;
}

export interface RouteSegment {
  segment_type: 'train' | 'bus' | 'walk';
  railway_name: string;
  duration: string;
  is_through: boolean;
  schedule_candidates?: ScheduleCandidate[];
}

export interface PlannerMetadata {
  planner_state: string;
  planner_mode: string;
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
  planner_metadata?: PlannerMetadata;
}

export interface DepartureInfo {
  id: string;
  time: string;
  arrival_time?: string;
  train_name: string;
  train_type?: string;
  platform?: string;
  direction?: string;
  metadata?: Record<string, any>;
}

export interface Timetable {
  route_id: string;
  weekday: DepartureInfo[];
  saturday: DepartureInfo[];
  holiday: DepartureInfo[];
}

export interface LegSelection {
  segment_index: number;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  arrival_time?: string;
  transport_name?: string;
  platform?: number;
  fare?: number;
}

export interface MovementRequest {
  route_id: string;
  selected_departure_time: string;
  selected_arrival_time: string;
  departure_station: string;
  arrival_station: string;
  search_time?: string;
  search_date?: string;
  notion_page_url?: string;
  legs?: LegSelection[];
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
