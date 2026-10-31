"""Group provider candidates by passenger structure before assigning categories."""
import hashlib
import re

from domain.journey import family_identity, service_family
from domain.route import Route


def duration_minutes(value: str) -> int | None:
    hours = re.search(r"(\d+)\s*(?:h|時間)", value)
    minutes = re.search(r"(\d+)\s*(?:m|分)", value)
    if not hours and not minutes:
        return None
    return (int(hours[1]) * 60 if hours else 0) + (int(minutes[1]) if minutes else 0)


def clock_minutes(value: str) -> int | None:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
    if not match:
        return None
    return int(match[1]) * 60 + int(match[2])


def group_route_families(routes: list[Route]) -> list[Route]:
    grouped: dict[tuple, Route] = {}
    for route in routes:
        identity = family_identity(route)
        # Legacy adapters without aligned segments cannot prove equivalence.
        key = identity or ("unstructured", route.id)
        if key in grouped:
            previous = grouped[key]
            previous_duration, current_duration = duration_minutes(previous.total_duration), duration_minutes(route.total_duration)
            comparable = previous_duration is not None and current_duration is not None
            arrival_better = bool(route.arrival_time and previous.arrival_time and route.arrival_time <= previous.arrival_time)
            same_arrival = route.arrival_time == previous.arrival_time
            dominates = (comparable and (arrival_better or same_arrival)
                         and current_duration <= previous_duration
                         and route.total_fare <= previous.total_fare
                         and (current_duration < previous_duration or route.total_fare < previous.total_fare
                              or route.arrival_time < previous.arrival_time))
            if not dominates:
                continue
        family_key = hashlib.sha256(repr(key).encode()).hexdigest()[:24]
        rides = [leg for leg in route.passenger_legs if leg.segment_type != "walk"]
        railway_names = [service_family(name) for leg in rides for name in leg.railway_names]
        railway_name = " → ".join(dict.fromkeys(railway_names)) or service_family(route.railway_name)
        if rides and all("新幹線" in n or "shinkansen" in n.lower()
                         for leg in rides for n in leg.railway_names):
            railway_name = "Shinkansen"
        waiting = 0
        complete = len(rides) > 1
        for left, right in zip(rides, rides[1:]):
            arrival, departure = clock_minutes(left.arrival_time), clock_minutes(right.departure_time)
            if arrival is None or departure is None:
                complete = False
                break
            walk_legs = [leg for leg in route.passenger_legs[left.index + 1:right.index] if leg.segment_type == 'walk']
            walks = [duration_minutes(leg.duration) for leg in walk_legs]
            if any(minutes is None for minutes in walks):
                complete = False
                break
            gap = (departure - arrival) % 1440
            if sum(walks) > gap:
                complete = False
                break
            waiting += gap - sum(walks)
        grouped[key] = route.model_copy(update={
            "family_key": family_key,
            "railway_name": railway_name,
            "transfer_count": max(0, len(rides) - 1) if rides else route.transfer_count,
            "waiting_duration": f"{waiting}m" if complete else "",
            "segments": [segment.model_copy(update={"railway_name": service_family(segment.railway_name)}) for segment in route.segments],
        })
    return list(grouped.values())


def categorize_routes(routes: list[Route]) -> list[Route]:
    """Label meaningful trade-offs, retaining distinct paths and passenger topologies."""
    if not routes:
        return []
    durations = [duration_minutes(route.total_duration) for route in routes]
    known_durations = [n for n in durations if n is not None]
    fastest = min(known_durations) if known_durations else None
    cheapest = min(route.total_fare for route in routes if route.total_fare > 0) if any(r.total_fare > 0 for r in routes) else None
    transfers = min(route.transfer_count for route in routes)
    result = []
    for route, duration in zip(routes, durations):
        categories = []
        if duration is not None and duration == fastest:
            categories.append("FASTEST")
        if route.transfer_count == transfers:
            categories.append("FEWEST TRANSFERS")
        if cheapest is not None and route.total_fare == cheapest:
            categories.append("CHEAPEST")
        result.append(route.model_copy(update={"categories": categories}))
    # No dominance pruning across corridors: these are indicative prices and sample
    # departures, not the complete daily timetable of each family.
    return sorted(result, key=lambda r: (duration_minutes(r.total_duration) is None,
                                        duration_minutes(r.total_duration) or 0,
                                        r.transfer_count, r.total_fare))
