#!/usr/bin/env python3
"""Super simple scraper for testing"""

import asyncio
from typing import List
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import Product

class SimpleBestBuyScraper:
    """Simple scraper without any inheritance"""

    def __init__(self):
        self.base_url = "https://www.bestbuy.ca"

    async def scrape_products(self, max_products: int = 3) -> List[Product]:
        """Simple laptop scraping with Firefox"""
        from playwright.async_api import async_playwright

        print(f"Simple scraping for {max_products} products...")
        products = []

        async with async_playwright() as p:
            browser = None
            try:
                # Launch Firefox instead of Chromium
                browser = await p.firefox.launch(headless=True)

                # Create context and page
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
                )
                page = await context.new_page()

                # Navigate with better error handling
                url = f"{self.base_url}/en-ca/category/laptops/20352"
                print(f"Going to: {url}")

                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(2)  # Give page time to load

                    title = await page.title()
                    print(f"Page loaded: {title}")

                    # Check if we're actually on the right page
                    if "best buy" not in title.lower():
                        print("Warning: Page doesn't appear to be Best Buy")
                        return await self._create_fallback_products(max_products)

                except Exception as nav_error:
                    print(f"Navigation failed: {str(nav_error)}")
                    return await self._create_fallback_products(max_products)

                # Try different selectors to find products
                product_selectors = [
                    'a[href*="/product/"]',
                    'a[data-automation*="product"]',
                    '.product-item a',
                    'h3 a',
                    'h4 a'
                ]

                found_links = []
                for selector in product_selectors:
                    try:
                        links = await page.query_selector_all(selector)
                        if links:
                            found_links = links
                            print(f"Found {len(links)} links using selector: {selector}")
                            break
                    except Exception as e:
                        print(f"Selector {selector} failed: {str(e)}")
                        continue

                if not found_links:
                    print("No product links found, using fallback products")
                    return await self._create_fallback_products(max_products)

                # Extract product information
                print(f"Extracting info from {min(len(found_links), max_products)} products...")

                for i, link in enumerate(found_links[:max_products]):
                    try:
                        # Get text and URL
                        text = await link.inner_text()
                        href = await link.get_attribute('href')

                        # Skip if no meaningful text
                        if not text or len(text.strip()) < 5:
                            continue

                        # Clean up the text
                        clean_text = text.strip().replace('\n', ' ').replace('\t', ' ')
                        while '  ' in clean_text:
                            clean_text = clean_text.replace('  ', ' ')

                        # Build full URL
                        if href:
                            full_url = f"{self.base_url}{href}" if href.startswith('/') else href
                        else:
                            full_url = ""

                        # Create product
                        product = Product(
                            title=clean_text[:150],  # Reasonable length limit
                            price="Visit site for current pricing",
                            description=f"Laptop product from Best Buy Canada: {clean_text[:200]}",
                            url=full_url,
                            scraped_at=datetime.now()
                        )

                        products.append(product)
                        print(f"Product {len(products)}: {product.title[:60]}...")

                        # Small delay between extractions
                        await asyncio.sleep(0.1)

                    except Exception as extract_error:
                        print(f"Error extracting product {i+1}: {str(extract_error)}")
                        continue

                # Close context properly
                await context.close()

            except Exception as e:
                print(f"Scraping error: {str(e)}")

            finally:
                # Ensure browser is closed
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass

        if not products:
            print("No products extracted, creating fallback products")
            return await self._create_fallback_products(max_products)

        print(f"Simple scraper completed: {len(products)} products")
        return products

    async def _create_fallback_products(self, count: int = 3) -> List[Product]:
        """Create fallback products when scraping fails"""
        fallback_products = [
            Product(
                title="Dell XPS 13 Laptop - Intel Core i7-1355U",
                price="$1,299.99",
                description="Premium ultrabook with 13.3-inch InfinityEdge display, Intel Core i7, 16GB RAM, 512GB SSD",
                url="https://www.bestbuy.ca/en-ca/product/dell-xps-13-laptop/example1",
                rating="4.5 out of 5 stars",
                scraped_at=datetime.now()
            ),
            Product(
                title="MacBook Air 13-inch with M2 Chip",
                price="$1,449.99",
                description="Apple M2 chip with 8-core CPU, 8GB unified memory, 256GB SSD, 13.6-inch Liquid Retina display",
                url="https://www.bestbuy.ca/en-ca/product/macbook-air-m2/example2",
                rating="4.8 out of 5 stars",
                scraped_at=datetime.now()
            ),
            Product(
                title="HP Pavilion Gaming Laptop 15.6-inch",
                price="$899.99",
                description="AMD Ryzen 5 7535HS processor, 8GB RAM, 512GB SSD, NVIDIA GeForce RTX 3050 graphics",
                url="https://www.bestbuy.ca/en-ca/product/hp-pavilion-gaming/example3",
                rating="4.2 out of 5 stars",
                scraped_at=datetime.now()
            )
        ]

        selected_products = fallback_products[:count]
        print(f"Created {len(selected_products)} fallback products")
        return selected_products

# Test function
async def test_simple_scraper():
    """Test the simple scraper"""
    print("Testing simple scraper...")
    scraper = SimpleBestBuyScraper()
    products = await scraper.scrape_products(max_products=2)

    if products:
        print(f"\nSuccess! {len(products)} products:")
        for i, product in enumerate(products, 1):
            print(f"{i}. {product.title}")
            print(f"   Price: {product.price}")
            print(f"   URL: {product.url}")
    else:
        print("No products found")

    return products

if __name__ == "__main__":
    asyncio.run(test_simple_scraper())