import assert from 'node:assert/strict';
import { test } from 'node:test';
import { calendarDate, shiftCalendarDay, shiftCalendarMonth } from '../src/utils/calendar.ts';

test('calendar keyboard day navigation crosses leap days and year boundaries', () => {
  assert.equal(shiftCalendarDay('2028-02-28', 1), '2028-02-29');
  assert.equal(shiftCalendarDay('2028-02-29', 1), '2028-03-01');
  assert.equal(shiftCalendarDay('2026-01-01', -1), '2025-12-31');
  assert.equal(shiftCalendarDay('2026-12-28', 7), '2027-01-04');
});

test('calendar month and year navigation clamps to the target month', () => {
  assert.equal(shiftCalendarMonth('2026-01-31', 1), '2026-02-28');
  assert.equal(shiftCalendarMonth('2028-02-29', 12), '2029-02-28');
  assert.equal(shiftCalendarMonth('2026-01-31', -1), '2025-12-31');
});

test('date-only values stay independent of local DST and preserve ISO date', () => {
  assert.equal(shiftCalendarDay('2026-03-08', 1), '2026-03-09');
  assert.equal(shiftCalendarDay('2026-11-01', -1), '2026-10-31');
  assert.equal(calendarDate('2026-11-03').toISOString(), '2026-11-03T12:00:00.000Z');
});
