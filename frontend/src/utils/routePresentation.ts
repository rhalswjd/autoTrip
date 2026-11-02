import type { Route } from '../api/types';

export type RouteSort = 'time' | 'transfers' | 'fare';
export function durationMinutes(value: string): number {
  const hours = value.match(/(\d+)h/), minutes = value.match(/(\d+)m/);
  return hours || minutes ? Number(hours?.[1] || 0) * 60 + Number(minutes?.[1] || 0) : Infinity;
}
export function sortRoutes(routes: Route[], sort: RouteSort): Route[] {
  const fare = (r: Route) => r.fare_status === 'unknown' || !r.total_fare ? Infinity : r.total_fare;
  return [...routes].sort((a, b) => (sort === 'fare' ? fare(a) - fare(b) :
    sort === 'transfers' ? a.transfer_count - b.transfer_count : 0) ||
    durationMinutes(a.total_duration) - durationMinutes(b.total_duration));
}
export const routeSections = [
  { kind: 'requested', title: 'Departing around your requested time' },
  { kind: 'daily_alternative', title: 'Other direct services on this date' },
  { kind: 'later_practical', title: 'Later, simpler option' },
] as const;
