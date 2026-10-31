"""Passenger actions and railway identity, without provider or UI dependencies."""
import re
import unicodedata
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from domain.station import Station

if TYPE_CHECKING:
    from domain.route import Route


def canonical_station(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s*【\s*乗換不要\s*】\s*", "", value)
    # Provider entity-type annotations are not part of a railway station's name.
    # Keep geographic/operator qualifiers, which may distinguish homonymous stops.
    return re.sub(r"\(鉄道\)$", "", value).strip()


def unqualified_station_name(value: str) -> str:
    return re.sub(r'\((?:北海道|東京都|京都府|大阪府|.{2,3}県)\)$', '', canonical_station(value))


def station_names_match(expected: str, actual: str) -> bool:
    expected, actual = canonical_station(expected), canonical_station(actual)
    if expected == actual:
        return True
    left, right = unqualified_station_name(expected), unqualified_station_name(actual)
    if left != expected and right != actual:
        return False  # Explicitly different regions must not collapse.
    return left == right


def service_family(value: str) -> str:
    """Remove exact train number and annotations, retaining railway/service identity."""
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[（(][^()（）]*[）)]", "", value)
    value = re.sub(r"\d+\s*号", "", value)
    value = re.sub(r"\s+\d+\s*$", "", value)
    return value.strip()


def corridor_identity(value: str) -> str:
    value = service_family(value)
    if "新幹線" in value:
        value = value[:value.index("新幹線") + len("新幹線")]
    elif "shinkansen" in value.lower():
        value = value[:value.lower().index("shinkansen") + len("shinkansen")]
    return re.sub(r"\s+", "", value).casefold()


def elapsed_minutes(departure: str, arrival: str) -> int | None:
    if not re.fullmatch(r'\d{1,2}:\d{2}', departure) or not re.fullmatch(r'\d{1,2}:\d{2}', arrival):
        return None
    start_h, start_m = map(int, departure.split(':'))
    end_h, end_m = map(int, arrival.split(':'))
    return ((end_h - start_h) * 60 + end_m - start_m) % 1440


def shift_time(value: str, offset: int) -> str:
    hours, minutes = map(int, value.split(':'))
    result = (hours * 60 + minutes + offset) % 1440
    return f'{result // 60:02}:{result % 60:02}'


class PassengerLeg(BaseModel):
    """One continuous vehicle ride (or walk), potentially across railway boundaries."""
    model_config = ConfigDict(frozen=True)
    index: int
    raw_segment_indices: list[int]
    departure_station: Station
    arrival_station: Station
    segment_type: str
    railway_names: list[str]
    railway_names_jp: list[str]
    through_boundaries: list[Station] = []
    has_seat_selection: bool = False
    departure_time: str = ""
    arrival_time: str = ""
    duration: str = ""


def passenger_legs(route: "Route") -> list[PassengerLeg]:
    if len(route.stations) < len(route.segments) + 1:
        return []
    groups: list[list[int]] = []
    for index, segment in enumerate(route.segments):
        through = (index > 0 and segment.is_through
                   and segment.segment_type == "train"
                   and route.segments[index - 1].segment_type == "train")
        if through:
            groups[-1].append(index)
        else:
            groups.append([index])
    result = []
    for index, group in enumerate(groups):
        segments = [route.segments[i] for i in group]
        start, end = group[0], group[-1]
        departure_time = segments[0].departure_time or (route.departure_time if start == 0 else '')
        arrival_time = segments[-1].arrival_time or (route.arrival_time if end == len(route.segments) - 1 else '')
        minutes = elapsed_minutes(departure_time, arrival_time)
        result.append(PassengerLeg(
            index=index, raw_segment_indices=group,
            departure_station=route.stations[start], arrival_station=route.stations[end + 1],
            segment_type=segments[0].segment_type,
            railway_names=list(dict.fromkeys(service_family(s.railway_name) for s in segments)),
            railway_names_jp=list(dict.fromkeys(service_family(s.railway_name_jp) for s in segments)),
            through_boundaries=[route.stations[i] for i in group[1:]],
            has_seat_selection=any(s.has_seat_selection for s in segments),
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration=segments[0].duration or (f'{minutes}m' if minutes is not None else '') if len(segments) == 1 else '',
        ))
    return result


def family_identity(route: "Route") -> tuple:
    """Ordered passenger actions and corridors; exact train/timing/fare are excluded."""
    return tuple((
        canonical_station(leg.departure_station.name_jp or leg.departure_station.name),
        canonical_station(leg.arrival_station.name_jp or leg.arrival_station.name),
        leg.segment_type,
        tuple(dict.fromkeys(corridor_identity(name) for name in
                            (leg.railway_names_jp if any(leg.railway_names_jp) else leg.railway_names))),
    ) for leg in route.passenger_legs)
