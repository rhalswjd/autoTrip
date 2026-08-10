import urllib.request
import urllib.parse
from html.parser import HTMLParser

class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.div_route_summary_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for name, value in attrs:
                if name == "class" and "routeSummary" in value:
                    self.div_route_summary_count += 1

def run():
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
    qs = urllib.parse.urlencode(params)
    url = f"https://transit.yahoo.co.jp/search/result?{qs}"
    
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        
    print(f"HTML size: {len(html)}")
    
    parser = SimpleHTMLParser()
    parser.feed(html)
    print(f"route_item count (div.routeSummary): {parser.div_route_summary_count}")

if __name__ == "__main__":
    run()
