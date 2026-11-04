import type { Route } from '../api/types';

function calendarDay(value: string | undefined): number | undefined {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return undefined;
  const timestamp = Date.parse(`${value}T00:00:00Z`);
  if (!Number.isFinite(timestamp) || new Date(timestamp).toISOString().slice(0, 10) !== value) return undefined;
  return timestamp;
}

/** Presentation facts only: never infer dates from clocks or create route alternatives. */
export function routeBadges(route: Route, requestedDepartureDate?: string) {
  const noTransfers = route.transfer_count === 0;
  const rides = route.passenger_legs.filter(leg => leg.segment_type !== 'walk');
  const requested = calendarDay(requestedDepartureDate);
  // Route.search_date is the existing per-route calendar used for timetable lookup.
  // The contract has no separate route departure datetime. Unreported rollovers
  // cannot be inferred here; the backend must supply the correct route calendar.
  const departure = calendarDay(route.search_date);
  return {
    direct: noTransfers && rides.length === 1,
    noTransfers,
    departsTomorrow: requested !== undefined && departure !== undefined && departure - requested === 86400000,
  };
}
