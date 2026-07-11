import requests
from bs4 import BeautifulSoup
import re

url = "https://transit.yahoo.co.jp/search/result"
params = {"from": "東京", "to": "大阪"}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

response = requests.get(url, params=params, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"URL: {response.url}")

soup = BeautifulSoup(response.text, 'html.parser')

routes = soup.select('[id^="route0"]')
print(f"Found {len(routes)} routes")

for route_div in routes[:3]:
    summary = route_div.select_one('.routeSummary')
    if summary:
        print("Summary text:", summary.text[:100])
    detail = route_div.select_one('.routeDetail')
    if detail:
        stations = [dt.text.strip() for dt in detail.select('.station dt') if dt.text.strip()]
        trains = [t.text.strip() for t in detail.select('.transport div') if t.text.strip()]
        print("Stations:", stations)
        print("Trains:", trains)
    else:
        print("No routeDetail found")

