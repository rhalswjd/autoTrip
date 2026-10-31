"""Small opt-in real-provider smoke. Never writes to Notion."""
import argparse
import asyncio
import json

import httpx

from application.services.search_service import SearchService
from application.services.timetable_service import TimetableService
from domain.search import SearchRequest
from infrastructure.adapters.transport_scraper import TransportScraperAdapter
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository
from infrastructure.scrapers.timetable.odekake_downloader import JROdekakeDownloader
from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter


async def run(args):
    cache = FakeCacheAdapter()
    yahoo = YahooTimetableScraper()
    downloader = JROdekakeDownloader(cache)
    adapter = TransportScraperAdapter(YahooTransitAdapter(yahoo), JROdekakeTimetableScraper(downloader), yahoo)
    requests = {"total": 0, "redirects": 0, "429": 0}
    original_send = httpx.AsyncClient.send

    async def counted_send(client, request, **kwargs):
        if requests["429"]:
            raise RuntimeError("Live smoke stopped after HTTP 429")
        response = await original_send(client, request, **kwargs)
        requests["total"] += 1 + len(response.history)
        requests["redirects"] += len(response.history)
        if response.status_code == 429:
            requests["429"] += 1
            raise RuntimeError("Live smoke stopped after HTTP 429")
        return response

    httpx.AsyncClient.send = counted_send
    result = {"query": vars(args)}
    try:
        service = SearchService(adapter, cache, SqliteStationRepository())
        routes = await service.search(SearchRequest(departure_station=args.origin,
            arrival_station=args.destination, departure_date=args.date, departure_time=args.time))
        result["families"] = [{"id": r.id, "name": r.railway_name, "family": r.family_key,
            "source": r.search_source, "rank": r.source_rank,
            "legs": [[leg.departure_station.name_jp, leg.arrival_station.name_jp] for leg in r.passenger_legs],
            "elapsed": r.total_duration, "onboard": r.onboard_duration, "waiting": r.waiting_duration}
            for r in routes]
        selected = next((r for r in routes if args.service in r.railway_name), None)
        if selected and args.timetable:
            timetable_service = TimetableService(adapter, cache)
            for leg in selected.passenger_legs:
                if leg.segment_type == "walk":
                    continue
                timetable = await timetable_service.get_leg_timetable(selected.id, leg.index)
                exact = timetable.selected_departures()
                result.setdefault("timetables", []).append({"leg": leg.index, "source": timetable.source,
                    "calendar": timetable.selected_calendar, "count": len(exact), "complete": timetable.complete,
                    "next_cursor": timetable.next_cursor, "candidates": timetable.total_candidates,
                    "examples": [{"train": d.train_name, "departure": d.time, "arrival": d.arrival_time,
                                  "platform": d.platform, "arrival_platform": d.arrival_platform} for d in exact[:3]]})
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        httpx.AsyncClient.send = original_send
        await yahoo.client.aclose()
    result["requests"] = requests
    result["official_cache_hits"] = downloader.cache_hits
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if "error" in result or requests["429"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--time", default="06:00")
    parser.add_argument("--service", default="")
    parser.add_argument("--timetable", action="store_true")
    asyncio.run(run(parser.parse_args()))
