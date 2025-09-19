from playwright.async_api import async_playwright
from typing import Dict, Optional

class PlaywrightParser:
    async def parse_product(self, url: str) -> Optional[Dict]:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            
            # Ждем загрузки контента
            await page.wait_for_selector('[data-price]')
            
            return {
                'title': await page.text_content('h1'),
                'price': await page.text_content('[data-price]'),
                'availability': await page.is_visible('[data-in-stock]')
            }