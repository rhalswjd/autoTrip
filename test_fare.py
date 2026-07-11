import requests
from bs4 import BeautifulSoup
import re

url = "https://transit.yahoo.co.jp/search/result"
params = {
    "from": "名古屋", "to": "東京", "shin": "1", "ex": "1", "hb": "1", "al": "1", 
    "type": "5"
}
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, params=params, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

routes = soup.select('[id^="route0"]')
for r in routes:
    fare_elem = r.select_one('.fare')
    if fare_elem:
        fare_text = fare_elem.text
        fare_match = re.search(r'([0-9,]+)円', fare_text)
        print("Fare text:", fare_text)
        print("Regex match:", fare_match.group(1))
