import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sortRoutes, routeSections } from '../src/utils/routePresentation.ts';
import type { Route } from '../src/api/types.ts';

const routes = [
  { id: 'slow', total_duration: '3h', transfer_count: 0, total_fare: 0, fare_status: 'unknown' },
  { id: 'quick', total_duration: '59m', transfer_count: 2, total_fare: 4700, fare_status: 'indicative' },
  { id: 'cheap', total_duration: '1h 30m', transfer_count: 1, total_fare: 2000, fare_status: 'indicative' },
] as Route[];
test('Travel time is elapsed, transfers are numeric, unknown fare is not free', () => {
  assert.equal(sortRoutes(routes, 'time')[0].id, 'quick');
  assert.equal(sortRoutes(routes, 'transfers')[0].id, 'slow');
  assert.deepEqual(sortRoutes(routes, 'fare').map(r => r.id), ['cheap', 'quick', 'slow']);
  assert.equal(routes[0].id, 'slow');
});
test('strict, daily and later alternatives have separate honest labels', () => {
  assert.equal(routeSections.length, 3);
  assert.ok(routeSections.every(s => !/best|recommended/i.test(s.title)));
});
