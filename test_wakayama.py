import requests
from bs4 import BeautifulSoup
import re

url = "https://transit.yahoo.co.jp/search/result"
headers = {'User-Agent': 'Mozilla/5.0'}

def test_query(params, name):
    print(f"\n--- {name} ---")
    response = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    routes = soup.select('[id^="route0"]')
    print(f"URL: {response.url}")
    print(f"Found {len(routes)} routes")
    for r in routes:
        summary = r.select_one('.routeSummary')
        if summary:
            print(summary.text[:100])

# Test 1: Default
test_query({"from": "新大阪", "to": "和歌山", "shin": "1", "ex": "1", "hb": "1", "al": "1", "s": "0"}, "Default with s=0")

# Test 2: With type=1 (Departure) and y=2024, m=10, d=10, hh=10, m1=0, m2=0
test_query({
    "from": "新大阪", "to": "和歌山", "shin": "1", "ex": "1", "hb": "1", "al": "1", 
    "y": "2026", "m": "07", "d": "12", "hh": "10", "m1": "0", "m2": "0", "type": "1"
}, "10 AM Departure (No s=0)")

# Test 3: No s=0 at all for default time
test_query({"from": "新大阪", "to": "和歌山", "shin": "1", "ex": "1", "hb": "1", "al": "1"}, "Default without s=0")

