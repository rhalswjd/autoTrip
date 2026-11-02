import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { Station, StationSearchResult } from '../src/api/types.ts';
import { stationDisplayName } from '../src/utils/stationDisplay.ts';
import { selectedSearchParams } from '../src/utils/stationSelection.ts';

test('verified display names leave selected identity and provider input untouched', () => {
  const origin = { id: '1163907', english_name: 'Kiikatsura', japanese_name: '紀伊勝浦', display_name_en: 'Kii-Katsuura' } as StationSearchResult;
  const target = { id: '9960914', english_name: 'Yuhigaurakitsuonsen', japanese_name: '夕日ヶ浦木津温泉', display_name_en: 'Yuhigaura-Kitsuonsen' } as StationSearchResult;
  assert.equal(stationDisplayName(origin), 'Kii-Katsuura');
  assert.equal(stationDisplayName(target), 'Yuhigaura-Kitsuonsen');
  assert.equal(stationDisplayName({ name: 'Kiikatsura', display_name_en: origin.display_name_en } as Station), 'Kii-Katsuura');
  const payload = selectedSearchParams(origin, target, '2026-11-02', '06:00');
  assert.equal(payload.departure_station, '紀伊勝浦');
  assert.equal(payload.arrival_station, '夕日ヶ浦木津温泉');
  assert.equal(payload.arrival_station_id, '9960914');
  assert.deepEqual(payload, selectedSearchParams({ ...origin, display_name_en: 'Cosmetic' }, target, '2026-11-02', '06:00'));
});

test('unregistered and already readable names retain their existing spelling', () => {
  assert.equal(stationDisplayName({ name: 'Shin-Osaka' } as Station), 'Shin-Osaka');
  assert.equal(stationDisplayName({ english_name: 'Imported' } as StationSearchResult), 'Imported');
});
