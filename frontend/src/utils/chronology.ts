import type { DepartureInfo, Route } from '../api/types';

export function datedClock(day: string, time: string): number {
  if (!day || !/^\d{1,2}:\d{2}$/.test(time)) return NaN;
  const [h,m] = time.split(':').map(Number);
  return Date.parse(`${day}T00:00:00+09:00`) + (h * 60 + m) * 60000;
}
export function exactTimes(exact: DepartureInfo, fallbackDate = ''): { departure: number; arrival: number } {
  const day = exact.operating_date || fallbackDate;
  const departure = exact.departure_datetime ? Date.parse(exact.departure_datetime) : datedClock(day,exact.time);
  let arrival = exact.arrival_datetime ? Date.parse(exact.arrival_datetime) : datedClock(day,exact.arrival_time || '');
  if (!exact.arrival_datetime && arrival < departure) arrival += 86400000;
  return { departure, arrival };
}
export function jstDate(value: number): string { return new Date(value + 9 * 3600000).toISOString().slice(0,10); }
export function displayDateTime(value: number): string {
  return Number.isFinite(value) ? new Date(value + 9 * 3600000).toISOString().slice(0,16).replace('T',' ') : '날짜·시각 미확인';
}
export function compatibleDeparture(exact: DepartureInfo, previousArrival: string | number | undefined, margin = 0, fallbackDate = ''): boolean {
  if (previousArrival === undefined) return true;
  const previous = typeof previousArrival === 'string' ? Date.parse(previousArrival) : previousArrival;
  return exactTimes(exact,fallbackDate).departure >= previous + margin * 60000;
}
export function selectExactDeparture(selected: Record<number,DepartureInfo>, index: number, exact: DepartureInfo): Record<number,DepartureInfo> {
  return Object.fromEntries([...Object.entries(selected).filter(([key]) => Number(key) < index), [String(index),exact]]);
}
export function chronologicalJourney(route: Route, selected: Record<number,DepartureInfo>): boolean {
  let previous: number | undefined, previousIndex = -1;
  for (const leg of route.passenger_legs.filter(l => l.segment_type !== 'walk')) {
    const exact = selected[leg.index];
    if (!exact?.arrival_time) return false;
    const margin = route.passenger_legs.slice(previousIndex + 1,leg.index).filter(l => l.segment_type === 'walk')
      .reduce((sum,l) => sum + walkDuration(l),0);
    const times = exactTimes(exact,route.search_date);
    if (!Number.isFinite(times.arrival) || times.arrival < times.departure || !compatibleDeparture(exact,previous,margin,route.search_date)) return false;
    previous = times.arrival; previousIndex = leg.index;
  }
  return previous !== undefined;
}
export function walkDuration(leg: Route['passenger_legs'][number]): number {
  const explicit = leg.duration.match(/^(\d+)m$/);
  if (explicit) return Number(explicit[1]);
  const start=datedClock('2000-01-01',leg.departure_time), end=datedClock('2000-01-01',leg.arrival_time);
  return Number.isFinite(start+end) ? ((end-start+86400000)%86400000)/60000 : 0;
}
