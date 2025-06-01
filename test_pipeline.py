# test_pipeline.py
import asyncio
import httpx
import time
from typing import Dict, Any

class PipelineTester:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def test_api_health(self) -> bool:
        """Test if the API is running"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("API health check passed")
                return True
            else:
                print(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"Cannot connect to API: {str(e)}")
            print("Make sure the API server is running with: python main.py")
            return False

    async def test_root_endpoint(self):
        """Test the root endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print("Root endpoint working")
                print(f"   Cached products: {data.get('cached_products', 0)}")
                print(f"   Last update: {data.get('last_update')}")
                return data
            else:
                print(f"Root endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"Root endpoint error: {str(e)}")

    async def test_products_endpoint_empty(self):
        """Test products endpoint when empty"""
        try:
            response = await self.client.get(f"{self.base_url}/products")
            if response.status_code == 404:
                print("Empty products endpoint returns 404 as expected")
                return True
            elif response.status_code == 200:
                data = response.json()
                print(f"Found {data.get('total_count', 0)} cached products")
                return True
            else:
                print(f"Unexpected products response: {response.status_code}")
                return False
        except Exception as e:
            print(f"Products endpoint error: {str(e)}")
            return False

    async def test_refresh_endpoint(self, max_products: int = 5):
        """Test the refresh endpoint to start scraping"""
        try:
            print(f"Starting refresh with {max_products} products...")
            response = await self.client.post(
                f"{self.base_url}/refresh?max_products={max_products}"
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Refresh started: {data.get('message')}")
                return True
            elif response.status_code == 409:
                print("Scraping already in progress")
                return True
            else:
                print(f"Refresh failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Refresh endpoint error: {str(e)}")
            return False

    async def wait_for_processing(self, max_wait: int = 300):
        """Wait for background processing to complete"""
        print("Waiting for background processing...")

        start_time = time.time()
        last_status_time = 0

        while time.time() - start_time < max_wait:
            try:
                response = await self.client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    data = response.json()

                    if not data.get('scraping_active', True):
                        cached_count = data.get('cached_products', 0)
                        if cached_count > 0:
                            print(f"Processing complete! {cached_count} products ready")
                            return True
                        else:
                            print("Processing finished but no products found")
                            return False

                    # Show progress every 15 seconds
                    current_time = time.time()
                    if current_time - last_status_time > 15:
                        elapsed = int(current_time - start_time)
                        print(f"   Still processing... ({elapsed}s elapsed)")
                        last_status_time = current_time

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                print(f"Error checking status: {str(e)}")
                await asyncio.sleep(5)

        print(f"Timeout after {max_wait} seconds")
        return False

    async def test_final_products(self):
        """Test the products endpoint after processing"""
        try:
            response = await self.client.get(f"{self.base_url}/products")

            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])

                print(f"Retrieved {len(products)} processed products")

                # Test first product in detail
                if products:
                    first_product = products[0]
                    print(f"\nSample Product:")
                    print(f"   Title: {first_product.get('title', 'N/A')}")
                    print(f"   Price: {first_product.get('price', 'N/A')}")
                    print(f"   Rating: {first_product.get('rating', 'N/A')}")
                    print(f"   URL: {first_product.get('url', 'N/A')}")
                    print(f"   LLM Summary: {first_product.get('llm_summary', 'N/A')}")

                    highlights = first_product.get('llm_highlights', [])
                    print(f"   LLM Highlights ({len(highlights)} items):")
                    for i, highlight in enumerate(highlights, 1):
                        print(f"      {i}. {highlight}")

                    # Validate required fields
                    required_fields = ['title', 'price', 'llm_summary', 'llm_highlights']
                    missing_fields = [field for field in required_fields if not first_product.get(field)]

                    if missing_fields:
                        print(f"Warning - Missing fields: {missing_fields}")
                    else:
                        print("All required fields present")

                    # Show a few more products briefly
                    if len(products) > 1:
                        print(f"\nOther products:")
                        for i, product in enumerate(products[1:4], 2):  # Show 2-4
                            title = product.get('title', 'N/A')[:50]
                            price = product.get('price', 'N/A')
                            summary = product.get('llm_summary', 'N/A')[:80]
                            print(f"   {i}. {title}... - {price}")
                            print(f"      {summary}...")

                return data
            else:
                print(f"Products endpoint failed: {response.status_code}")
                return None

        except Exception as e:
            print(f"Final products test error: {str(e)}")
            return None

    async def run_full_pipeline_test(self, max_products: int = 5):
        """Run the complete pipeline test"""
        print("Starting Full Pipeline Test...")
        print("=" * 50)

        # 1. Health check
        print("\n1. Testing API health...")
        if not await self.test_api_health():
            return False

        # 2. Test root endpoint
        print("\n2. Testing root endpoint...")
        await self.test_root_endpoint()

        # 3. Test empty products
        print("\n3. Testing products endpoint...")
        await self.test_products_endpoint_empty()

        # 4. Start refresh
        print("\n4. Starting scrape and process...")
        if not await self.test_refresh_endpoint(max_products):
            return False

        # 5. Wait for completion
        print("\n5. Waiting for completion...")
        if not await self.wait_for_processing():
            print("Processing timeout - check the server logs")
            return False

        # 6. Test final results
        print("\n6. Testing final results...")
        final_data = await self.test_final_products()

        # Cleanup
        await self.client.aclose()

        if final_data and final_data.get('products'):
            print(f"\nFull Pipeline Test PASSED!")
            print(f"Successfully processed {len(final_data['products'])} products")
            print("Your e-commerce LLM pipeline is working correctly!")
            return True
        else:
            print(f"\nFull Pipeline Test FAILED!")
            return False

async def main():
    print("Pipeline Integration Testing")
    print("=" * 40)

    tester = PipelineTester()
    success = await tester.run_full_pipeline_test(max_products=5)  # Start small

    if success:
        print("\nAll pipeline tests passed! Your system is ready.")
        print("\nNext steps:")
        print("- Try with more products: /refresh?max_products=10")
        print("- Test the API endpoints manually")
        print("- Deploy to GCP if needed")
    else:
        print("\nPipeline tests failed. Check the issues above.")

if __name__ == "__main__":
    asyncio.run(main())