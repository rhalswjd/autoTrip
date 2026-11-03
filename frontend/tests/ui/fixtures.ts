// Synthetic data used only by the deterministic UI regression harness.
import type { DepartureInfo, PassengerLeg, Route, Station, Timetable } from '../../src/api/types';

const station = (name: string, jp: string): Station => ({ name, display_name_en: name, name_jp: jp, lat: 0, lng: 0, platform: null, has_midori_office: false });
const kii = station('Kii-Katsuura', '紀伊勝浦');
const osaka = station('Osaka', '大阪');
const toyooka = station('Toyooka', '豊岡');
const yuhigaura = station('Yuhigaura-Kitsuonsen', '夕日ヶ浦木津温泉');
const kyoto = station('Kyoto', '京都');
const leg = (index: number, from: Station, to: Station, service: string, start: string, end: string): PassengerLeg => ({
  index, raw_segment_indices: [index], departure_station: from, arrival_station: to, segment_type: 'train', railway_names: [service], railway_names_jp: [],
  through_boundaries: [], has_seat_selection: index < 2, departure_time: start, arrival_time: end, duration: '',
});
export const route: Route = {
  id: 'visual-transfer', result_kind: 'requested', alternative_reason: '', evidence_url: '', timing_status: 'search',
  passenger_legs: [leg(0, kii, osaka, 'Kuroshio', '06:45', '10:46'), leg(1, osaka, toyooka, 'Konotori', '12:11', '14:43'), leg(2, toyooka, yuhigaura, 'Kyoto Tango Railway', '14:51', '15:24')],
  family_key: 'visual-transfer', categories: ['FASTEST'], waiting_duration: '1h 33m', fare_status: 'estimated', departure_station: kii.name, arrival_station: yuhigaura.name,
  railway_name: 'Kuroshio / Konotori / Kyoto Tango Railway', departure_time: '06:45', arrival_time: '15:24', total_duration: '8h 39m', onboard_duration: '7h 6m', non_riding_duration: '1h 33m',
  total_fare: 12480, transfer_count: 2, polyline: '', search_date: '2026-11-02', search_time: '06:00', stations: [kii, osaka, toyooka, yuhigaura], segments: [],
};
export const throughRoute: Route = { ...route, id: 'visual-through', categories: ['FEWEST TRANSFERS'], transfer_count: 0, departure_station: kyoto.name, stations: [kyoto, yuhigaura],
  railway_name: 'Hashidate', departure_time: '12:25', arrival_time: '15:11', total_duration: '2h 46m', waiting_duration: '0m',
  passenger_legs: [{ ...leg(0, kyoto, yuhigaura, 'Hashidate', '12:25', '15:11'), railway_names: ['Hashidate / JR West', 'Kyoto Tango Railway'], through_boundaries: [station('Fukuchiyama', '福知山')], raw_segment_indices: [0, 1] }],
};
export const walkingRoute: Route = { ...route, id: 'visual-walking', categories: ['CHEAPEST'], total_duration: '10h 4m', total_fare: 11000, transfer_count: 1,
  passenger_legs: [route.passenger_legs[0], { ...leg(1, osaka, kyoto, 'Walk', '', ''), segment_type: 'walk', has_seat_selection: false }, { ...route.passenger_legs[2], index: 2, departure_station: kyoto }],
};
const kashihara = station('Kashihara-jingu-mae', '橿原神宮前');
const nishiguchi = station('Kashihara-jingu-nishiguchi', '橿原神宮西口');
export const longNameRoute: Route = { ...throughRoute, id: 'visual-long-names', departure_station: kashihara.name, arrival_station: nishiguchi.name,
  stations: [kashihara, nishiguchi], railway_name: 'Kyoto Tango Railway Limited Express Hashidate',
  passenger_legs: [{ ...leg(0, kashihara, nishiguchi, 'Kyoto Tango Railway Limited Express Hashidate', '12:25', '15:11'), through_boundaries: [] }],
};
export const routes: Route[] = [route, throughRoute, walkingRoute, { ...route, id: 'visual-long-wait', total_duration: '15h 59m', waiting_duration: '8h 59m', categories: [] },
  { ...throughRoute, id: 'visual-daily', result_kind: 'daily_alternative', departure_time: '09:50', arrival_time: '12:40', alternative_reason: 'Outside your requested time window.', categories: [] },
  { ...throughRoute, id: 'visual-later', result_kind: 'later_practical', alternative_reason: 'A later departure with fewer changes.', categories: [] },
];

export function departure(index: number, time: string, arrival: string, date = '2026-11-02'): DepartureInfo {
  return { id: `${index}-${time}-${date}`, time, arrival_time: arrival, operating_date: date, departure_datetime: `${date}T${time}:00+09:00`, arrival_datetime: `${date}T${arrival}:00+09:00`,
    train_name: ['Kuroshio 6', 'Konotori 7', 'Kyoto Tango Local'][index], train_number: index === 0 ? '56M' : '', platform: index === 0 ? '1' : '', arrival_platform: '',
    platform_status: index === 0 ? 'KNOWN' : 'SOURCE_NOT_PROVIDED', arrival_platform_status: index === 2 ? 'LOOKUP_FAILED' : 'SOURCE_NOT_PROVIDED', source: index === 2 ? 'yahoo' : 'jr_odekake',
    source_url: '', base_fare: null, express_fare: null, fare_status: 'unknown' };
}
export function timetable(index: number, date = '2026-11-02', routeId = route.id): Timetable {
  const direct = ['visual-through', 'visual-daily', 'visual-later', 'visual-long-names'].includes(routeId);
  const trains = direct ? [{ ...departure(0, '12:25', '15:11', date), train_name: routeId === 'visual-long-names' ? 'Kyoto Tango Railway Limited Express Hashidate 7' : 'Hashidate 7', train_number: '5087M', platform: '31' }] : index === 0 ? [departure(0, '06:45', '10:46', date), departure(0, '07:45', '11:46', date)] : index === 1 ?
    [departure(1, '09:11', '11:43', date), departure(1, '12:11', '14:43', date), departure(1, '13:11', '15:43', date)] :
    [departure(2, '14:51', '15:24', date), departure(2, '15:51', '16:24', date)];
  return { route_id: route.id, availability: 'SUPPORTED', source: index === 2 ? 'yahoo' : 'jr_odekake', source_url: '', status: 'available', message: '', complete: true, next_cursor: null, total_candidates: trains.length, selected_calendar: 'weekday', weekday: trains, saturday: [], holiday: [] };
}
