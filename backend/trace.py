import httpx
from bs4 import BeautifulSoup
import re
import sys

def trace_route(dep, arr):
    print(f"\n{'='*50}")
    print(f"TRACING ROUTE: {dep} -> {arr}")
    print(f"{'='*50}")
    
    url = "https://transit.yahoo.co.jp/search/result"
    params = {
        "from": dep,
        "to": arr,
        "shin": "1",
        "ex": "1",
        "hb": "1",
        "al": "1",
        "type": "5"
    }
    
    print("1) REQUEST URL:")
    req = httpx.Request('GET', url, params=params)
    print(req.url)
    
    print("\n2) KEYWORDS SENT TO YAHOO:")
    print(f"Departure Keyword: {dep}")
    print(f"Arrival Keyword: {arr}")
    
    client = httpx.Client(follow_redirects=True)
    resp = client.get(url, params=params)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    print("\n3) YAHOO HTML ACTUAL RESOLUTION (出発/到着 Text):")
    display_info = soup.select_one('.labelRoute')
    if display_info:
        print(display_info.text.strip())
    else:
        print("Not found .labelRoute. Searching for title...")
        title = soup.title.string if soup.title else ""
        print(f"Title: {title}")
    
    route1 = soup.select_one('#route01')
    if route1:
        print("\n4) PARSER SELECTOR TARGETS:")
        summary = route1.select_one('.routeSummary')
        
        time_elem = summary.select_one('.time')
        print(f"Selector '.time' content: {time_elem.text.strip() if time_elem else 'Not found'}")
        
        fare_elem = summary.select_one('.fare')
        print(f"Selector '.fare' content: {fare_elem.text.strip() if fare_elem else 'Not found'}")
        
        print("\n5) DURATION EXTRACTION LOGIC:")
        time_text = time_elem.text if time_elem else ""
        print(f"Raw time_text: {time_text}")
        
        duration_match = re.search(r'着(.+?)（', time_text)
        duration = duration_match.group(1) if duration_match else "0 min"
        if duration == "0 min":
            dur_match = re.search(r'([0-9]+時間[0-9]+分|[0-9]+分)', time_text)
            if dur_match:
                duration = dur_match.group(1)
        print(f"Extracted Duration by Parser: {duration}")
        
        print("\n6) STOPS / TRANSFER COUNT EXTRACTION LOGIC:")
        fare_text = fare_elem.text if fare_elem else summary.text
        print(f"Text used for transfer parsing: {fare_text}")
        transfer_match = re.search(r'乗換：(\d+)回', fare_text) if not fare_elem else re.search(r'乗換：(\d+)回', summary.text)
        transfers = int(transfer_match.group(1)) if transfer_match else 0
        print(f"Extracted Transfer Count (UI calls this 'Stops'): {transfers}")
        
        print("\n7) TRANSLATION SERVICE VALUES:")
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from infrastructure.services.translation_service import TranslationService
        ts = TranslationService()
        
        detail = route1.select_one('.routeDetail')
        station_names = [dt.text.strip() for dt in detail.select('.station dt') if dt.text.strip()]
        print("Yahoo Original Stations:", station_names)
        
        print("Translation Output:")
        for s in station_names:
            en = ts.get_english_name(s)
            print(f"  {s} -> {en}")
            
        print("\n8) FINAL API RESPONSE FRAGMENT:")
        print(f"departure_station: {ts.get_english_name(station_names[0]) if station_names else dep}")
        print(f"arrival_station: {ts.get_english_name(station_names[-1]) if station_names else arr}")
        print(f"total_duration: {duration.replace('時間', 'h ').replace('分', 'm').strip()}")
        print(f"transfer_count (Stops in UI): {transfers}")
        
    else:
        print("No route found in HTML.")

trace_route("Shin-Osaka", "Osaka")
trace_route("Shin-Osaka", "Nagoya")
trace_route("新大阪", "大阪")
trace_route("新大阪", "名古屋")
