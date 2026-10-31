"""Shared deterministic domain factories; never contact external providers."""
from domain.route import Route, RouteSegment
from domain.station import Station


def journey(names: list[str], trains: list[str], through: list[bool] | None = None, **updates) -> Route:
    return Route(
        id=updates.pop("id", "route"), departure_station=names[0],
        arrival_station=names[-1], railway_name=trains[0], total_duration="1h",
        total_fare=1000, transfer_count=len(trains) - 1, polyline="display only",
        search_date="2026-10-31", search_time="06:00",
        stations=[Station(name=n, name_jp=n) for n in names],
        segments=[RouteSegment(segment_type="train", railway_name=t,
                               railway_name_jp=t, is_through=(through or [False] * len(trains))[i])
                  for i, t in enumerate(trains)], **updates,
    )
