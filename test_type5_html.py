import requests
from bs4 import BeautifulSoup

url = "https://transit.yahoo.co.jp/search/result"
params = {
    "from": "新大阪", "to": "和歌山", "shin": "1", "ex": "1", "hb": "1", "al": "1", 
    "type": "5"
}
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, params=params, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

r = soup.select_one('#route01')
summary = r.select_one('.routeSummary')
print(summary.encode())
