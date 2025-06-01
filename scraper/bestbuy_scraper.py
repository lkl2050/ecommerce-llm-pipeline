import asyncio
from typing import List, Optional
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.anti_bot import AntiBot
from api.models import Product
from config import Config

class EnhancedBestBuyCanadaScraper:
    """Enhanced Best Buy Canada scraper using Firefox"""

    def __init__(self):
        self.base_url = "https://www.bestbuy.ca"
        self.config = Config()
        self.anti_bot = AntiBot()
        self.headless = True

    async def scrape_products(self, max_products: int = 20) -> List[Product]:
        """Scrape tv products"""
        laptops_url = f"{self.base_url}/en-ca/category/laptops/20352"
        return await self.scrape_category(laptops_url, max_products)

    async def scrape_category(self, category_url: str, max_products: int) -> List[Product]:
        """Scrape products from a category page"""
        from playwright.async_api import async_playwright

        products = []

        async with async_playwright() as p:
            browser = None
            try:
                print(f"Starting Firefox scraper for {category_url}")

                # Launch Firefox with safe settings
                browser = await p.firefox.launch(headless=self.headless)

                # Create context with stealth settings
                context = await self.anti_bot.setup_stealth_context(browser)
                page = await context.new_page()

                print(f"Navigating to: {category_url}")

                # Navigate with proper timeout
                await page.goto(category_url, wait_until="domcontentloaded", timeout=30000)

                # Wait for page to load
                await asyncio.sleep(3)

                # Check if page loaded correctly
                title = await page.title()
                print(f"Page title: {title}")

                if "best buy" not in title.lower():
                    print("Page doesn't seem to be Best Buy")
                    return []

                # Wait for products to load
                print("Waiting for products to load...")

                # Try multiple selectors for product containers
                product_selectors = [
                    '[data-automation="product-item"]',
                    '.product-item',
                    '.productItemContainer',
                    '[class*="product"]',
                    '.x-productListItem',
                    'a[href*="laptop"]'
                ]

                product_elements = []
                for selector in product_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        elements = await page.query_selector_all(selector)
                        if elements:
                            product_elements = elements
                            print(f"Found {len(elements)} products using selector: {selector}")
                            break
                    except:
                        print(f"Selector '{selector}' not found, trying next...")
                        continue

                if not product_elements:
                    print("No product elements found with any selector")
                    return []

                # Handle infinite scroll if needed
                if len(product_elements) < max_products:
                    print("Attempting to load more products...")
                    scrolled = await self.infinite_scroll(page, max_scrolls=3)
                    if scrolled:
                        # Re-get product elements after scrolling
                        for selector in product_selectors:
                            try:
                                elements = await page.query_selector_all(selector)
                                if elements and len(elements) > len(product_elements):
                                    product_elements = elements
                                    print(f"After scrolling: {len(elements)} products")
                                    break
                            except:
                                continue

                # Extract product information
                print(f"Extracting info from {min(len(product_elements), max_products)} products...")

                for i, element in enumerate(product_elements[:max_products]):
                    try:
                        product = await self._extract_simple_product_info(element, i, context)
                        if product:
                            products.append(product)
                            print(f"Product {len(products)}: {product.title[:50]}...")

                        # Small delay between extractions
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"Error extracting product {i+1}: {str(e)}")
                        continue

                await context.close()
                print(f"Scraping complete! Found {len(products)} products")

            except Exception as e:
                print(f"Scraping error: {str(e)}")

            finally:
                if browser:
                    await browser.close()

        return products

    async def infinite_scroll(self, page, max_scrolls: int = 10) -> bool:
        """Handle infinite scroll pages to load more content"""
        print("Handling infinite scroll...")

        try:
            previous_height = await page.evaluate("document.body.scrollHeight")
            scrolls_performed = 0

            for scroll_attempt in range(max_scrolls):
                # Scroll to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                # Wait for content to load
                await asyncio.sleep(2)

                # Check if new content loaded
                current_height = await page.evaluate("document.body.scrollHeight")

                if current_height == previous_height:
                    # Try clicking "Load More" button if exists
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
                                await asyncio.sleep(2)
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
        except Exception as e:
            print(f"Infinite scroll error: {str(e)}")
            return False

    async def _extract_simple_product_info(self, element, index: int, context) -> Optional[Product]:
        """Simplified product extraction with better error handling"""
        try:
            # Extract title with multiple fallbacks
            title = "Unknown Product"
            title_selectors = [
                '[data-automation="product-title"]',
                '.product-item-name',
                'h3 a',
                'h4 a',
                '.productItemName',
                'a[href*="laptop"]'
            ]

            for selector in title_selectors:
                try:
                    title_elem = await element.query_selector(selector)
                    if title_elem:
                        title_text = await title_elem.inner_text()
                        if title_text and title_text.strip():
                            title = title_text.strip()
                            break
                except:
                    continue

            # Extract price with multiple fallbacks
            price = "Price not available"
            price_selectors = [
                '[data-automation="product-price"]',
                '.current-price',
                '.price',
                '[class*="price"]',
                '.screenReaderOnly'
            ]

            for selector in price_selectors:
                try:
                    price_elem = await element.query_selector(selector)
                    if price_elem:
                        price_text = await price_elem.inner_text()
                        if price_text and '$' in price_text:
                            price = self._clean_price(price_text)
                            break
                except:
                    continue

            # Extract URL
            url = ""
            try:
                link_elem = await element.query_selector('a')
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        url = f"{self.base_url}{href}" if href.startswith('/') else href
            except:
                pass
            
            actual_url = self._extract_actual_url(url)
            detailed_specs = await self._get_detailed_specs(actual_url, context) if actual_url else ""

            # Extract rating (optional)
            rating = None
            rating_selectors = [
                '[data-automation="product-rating"]',
                '.rating',
                '[class*="rating"]',
                '[class*="star"]'
            ]

            for selector in rating_selectors:
                try:
                    rating_elem = await element.query_selector(selector)
                    if rating_elem:
                        rating_text = await rating_elem.inner_text()
                        if rating_text and rating_text.strip():
                            rating = rating_text.strip()
                            break
                except:
                    continue

            # Extract image URL (optional)
            image_url = None
            try:
                img_elem = await element.query_selector('img')
                if img_elem:
                    src = await img_elem.get_attribute('src') or await img_elem.get_attribute('data-src')
                    if src and not src.startswith('data:'):
                        image_url = src if src.startswith('http') else f"https:{src}"
            except:
                pass

            # Simple or detailed description
            description = detailed_specs if detailed_specs else f"Laptop product available at Best Buy Canada. {title}"

            # Only return product if we have basic info
            if title != "Unknown Product" and url:
                return Product(
                    title=self._clean_text(title),
                    price=price,
                    description=description[:3000],
                    url=url,
                    rating=rating,
                    image_url=image_url,
                    scraped_at=datetime.now()
                )
            else:
                print(f"Insufficient data for product {index + 1}")
                return None

        except Exception as e:
            print(f"Error in product extraction: {str(e)}")
            return None
    
    def _extract_actual_url(self, redirect_url: str) -> str:
        """Extract actual product URL from tracking redirect"""
        import urllib.parse
        
        if 'criteo.com' in redirect_url:
            # Extract dest parameter
            parsed = urllib.parse.urlparse(redirect_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'dest' in query_params:
                actual_url = urllib.parse.unquote(query_params['dest'][0])
                return actual_url
        
        return redirect_url

    async def _get_detailed_specs(self, product_url: str, context) -> str:
        """Navigate to product page and extract detailed specs"""
        try:
            print(f"Getting specs from: {product_url}")
            page = await context.new_page()
            await page.goto(product_url, timeout=30000)
            await asyncio.sleep(2)
            
            # Check page content
            page_content = await page.content()
            print(f"Page loaded, content length: {len(page_content)}")
            
            # Target the specific selectors
            spec_selectors = [
                '[data-testid="more-information-container"]',
                '.productDescription_2WBlx',
                '.moreInformation_389hV',
                '.boxContentsContainer_1bKGR',
                '[data-testid="box-content-col-0"]'
            ]
            
            for selector in spec_selectors:
                print(f"Trying selector: {selector}")
                spec_elem = await page.query_selector(selector)
                if spec_elem:
                    specs_text = await spec_elem.inner_text()
                    print(f"Found specs: {specs_text[:100]}...")
                    await page.close()
                    return specs_text[:3000]
            
            print("No specs found with any selector")
            await page.close()
            return ""
        except Exception as e:
            print(f"Error getting specs: {str(e)}")
            return ""

    def _clean_price(self, price: str) -> str:
        """Clean price text"""
        if not price:
            return "Price not available"

        import re
        price = re.sub(r'(current price|sale price|was|now)', '', price, flags=re.IGNORECASE)
        price = re.sub(r'\s+', ' ', price.strip())

        # Find price pattern
        price_match = re.search(r'\$[\d,]+\.?\d*', price)
        if price_match:
            return price_match.group()

        return price.strip()[:50] if price.strip() else "Price not available"

    def _clean_text(self, text: str) -> str:
        """Clean text content"""
        if not text:
            return ""

        # Basic cleaning
        cleaned = re.sub(r'\s+', ' ', text.strip())
        return cleaned[:200]  # Reasonable limit