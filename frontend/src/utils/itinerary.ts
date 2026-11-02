import type { DepartureInfo, LegSelection, Route } from '../api/types';
import { exactTimes } from './chronology.ts';

export function operatingMinute(time: string): number {
  const [hours, minutes] = time.split(':').map(Number);
  return (hours < 4 ? hours + 24 : hours) * 60 + minutes;
}

function clock(minute: number): string {
  const value = ((minute % 1440) + 1440) % 1440;
  return String(Math.floor(value / 60)).padStart(2, '0') + ':' + String(value % 60).padStart(2, '0');
}

function difference(departure: string, arrival: string): number {
  return (operatingMinute(arrival) - operatingMinute(departure) + 1440) % 1440;
}

export function itineraryPreview(route: Route, selected: Record<number, DepartureInfo>): Route {
  const rides = route.passenger_legs.filter(leg => leg.segment_type !== 'walk');
  const first = rides[0] && selected[rides[0].index];
  const last = rides.at(-1) && selected[rides.at(-1)!.index];
  const complete = rides.length > 0 && rides.every(leg => selected[leg.index]?.arrival_time);
  const prefixWalk = rides.length > 0 && rides[0].index > 0;
  const suffixWalk = rides.length > 0 && rides.at(-1)!.index < route.passenger_legs.length - 1;
  // Preserve only the discovery provider's measured access/egress estimate.
  // This is labelled as estimated walking, never as an exact train running time.
  const prefix = !prefixWalk ? 0 : route.departure_time && rides[0].departure_time
    ? difference(route.departure_time, rides[0].departure_time) : null;
  const suffix = !suffixWalk ? 0 : route.arrival_time && rides.at(-1)!.arrival_time
    ? difference(rides.at(-1)!.arrival_time, route.arrival_time) : null;
  const dated = Boolean(route.search_date || first?.operating_date || first?.departure_datetime);
  const elapsed = complete && first && last && prefix !== null && suffix !== null ?
    (dated ? (exactTimes(last,route.search_date).arrival-exactTimes(first,route.search_date).departure)/60000 : difference(first.time, last.arrival_time!)) + prefix + suffix : null;
  const onboard = complete ? rides.reduce((sum,leg) => sum + (dated ? (exactTimes(selected[leg.index],route.search_date).arrival-exactTimes(selected[leg.index],route.search_date).departure)/60000 : difference(selected[leg.index].time,selected[leg.index].arrival_time!)),0) : null;
  let waiting: number | null = complete ? 0 : null;
  if (complete) for (let index = 1; index < rides.length; index++) {
    const previous = rides[index - 1], next = rides[index];
    const walks = route.passenger_legs.slice(previous.index + 1, next.index).filter(leg => leg.segment_type === 'walk');
    if (walks.some(leg => !/^\d+m$/.test(leg.duration))) { waiting = null; break; }
    const walk = walks.reduce((sum, leg) => sum + Number(leg.duration.slice(0, -1)), 0);
    const gap = dated ? (exactTimes(selected[next.index],route.search_date).departure-exactTimes(selected[previous.index],route.search_date).arrival)/60000 : difference(selected[previous.index].arrival_time!, selected[next.index].time);
    if (walk > gap) { waiting = null; break; }
    waiting! += gap - walk;
  }
  const exactFares = complete && rides.every(leg => selected[leg.index].fare_status === 'exact');
  return { ...route,
    departure_time: first && prefix !== null ? clock(operatingMinute(first.time) - prefix) : '',
    arrival_time: complete && last && suffix !== null ? clock(operatingMinute(last.arrival_time!) + suffix) : '',
    total_duration: elapsed === null ? '' : `${elapsed}m`,
    onboard_duration: onboard === null ? '' : `${onboard}m`,
    non_riding_duration: elapsed === null || onboard === null || elapsed < onboard ? '' : `${elapsed - onboard}m`,
    waiting_duration: waiting === null ? '' : `${waiting}m`,
    timing_status: !complete ? 'pending' : prefixWalk || suffixWalk ? 'includes_estimated_walking' : 'exact',
    fare_status: exactFares ? 'exact' : 'unknown',
    fare_breakdown: null,
    total_fare: exactFares ? rides.reduce((sum, leg) => sum + (selected[leg.index].base_fare || 0) + (selected[leg.index].express_fare || 0), 0) : 0,
  };
}

export function selectedPassengerLegs(route: Route, selected: Record<number, DepartureInfo>): LegSelection[] {
  return route.passenger_legs.filter(leg => leg.segment_type !== 'walk' && selected[leg.index]).map(leg => {
    const departure = selected[leg.index];
    const numericPlatform = /^\d+$/.test(departure.platform || '') ? Number(departure.platform) : undefined;
    return {
      passenger_leg_index: leg.index, segment_index: leg.raw_segment_indices[0], exact_departure_id: departure.id,
      timetable_date: departure.operating_date || route.search_date,
      departure_datetime: departure.departure_datetime, arrival_datetime: departure.arrival_datetime,
      departure_station: leg.departure_station.name, arrival_station: leg.arrival_station.name,
      departure_time: departure.time, arrival_time: departure.arrival_time,
      transport_name: departure.train_name, railway_name: leg.railway_names.join(' / '),
      platform: numericPlatform,
      base_fare: departure.fare_status === 'exact' ? departure.base_fare ?? undefined : undefined,
      express_fare: departure.fare_status === 'exact' ? departure.express_fare ?? undefined : undefined,
    };
  });
}
