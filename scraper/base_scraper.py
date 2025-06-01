import asyncio
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright, Page, BrowserContext
from abc import ABC, abstractmethod
from datetime import datetime
import random

from .anti_bot import AntiBot
from api.models import Product

class BaseScraper(ABC):
    """Enhanced base scraper with infinite scroll and anti-bot measures"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.anti_bot = AntiBot()

    async def infinite_scroll(self, page: Page, max_scrolls: int = 10) -> bool:
        """Handle infinite scroll pages to load more content"""
        print("Handling infinite scroll...")

        previous_height = await page.evaluate("document.body.scrollHeight")
        scrolls_performed = 0

        for scroll_attempt in range(max_scrolls):
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Wait for content to load
            await asyncio.sleep(random.uniform(2, 4))

            # Check if new content loaded
            current_height = await page.evaluate("document.body.scrollHeight")

            # Look for loading indicators
            loading_selectors = [
                '[data-automation="loading"]',
                '.loading',
                '.spinner',
                '[class*="load"]'
            ]

            # Wait for loading to complete
            for selector in loading_selectors:
                try:
                    await page.wait_for_selector(selector, state='detached', timeout=3000)
                except:
                    continue

            if current_height == previous_height:
                # No new content loaded, try clicking "Load More" button if exists
                load_more_selectors = [
                    'button:has-text("Load More")',
                    'button:has-text("Show More")',
                    '[data-automation="load-more"]',
                    '.load-more-button'
                ]

                loaded_more = False
                for selector in load_more_selectors:
                    try:
                        button = await page.query_selector(selector)
                        if button and await button.is_visible():
                            await button.click()
                            await asyncio.sleep(random.uniform(2, 3))
                            loaded_more = True
                            break
                    except:
                        continue

                if not loaded_more:
                    print(f"Infinite scroll complete after {scrolls_performed} scrolls")
                    break

            previous_height = current_height
            scrolls_performed += 1

            # Human-like behavior between scrolls
            await self.anti_bot.human_like_behavior(page)

        return scrolls_performed > 0

    async def wait_for_dynamic_content(self, page: Page, timeout: int = 15000):
        """Wait for dynamic content to fully load"""
        try:
            # Wait for network to be idle
            await page.wait_for_load_state('networkidle', timeout=timeout)

            # Wait for specific content indicators
            content_selectors = [
                '[data-automation="product-item"]',
                '.product-item',
                '.product-card',
                '[class*="product"]'
            ]

            for selector in content_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except:
                    continue

        except Exception as e:
            print(f"Dynamic content loading timeout: {str(e)}")

    @abstractmethod
    async def scrape_category(self, category_url: str, max_products: int) -> List[Product]:
        """Abstract method for scraping a specific category"""
        pass

    async def scrape_with_retries(self, url: str, max_retries: int = 3) -> Optional[Page]:
        """Scrape with retry logic and bot detection handling"""
        async with async_playwright() as p:
            # Use Firefox instead of Chromium
            browser = await p.firefox.launch(headless=self.headless)

            for attempt in range(max_retries):
                try:
                    # Create stealth context
                    context = await self.anti_bot.setup_stealth_context(browser)
                    page = await context.new_page()

                    # Navigate with realistic timing
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    # Check for bot detection
                    if await self.anti_bot.handle_captcha_detection(page):
                        if attempt < max_retries - 1:
                            print(f"Retry attempt {attempt + 1} due to bot detection")
                            await context.close()
                            await asyncio.sleep(random.uniform(10, 20))
                            continue
                        else:
                            print("Max retries reached, bot detection not resolved")
                            await browser.close()
                            return None

                    # Wait for dynamic content
                    await self.wait_for_dynamic_content(page)

                    return page

                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(self.anti_bot.get_random_delay())
                    continue

            await browser.close()
            return None