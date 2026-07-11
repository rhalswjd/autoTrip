import requests
from bs4 import BeautifulSoup

url = "https://transit.yahoo.co.jp/search/result"
params = {
    "from": "新大阪", "to": "和歌山", "shin": "1", "ex": "1", "hb": "1", "al": "1", 
    "y": "2026", "m": "07", "d": "12", "hh": "10", "m1": "0", "m2": "0", "type": "1"
}
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, params=params, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

routes = soup.select('[id^="route0"]')
print(f"Found {len(routes)} routes")
for r in routes:
    summary = r.select_one('.routeSummary')
    if summary:
        print(summary.text[:100])
