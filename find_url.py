import asyncio
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

async def find_timetable_url(dep, arr):
    # 1. Get station timetable list
    search_url = f"https://transit.yahoo.co.jp/timetable/search?q={urllib.parse.quote(dep)}"
    req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req) as r:
        html = r.read().decode("utf-8")
        
    soup = BeautifulSoup(html, "html.parser")
    
    # 2. Find the correct line
    for a in soup.select(".elmSearchResult a"):
        # The links might be under .elmSearchResult or similar
        pass
        
    # Let's just find any 'a' tag that contains the arrival station
    for a in soup.select("a"):
        if "timetable" in a.get("href", "") and arr in a.text:
            return f"https://transit.yahoo.co.jp{a['href']}"
            
    return None

def test():
    url = asyncio.run(find_timetable_url("新大阪", "広島"))
    print("Found URL:", url)

if __name__ == "__main__":
    test()
