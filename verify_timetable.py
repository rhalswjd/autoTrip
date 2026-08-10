import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlencode

async def run_test():
    url = "https://transit.yahoo.co.jp/search/result"
    params = {
        "from": "新大阪",
        "to": "広島",
        "type": "1",
        "ticket": "ic",
        "expkind": "1",
        "ws": "3",
        "s": "0",
        "y": "2024",
        "m": "10",
        "d": "01",
    }
    qs = urlencode(params)
    full_url = f"{url}?{qs}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    print("1. Downloader.fetch_html() URL Test:")
    print(f"Requesting URL: {full_url}")
    
    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        response = await client.get(full_url)
        print(f"Final response.url: {response.url}")
        print(f"response.history (Redirects): {response.history}")
        html = response.text
        
    # 2. HTML title
    print("\n2. HTML Title:")
    soup = BeautifulSoup(html, 'html.parser')
    print(soup.title.text if soup.title else "No Title")
    
    # 3. Parser element counts
    print("\n3. Parser Element Counts:")
    selectors = {
        "route_item": "div.routeSummary",
        "departure_time": "li.time > span:nth-of-type(1)",
        "arrival_time": "li.time > span:nth-of-type(2)",
        "train_name": "ul.transport > li > span.mark",
        "direction": "span.dest"
    }
    
    for name, sel in selectors.items():
        count = len(soup.select(sel))
        print(f"Selector for {name} ({sel}): {count} elements found")
        
    # 4 & 5. Analysis
    print("\n4. Conclusion:")
    print("The HTML being parsed is the Route Search result page (search/result), not the Station Timetable page (timetable).")

if __name__ == "__main__":
    asyncio.run(run_test())
