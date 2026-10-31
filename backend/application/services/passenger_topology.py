import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from domain.route import Route
from domain.timetable import DepartureInfo
from domain.journey import canonical_station, station_names_match


class TopologyCompatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    ALTERNATIVE_TOPOLOGY = "ALTERNATIVE_TOPOLOGY"
    NOT_COMPATIBLE = "NOT_COMPATIBLE"


@dataclass(frozen=True)
class SegmentTopologyConstraint:
    origin: str
    segment_destination: str
    required_destination: str
    bypass_destinations: tuple[str, ...]


class PassengerTopologyClassifier:
    """Classifies a train against the passenger actions of an immutable Route."""

    _NO_TRANSFER_ANNOTATION = re.compile(r"\s*【\s*乗換不要\s*】\s*")
    _PREFECTURE_QUALIFIER = re.compile(
        r"\((?:北海道|東京都|京都府|大阪府|.{2,3}県)\)$"
    )

    @classmethod
    def _canonical_station(cls, station_name: str) -> str:
        return canonical_station(station_name or "")

    @classmethod
    def _station_matches(cls, expected: str, actual: str) -> bool:
        return station_names_match(expected, actual)

    @staticmethod
    def _station_name(route: Route, station_index: int) -> str:
        station = route.stations[station_index]
        return station.name_jp or station.name

    @classmethod
    def passenger_transfer_stations(cls, route: Route) -> tuple[str, ...]:
        boundary_count = min(len(route.stations) - 1, len(route.segments))
        return tuple(
            cls._station_name(route, station_index)
            for station_index in range(1, boundary_count)
            if not route.segments[station_index].is_through
        )

    @classmethod
    def constraint_for_segment(
        cls,
        route: Route,
        segment_index: int,
    ) -> SegmentTopologyConstraint:
        if segment_index < 0 or segment_index >= len(route.segments):
            raise ValueError(f"Invalid segment_index {segment_index}")
        if len(route.stations) <= segment_index + 1:
            raise ValueError("Route stations do not align with segments")

        current_leg_end = segment_index
        while (
            current_leg_end + 1 < len(route.segments)
            and route.segments[current_leg_end + 1].is_through
        ):
            current_leg_end += 1

        later_leg_destinations: list[str] = []
        next_leg_start = current_leg_end + 1
        while next_leg_start < len(route.segments):
            next_leg_end = next_leg_start
            while (
                next_leg_end + 1 < len(route.segments)
                and route.segments[next_leg_end + 1].is_through
            ):
                next_leg_end += 1
            later_leg_destinations.append(
                cls._station_name(route, next_leg_end + 1)
            )
            next_leg_start = next_leg_end + 1

        return SegmentTopologyConstraint(
            origin=cls._station_name(route, segment_index),
            segment_destination=cls._station_name(route, segment_index + 1),
            required_destination=cls._station_name(route, current_leg_end + 1),
            bypass_destinations=tuple(later_leg_destinations),
        )

    @classmethod
    def classify(
        cls,
        route: Route,
        segment_index: int,
        departure: DepartureInfo,
    ) -> TopologyCompatibility:
        constraint = cls.constraint_for_segment(route, segment_index)
        raw_stops = departure.metadata.get("stop_sequence", [])
        if not isinstance(raw_stops, list) or not raw_stops:
            if (
                constraint.required_destination == constraint.segment_destination
                and not constraint.bypass_destinations
                and departure.arrival_time
            ):
                return TopologyCompatibility.COMPATIBLE
            return TopologyCompatibility.NOT_COMPATIBLE

        origin_index = next(
            (
                index
                for index, stop in enumerate(raw_stops)
                if cls._station_matches(constraint.origin, str(stop))
            ),
            None,
        )
        if origin_index is None:
            return TopologyCompatibility.NOT_COMPATIBLE

        remaining_stops = [str(stop) for stop in raw_stops[origin_index + 1:]]
        reaches_required_destination = any(
            cls._station_matches(constraint.required_destination, stop)
            for stop in remaining_stops
        )
        if not reaches_required_destination:
            return TopologyCompatibility.NOT_COMPATIBLE

        bypasses_transfer = any(
            cls._station_matches(bypass_destination, stop)
            for bypass_destination in constraint.bypass_destinations
            for stop in remaining_stops
        )
        if bypasses_transfer:
            return TopologyCompatibility.ALTERNATIVE_TOPOLOGY
        return TopologyCompatibility.COMPATIBLE

    @classmethod
    def filter_departures(
        cls,
        route: Route,
        segment_index: int,
        departures: list[DepartureInfo],
    ) -> list[DepartureInfo]:
        compatible_departures = []
        for departure in departures:
            compatibility = cls.classify(route, segment_index, departure)
            if compatibility != TopologyCompatibility.COMPATIBLE:
                continue
            compatible_departures.append(departure.model_copy(update={
                "metadata": {
                    **departure.metadata,
                    "topology_compatibility": compatibility.value,
                }
            }))
        return compatible_departures
