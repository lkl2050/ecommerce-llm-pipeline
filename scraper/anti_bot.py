import random
import asyncio
from typing import List, Dict
from playwright.async_api import BrowserContext, Page

class AntiBot:
    """Advanced anti-bot measures for web scraping"""

    # Updated user agents for Firefox
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    VIEWPORT_SIZES = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
        {'width': 1280, 'height': 720},
    ]

    @classmethod
    async def setup_stealth_context(cls, browser) -> BrowserContext:
        """Create a stealth browser context with randomized settings"""
        user_agent = random.choice(cls.USER_AGENTS)
        viewport = random.choice(cls.VIEWPORT_SIZES)

        context = await browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale='en-CA',
            timezone_id='America/Toronto',
            # Randomize screen size
            screen={'width': viewport['width'], 'height': viewport['height']},
            # Add realistic browser features
            java_script_enabled=True,
            accept_downloads=False,
            has_touch=random.choice([True, False]),
            is_mobile=False,
            # Set realistic headers for Firefox
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-CA,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            }
        )

        return context

    @classmethod
    async def human_like_behavior(cls, page: Page):
        """Add human-like behavior to avoid detection"""
        # Random mouse movements
        await page.mouse.move(
            random.randint(100, 800),
            random.randint(100, 600)
        )

        # Random scroll to simulate reading
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # Random delay
        await asyncio.sleep(random.uniform(1, 3))

    @classmethod
    async def handle_captcha_detection(cls, page: Page) -> bool:
        """Detect and handle basic captcha/bot detection"""
        # Check for common bot detection indicators
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            '[class*="captcha"]',
            '[id*="captcha"]',
            'div:has-text("verify you are human")',
            'div:has-text("unusual traffic")',
        ]

        for selector in captcha_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    print(f"Bot detection triggered: {selector}")
                    # Wait longer and try to appear more human
                    await cls.human_like_behavior(page)
                    await asyncio.sleep(random.uniform(5, 10))
                    return True
            except:
                continue

        return False

    @classmethod
    def get_random_delay(cls) -> float:
        """Get random delay between requests"""
        return random.uniform(2, 5)