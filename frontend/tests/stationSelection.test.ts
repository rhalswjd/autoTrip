import { test } from 'node:test';
import assert from 'node:assert/strict';
import { selectedSearchParams } from '../src/utils/stationSelection.ts';
import type { StationSearchResult } from '../src/api/types.ts';

test('fuzzy discovery becomes an exact selected identity, not another name lookup', () => {
  const origin = { id: '1160712', english_name: 'Kashiwara', japanese_name: '柏原(大阪)', region: 'Osaka' } as StationSearchResult;
  const target = { id: '1160704', english_name: 'Nara', japanese_name: '奈良' } as StationSearchResult;
  const payload = selectedSearchParams(origin, target, '2026-11-02', '09:00');
  assert.equal(payload.departure_station_id, origin.id);
  assert.equal(payload.arrival_station_id, target.id);
  assert.equal(payload.departure_station, origin.japanese_name);
  assert.equal(payload.departure_time, '09:00');
  assert.equal(selectedSearchParams({ ...origin, id: '1163005' }, target, '2026-11-02', '09:00').departure_station_id, '1163005');
});
