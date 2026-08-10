from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

class JROdekakeDownloader:
    """
    Playwright를 사용하여 JR Odekake의 403 WAF를 우회하여 HTML을 다운로드합니다.
    """
    async def fetch_html(self, url: str) -> str:
        from playwright_stealth import Stealth
        logger.info(f"[JROdekakeDownloader] Start Playwright fetching: {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            response = await page.goto(url, wait_until="networkidle")
            logger.info(f"[JROdekakeDownloader] Playwright Response Status: {response.status if response else 'None'}")
            html = await page.content()
            await browser.close()
            return html

    async def fetch_htmls(self, urls: dict[str, str]) -> dict[str, str]:
        from playwright_stealth import Stealth
        logger.info(f"[JROdekakeDownloader] Start Playwright fetching multiple URLs: {list(urls.values())}")
        
        results = {}
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            for key, url in urls.items():
                logger.info(f"[JROdekakeDownloader] Fetching {key}: {url}")
                response = await page.goto(url, wait_until="networkidle")
                logger.info(f"[JROdekakeDownloader] Playwright Response Status for {key}: {response.status if response else 'None'}")
                results[key] = await page.content()
                
            await browser.close()
            return results
