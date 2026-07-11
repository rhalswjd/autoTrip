import requests
from bs4 import BeautifulSoup
import asyncio
import httpx

async def fetch_routes(s_val):
    url = "https://transit.yahoo.co.jp/search/result"
    params = {
        "from": "新大阪", "to": "和歌山", "shin": "1", "ex": "1", "hb": "1", "al": "1", 
        "type": "5"
    }
    if s_val is not None:
        params["s"] = str(s_val)
        
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        soup = BeautifulSoup(response.text, 'html.parser')
        routes = soup.select('[id^="route0"]')
        print(f"s={s_val} found {len(routes)} routes")
        for r in routes:
            summary = r.select_one('.routeSummary')
            if summary:
                print(f" [s={s_val}]", summary.text[:60])

async def main():
    await asyncio.gather(
        fetch_routes(None),
        fetch_routes(0),
        fetch_routes(1),
        fetch_routes(2)
    )

asyncio.run(main())
