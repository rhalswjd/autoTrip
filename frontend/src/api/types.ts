export const SeatPreference = {
  RESERVED: 'RESERVED',
  NON_RESERVED: 'NON_RESERVED',
  GREEN: 'GREEN',
  NOT_APPLICABLE: 'NOT_APPLICABLE'
} as const;

export type SeatPreference = typeof SeatPreference[keyof typeof SeatPreference];

export interface Station {
  display_name_en?: string;
  prefecture?: string;
  railway_company?: string;
  provider_ids?: Record<string, string>;
  provider_aliases?: Record<string, string>;
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
  railway_id: string;
  departure_time: string;
  arrival_time: string;
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
  fare_breakdown?: { base: number | null; surcharge: number | null; seat_supplement: number | null; total: number | null; seat_basis: string } | null;
  result_kind: 'requested' | 'daily_alternative' | 'later_practical';
  alternative_reason: string;
  evidence_url: string;
  timing_status: string;
  passenger_legs: PassengerLeg[];
  family_key: string;
  categories: string[];
  waiting_duration: string;
  fare_status: string;
  id: string;
  departure_station: string;
  arrival_station: string;
  railway_name: string;
  departure_time: string;
  arrival_time: string;
  total_duration: string;
  onboard_duration: string;
  non_riding_duration: string;
  total_fare: number;
  transfer_count: number;
  polyline: string;
  search_date?: string;
  search_time?: string;
  search_source?: string;
  source_rank?: number;
  stations: Station[];
  segments: RouteSegment[];
  planner_metadata?: PlannerMetadata;
}

export type PlatformStatus = 'KNOWN' | 'SOURCE_NOT_PROVIDED' | 'LOOKUP_FAILED';

export interface DepartureInfo {
  platform_status?: PlatformStatus;
  arrival_platform_status?: PlatformStatus;
  departure_datetime?: string;
  arrival_datetime?: string;
  operating_date: string;
  arrival_platform: string;
  source: string;
  source_url: string;
  train_number: string;
  base_fare: number | null;
  express_fare: number | null;
  fare_status: string;
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
  search_date?: string;
  availability: 'SUPPORTED' | 'UNSUPPORTED' | 'PROVIDER_ERROR';
  source: string;
  source_url: string;
  status: string;
  message: string;
  complete: boolean;
  next_cursor: number | null;
  total_candidates: number;
  route_id: string;
  selected_calendar: 'weekday' | 'saturday' | 'holiday';
  weekday: DepartureInfo[];
  saturday: DepartureInfo[];
  holiday: DepartureInfo[];
}

export interface LegSelection {
  source?: string;
  platform_status?: PlatformStatus | null;
  arrival_platform_status?: PlatformStatus | null;
  arrival_platform?: number | string | null;
  timetable_date?: string;
  departure_datetime?: string;
  arrival_datetime?: string;
  passenger_leg_index?: number;
  exact_departure_id?: string;
  segment_index: number;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  arrival_time?: string;
  transport_name?: string;
  railway_name?: string;
  platform?: number | string | null;
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
  parent_page_id?: string | null;
  child_page_ids?: string[];
  route_id: string;
  departure_station: string;
  arrival_station: string;
  selected_departure_time: string;
  selected_arrival_time: string;
  search_mode: string;
  status: string;
  notion_url: string;
}

export interface PassengerLeg {
  index: number;
  raw_segment_indices: number[];
  departure_station: Station;
  arrival_station: Station;
  segment_type: string;
  railway_names: string[];
  railway_names_jp: string[];
  through_boundaries: Station[];
  has_seat_selection: boolean;
  departure_time: string;
  arrival_time: string;
  duration: string;
}

export interface StationSearchResult {
  display_name_en?: string;
  prefecture?: string;
  region?: string;
  railway_company?: string;
  display_label?: string;
  provider_ids?: Record<string, string>;
  provider_aliases?: Record<string, string>;
  id: string;
  english_name: string;
  japanese_name: string;
  has_midori_office: boolean;
}

export interface SearchParams {
  departure_station_id?: string;
  arrival_station_id?: string;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  departure_date: string;
}
