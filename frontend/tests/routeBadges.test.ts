import { test } from 'node:test';
import assert from 'node:assert/strict';
import { routeBadges } from '../src/utils/routeBadges.ts';
import type { Route } from '../src/api/types.ts';

const direct = {
  transfer_count: 0, search_date: '2026-11-03', departure_time: '17:12', arrival_time: '18:51',
  passenger_legs: [{ segment_type: 'train', raw_segment_indices: [0, 1], through_boundaries: [{}] }],
} as Route;

test('one continuous ride, including a through service, shows both simplicity facts', () => {
  assert.deepEqual(routeBadges(direct, '2026-11-03'), { direct: true, noTransfers: true, departsTomorrow: false });
});

test('zero transfers is independent of direct ride evidence', () => {
  assert.deepEqual(routeBadges({ ...direct, passenger_legs: [] }), { direct: false, noTransfers: true, departsTomorrow: false });
  assert.equal(routeBadges({ ...direct, passenger_legs: [{ ...direct.passenger_legs[0], segment_type: 'walk' }] }).direct, false);
  assert.equal(routeBadges({ ...direct, transfer_count: 2 }).noTransfers, false);
  assert.equal(routeBadges({ ...direct, transfer_count: 2 }).direct, false);
});

test('exactly the next calendar date shows tomorrow regardless of the clock', () => {
  for (const departure_time of ['00:01', '04:00', '17:12', '23:55']) {
    assert.equal(routeBadges({ ...direct, search_date: '2026-11-04', departure_time }, '2026-11-03').departsTomorrow, true);
    assert.equal(routeBadges({ ...direct, departure_time }, '2026-11-03').departsTomorrow, false);
  }
});

test('overnight arrival does not imply tomorrow departure', () => {
  const overnight = { ...direct, departure_time: '23:30', arrival_time: '01:20', total_duration: '1h 50m' };
  assert.equal(routeBadges(overnight, '2026-11-03').departsTomorrow, false);
});

test('date comparison handles month, year and leap boundaries', () => {
  for (const [requested, actual] of [['2026-11-30', '2026-12-01'], ['2026-12-31', '2027-01-01'], ['2028-02-28', '2028-02-29'], ['2028-02-29', '2028-03-01']]) {
    assert.equal(routeBadges({ ...direct, search_date: actual }, requested).departsTomorrow, true);
  }
});

test('missing, invalid, past and more distant dates never claim tomorrow', () => {
  for (const search_date of [undefined, '', '2026-11-02', '2026-11-05', '2026-02-30', '03/11/2026']) {
    assert.equal(routeBadges({ ...direct, search_date }, '2026-11-03').departsTomorrow, false);
  }
  assert.equal(routeBadges(direct).departsTomorrow, false);
  assert.equal(routeBadges(direct, '2026-11-02T23:59:00+09:00').departsTomorrow, false);
});

test('badge calculation does not mutate route data', () => {
  const route = Object.freeze({ ...direct, search_date: '2026-11-04' });
  const before = JSON.stringify(route);
  routeBadges(route, '2026-11-03');
  assert.equal(JSON.stringify(route), before);
});
