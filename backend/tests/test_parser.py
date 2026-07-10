from infrastructure.scrapers.parser import RealHtmlParser
from infrastructure.scrapers.dtos import ScrapedRouteDTO
from bs4 import BeautifulSoup

def test_parser_with_html_fixture():
    fixture_html = """
    <html>
        <body>
            <div class="eki_name">大阪</div>
            <div class="icon_midori"></div>
            <div class="platform_info">Platform 4</div>
        </body>
    </html>
    """
    
    parser = RealHtmlParser()
    dtos = parser.parse_routes(fixture_html)
    
    assert len(dtos) == 1
    dto = dtos[0]
    assert dto.departure == "大阪"
    assert dto.platform_info == "Platform 4"
    assert dto.stations[0].has_midori_madoguchi is True
