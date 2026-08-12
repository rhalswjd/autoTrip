export const SeatPreference = {
  RESERVED: 'RESERVED',
  NON_RESERVED: 'NON_RESERVED',
  GREEN: 'GREEN',
  NOT_APPLICABLE: 'NOT_APPLICABLE'
} as const;

export type SeatPreference = typeof SeatPreference[keyof typeof SeatPreference];

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
  segment_type: string;
  railway_name: string;
  railway_name_jp: string;
  duration: string;
  is_through: boolean;
  schedule_candidates?: ScheduleCandidate[];
  departure_platform?: string | null;
  base_fare?: number | null;
  express_fare?: number | null;
  has_seat_selection?: boolean;
  selected_seat?: SeatPreference;
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
  base_fare?: number;
  express_fare?: number;
  selected_seat?: SeatPreference;
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
