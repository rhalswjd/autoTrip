import asyncio
import sys
import os
import sqlite3
import json
import httpx

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from application.services.search_service import SearchService
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.services.translation_service import TranslationService
from domain.search import SearchRequest

original_search = YahooTransitAdapter.search_routes
yahoo_data = {}

async def patched_search(self, departure, arrival, time=None, date=None):
    from urllib.parse import urlencode
    from bs4 import BeautifulSoup
    import re
    
    params = {
        'from': departure,
        'to': arrival,
        'shin': '1', 'ex': '1', 'hb': '1', 'al': '1', 'type': '5'
    }
    url = f"https://transit.yahoo.co.jp/search/result?{urlencode(params)}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        routes_data = []
        results = soup.select('.routeSummary')
        for r in results:
            time_text = r.select_one('.time').text if r.select_one('.time') else ""
            
            ride_match = re.search(r'乗車\s*([0-9]+時間[0-9]+分|[0-9]+分)', time_text)
            if ride_match:
                duration = ride_match.group(1)
            else:
                duration_match = re.search(r'着(.+?)（', time_text)
                duration = duration_match.group(1) if duration_match else "0 min"
                if duration == "0 min":
                    dur_match = re.search(r'([0-9]+時間[0-9]+分|[0-9]+分)', time_text)
                    if dur_match:
                        duration = dur_match.group(1)
            
            routes_data.append({
                "html": time_text,
                "final": duration.replace('時間', 'h ').replace('分', 'm').strip()
            })
        
        yahoo_data[f"{departure}_{arrival}"] = {
            "url": url,
            "routes": routes_data
        }
            
    return await original_search(self, departure, arrival, time, date)

YahooTransitAdapter.search_routes = patched_search

def trace_translation(jp_name: str) -> str:
    ts = TranslationService()
    clean_name = ts._hyphenate_prefix(jp_name)
    clean_name = jp_name.replace('(', '').replace(')', '').strip()
    
    if clean_name in ts._station_map:
        return "POI/Hardcoded override"
        
    if os.path.exists(ts.db_path):
        with sqlite3.connect(ts.db_path) as conn:
            cursor = conn.execute("SELECT name_en FROM stations WHERE name_jp = ? LIMIT 1", (clean_name,))
            if cursor.fetchone():
                return "Station DB"
                
    from infrastructure.repositories.sqlite_bus_stop_repository import SqliteBusStopRepository
    bus_repo = SqliteBusStopRepository()
    if bus_repo.get_english_name(jp_name):
        return "Bus Stop DB"
        
    return "Fallback (Original)"

async def main():
    repo = SqliteStationRepository(db_path="/app/backend/autotrip_stations.db")
    scraper = YahooTransitAdapter()
    cache = FakeCacheAdapter()
    service = SearchService(scraper, cache, repo)
    
    tests = [
        ("Shin-Osaka", "Osaka"),
        ("Shin-Osaka", "Nagoya"),
        ("Tokyo", "Shin-Osaka"),
        ("Universal Studios Japan", "Kyoto"),
        ("Kansai Airport", "Osaka")
    ]
    
    for dep, arr in tests:
        print(f"\n=======================")
        print(f"Request: {dep} -> {arr}")
        print(f"=======================")
        
        dep_jp = await service._get_jp_name(dep)
        arr_jp = await service._get_jp_name(arr)
        
        routes = await service.search(SearchRequest(departure_station=dep, arrival_station=arr))
        
        y_data = yahoo_data.get(f"{dep_jp}_{arr_jp}", {"url": "N/A", "routes": []})
        print(f"[Yahoo URL] {y_data['url']}")
        
        if len(routes) > 0:
            first_r = routes[0]
            print(f"\n[Parser Info for Best Route]")
            print(f"Original HTML .time : {y_data['routes'][0]['html'] if y_data['routes'] else 'N/A'}")
            print(f"Calculated Duration : {first_r.total_duration}")
            
            print(f"\n[Translation Layer]")
            print(f"Departure ({first_r.departure_station}): {trace_translation(first_r.departure_station)}")
            print(f"Arrival ({first_r.arrival_station}): {trace_translation(first_r.arrival_station)}")
            
            print(f"\n[Response (Route 1)]")
            try:
                print(json.dumps(first_r.model_dump(), indent=2, ensure_ascii=False))
            except AttributeError:
                print(first_r)
        else:
            print("No routes found.")

    print("\n\n=======================")
    print("POI DB Structure and Data")
    print("=======================")
    with sqlite3.connect("/app/backend/autotrip_poi.db") as conn:
        print("[Schema]")
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pois'")
        print(cursor.fetchone()[0])
        print("\n[Sample Data]")
        cursor = conn.execute("SELECT * FROM pois LIMIT 5")
        for row in cursor.fetchall():
            print(row)

if __name__ == "__main__":
    asyncio.run(main())
