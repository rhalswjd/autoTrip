import { test } from 'node:test';
import assert from 'node:assert/strict';
import { itineraryPreview, operatingMinute, selectedPassengerLegs } from '../src/utils/itinerary.ts';
import { selectedTimetableBucket } from '../src/utils/timetable.ts';
import type { Route, DepartureInfo, Timetable } from '../src/api/types.ts';

const route = {
  total_fare: 15000, total_duration: '60m', fare_status: 'indicative',
  passenger_legs: [{ index: 0, segment_type: 'train', raw_segment_indices: [0, 1],
    departure_station: { name: 'Fukui' }, arrival_station: { name: 'Kanazawa' },
    railway_names: ['Rail'], through_boundaries: [{ name: 'Daishoji' }] }],
} as Route;
const exact = { id: 'official-exact', time: '08:00', arrival_time: '09:20', train_name: 'Local',
  platform: '', fare_status: 'unknown', base_fare: null, express_fare: null } as DepartureInfo;

test('selected exact train replaces elapsed and does not reuse another service fare', () => {
  const selected = itineraryPreview(route, { 0: exact });
  assert.equal(selected.total_duration, '80m');
  assert.equal(selected.fare_status, 'unknown');
  assert.equal(selected.total_fare, 0);
});

test('one continuous PassengerLeg creates one persistence child across a through boundary', () => {
  const selections = selectedPassengerLegs(route, { 0: exact });
  assert.equal(selections.length, 1);
  assert.equal(selections[0].arrival_station, 'Kanazawa');
  assert.equal(selections[0].exact_departure_id, 'official-exact');
  assert.equal(selections[0].base_fare, undefined);
  assert.equal(selections[0].platform, undefined);
});

for (const calendar of ['weekday', 'saturday', 'holiday'] as const) {
  test(`${calendar} uses only its selected operating calendar`, () => {
    const timetable = { selected_calendar: calendar, weekday: [], saturday: [], holiday: [],
      [calendar]: [exact] } as unknown as Timetable;
    assert.equal(selectedTimetableBucket(timetable).departures[0].id, exact.id);
  });
}

test('an empty Saturday cannot fall back to weekday', () => {
  assert.deepEqual(selectedTimetableBucket({ selected_calendar: 'saturday', weekday: [exact],
    saturday: [], holiday: [] } as unknown as Timetable).departures, []);
});

test('overnight arrivals use the railway operating day', () => {
  assert.equal(operatingMinute('00:30') - operatingMinute('23:30'), 60);
});

test('selected transfer journey separates onboard and waiting from elapsed', () => {
  const two = { ...route, passenger_legs: [route.passenger_legs[0], { ...route.passenger_legs[0], index: 1 }] } as Route;
  const selected = itineraryPreview(two, { 0: { ...exact, arrival_time: '08:50' },
    1: { ...exact, time: '09:00', arrival_time: '10:30' } });
  assert.equal(selected.total_duration, '150m');
  assert.equal(selected.onboard_duration, '140m');
  assert.equal(selected.waiting_duration, '10m');
});

test('door-to-door elapsed retains provider-estimated final walking connection', () => {
  const withWalk = { ...route, arrival_time: '09:27', passenger_legs: [
    { ...route.passenger_legs[0], arrival_time: '09:20' },
    { ...route.passenger_legs[0], index: 1, segment_type: 'walk', departure_time: '09:22', arrival_time: '09:27', duration: '5m' },
  ] } as Route;
  const selected = itineraryPreview(withWalk, { 0: exact });
  assert.equal(selected.total_duration, '87m');
  assert.equal(selected.arrival_time, '09:27');
  assert.equal(selected.timing_status, 'includes_estimated_walking');
});
