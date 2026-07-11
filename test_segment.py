import requests
from bs4 import BeautifulSoup

url = "https://transit.yahoo.co.jp/search/result"
params = {
    "from": "新大阪", "to": "和歌山", "shin": "1", "ex": "1", "hb": "1", "al": "1", 
    "type": "5", "s": "1" # s=1 is usually local/cheap
}
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, params=params, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

routes = soup.select('[id^="route0"]')
print(f"Found {len(routes)} routes")
for r in routes:
    detail = r.select_one('.routeDetail')
    if detail:
        print("\n--- Route Detail ---")
        station_names = [dt.text.strip() for dt in detail.select('.station dt') if dt.text.strip()]
        
        trains = []
        for t in detail.select('.transport'):
            div = t.select_one('div')
            if div:
                # remove .small or .destination text
                for cls in ['.small', '.destination']:
                    elem = div.select_one(cls)
                    if elem:
                        elem.decompose()
                trains.append(div.text.strip())
        
        print("Stations:", station_names)
        print("Trains:", trains)
