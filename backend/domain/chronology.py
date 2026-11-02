"""Civil JST chronology. A small clock is never implicitly tomorrow."""
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def dated_clock(day: str, clock: str) -> datetime:
    hours, minutes = map(int, clock.split(':'))
    if not 0 <= hours < 48 or not 0 <= minutes < 60:
        raise ValueError('Invalid departure clock')
    return datetime.fromisoformat(day).replace(tzinfo=JST) + timedelta(hours=hours, minutes=minutes)


def exact_datetimes(exact, fallback_date: str):
    day = exact.operating_date or fallback_date
    departure = datetime.fromisoformat(exact.departure_datetime) if exact.departure_datetime else dated_clock(day, exact.time)
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=JST)
    if not exact.arrival_time:
        return departure, None
    arrival = datetime.fromisoformat(exact.arrival_datetime) if exact.arrival_datetime else dated_clock(day, exact.arrival_time)
    if arrival.tzinfo is None:
        arrival = arrival.replace(tzinfo=JST)
    if not exact.arrival_datetime and arrival < departure:
        arrival += timedelta(days=1)
    return departure, arrival


def stamp_departure(exact, day: str):
    departure, arrival = exact_datetimes(exact, day)
    return exact.model_copy(update={'departure_datetime': departure.isoformat(),
        'arrival_datetime': arrival.isoformat() if arrival else '', 'operating_date': exact.operating_date or day})
