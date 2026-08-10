import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json

def fetch_yahoo(dep, arr):
    url = "https://transit.yahoo.co.jp/search/result"
    params = {
        "from": dep,
        "to": arr,
        "type": "1",
        "ticket": "ic",
        "expkind": "1",
        "ws": "3",
        "s": "0",
        "y": "2024",
        "m": "10",
        "d": "01",
    }
    qs = urllib.parse.urlencode(params)
    full_url = f"{url}?{qs}"
    req = urllib.request.Request(full_url, headers={
        "User-Agent": "Mozilla/5.0",
    })
    
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode('utf-8')

def test():
    # 1. Fetch with Shin-Osaka (English)
    html_en = fetch_yahoo("Shin-Osaka", "Hiroshima")
    soup_en = BeautifulSoup(html_en, 'html.parser')
    
    with open("yahoo_en.html", "w") as f:
        f.write(html_en)
        
    print("=== English Names (Shin-Osaka -> Hiroshima) ===")
    print("Title:", soup_en.title.text if soup_en.title else None)
    route_items = soup_en.select("div.routeSummary")
    print("route_item count (div.routeSummary):", len(route_items))
    
    # 2. Fetch with Japanese
    html_jp = fetch_yahoo("新大阪", "広島")
    soup_jp = BeautifulSoup(html_jp, 'html.parser')
    
    with open("yahoo_jp.html", "w") as f:
        f.write(html_jp)
        
    print("\n=== Japanese Names (新大阪 -> 広島) ===")
    print("Title:", soup_jp.title.text if soup_jp.title else None)
    route_items_jp = soup_jp.select("div.routeSummary")
    print("route_item count (div.routeSummary):", len(route_items_jp))

if __name__ == "__main__":
    test()
