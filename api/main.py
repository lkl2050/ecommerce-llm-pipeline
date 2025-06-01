from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from scraper.bestbuy_scraper import EnhancedBestBuyCanadaScraper
from llm.processors import EnhancedGroqProcessor
from api.models import ProductResponse, ProductWithSummary

app = FastAPI(
    title="E-commerce LLM Pipeline API",
    description="Web scraping with LLM processing",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent storage file
PRODUCTS_FILE = "products_database.json"

# Global cache (loaded from file)
products_cache: List[ProductWithSummary] = []
last_scraped: Optional[datetime] = None
scraping_in_progress: bool = False

def save_products_to_file():
    """Save products to JSON file permanently"""
    try:
        data = {
            "products": [p.dict() for p in products_cache],
            "last_scraped": last_scraped.isoformat() if last_scraped else None,
            "total_count": len(products_cache),
            "saved_at": datetime.now().isoformat()
        }

        with open(PRODUCTS_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"Saved {len(products_cache)} products to {PRODUCTS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving products: {e}")
        return False

def load_products_from_file():
    """Load products from JSON file"""
    global products_cache, last_scraped

    try:
        if Path(PRODUCTS_FILE).exists():
            with open(PRODUCTS_FILE, 'r') as f:
                data = json.load(f)

            # Convert dict back to ProductWithSummary objects
            products_cache = [ProductWithSummary(**item) for item in data["products"]]

            if data.get("last_scraped"):
                last_scraped = datetime.fromisoformat(data["last_scraped"])

            print(f"Loaded {len(products_cache)} products from {PRODUCTS_FILE}")
            print(f"Last scraped: {last_scraped}")
        else:
            print(f"📄 No existing {PRODUCTS_FILE} found - starting fresh")
            products_cache = []
            last_scraped = None
    except Exception as e:
        print(f"Error loading products: {e}")
        products_cache = []
        last_scraped = None

@app.on_event("startup")
async def startup_event():
    """Load products when server starts"""
    print("🚀 Starting server and loading saved products...")
    load_products_from_file()

@app.get("/")
async def root():
    return {
        "message": "E-commerce LLM Pipeline API",
        "endpoints": {
            "products": "/products - Get processed products",
            "refresh": "/refresh - Scrape new products",
            "health": "/health - Health check",
            "save": "/save - Manually save to file",
            "clear": "/clear - Clear all products"
        },
        "cached_products": len(products_cache),
        "last_update": last_scraped,
        "storage_file": PRODUCTS_FILE
    }

@app.get("/products", response_model=ProductResponse)
async def get_products():
    """Get all processed products"""
    if not products_cache:
        raise HTTPException(
            status_code=404,
            detail="No products available. Use POST /refresh to scrape new data."
        )

    return ProductResponse(
        products=products_cache,
        total_count=len(products_cache),
        category="Laptops",
        scraped_at=last_scraped
    )

@app.post("/refresh")
async def refresh_products(background_tasks: BackgroundTasks, max_products: int = 15):
    """Start background scraping and processing"""
    global scraping_in_progress

    if scraping_in_progress:
        raise HTTPException(
            status_code=409,
            detail="Scraping already in progress"
        )

    background_tasks.add_task(scraping_pipeline, max_products)
    scraping_in_progress = True

    return {
        "message": f"Started scraping {max_products} products",
        "status": "processing",
        "current_total": len(products_cache)
    }

async def scraping_pipeline(max_products: int):
    """Background scraping and LLM processing with permanent storage"""
    global products_cache, last_scraped, scraping_in_progress

    try:
        print(f"Starting pipeline for {max_products} products")
        print(f"Current total: {len(products_cache)} products")

        # Scrape products
        scraper = EnhancedBestBuyCanadaScraper()
        raw_products = await scraper.scrape_products(max_products)

        if not raw_products:
            print("No products scraped")
            return

        print(f"Scraped {len(raw_products)} products, processing with LLM...")

        # Process with LLM
        llm_processor = EnhancedGroqProcessor()
        processed_products = await llm_processor.process_products_intelligently(raw_products)
        await llm_processor.close()

        # Accumulate products (avoid duplicates by URL)
        existing_urls = {p.url for p in products_cache}
        new_products = [p for p in processed_products if p.url not in existing_urls]

        old_count = len(products_cache)
        products_cache.extend(new_products)
        last_scraped = datetime.now()

        # Save to JSON file permanently
        if save_products_to_file():
            print(f"Successfully added {len(new_products)} new products")
            print(f"Total products: {len(products_cache)} (was {old_count})")
            print(f"Data permanently saved to {PRODUCTS_FILE}")
        else:
            print("Products added to memory but failed to save to file")

    except Exception as e:
        print(f"Pipeline error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        scraping_in_progress = False

@app.post("/save")
async def manual_save():
    """Manually save products to file"""
    success = save_products_to_file()

    if success:
        return {
            "message": f"Successfully saved {len(products_cache)} products",
            "filename": PRODUCTS_FILE,
            "total_products": len(products_cache),
            "saved_at": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to save products")

@app.post("/clear")
async def clear_products():
    """Clear all cached products and delete file"""
    global products_cache, last_scraped

    old_count = len(products_cache)
    products_cache = []
    last_scraped = None

    # Delete the file
    try:
        if Path(PRODUCTS_FILE).exists():
            Path(PRODUCTS_FILE).unlink()
            print(f"Deleted {PRODUCTS_FILE}")
    except Exception as e:
        print(f"Error deleting file: {e}")

    return {
        "message": f"Cleared {old_count} products and deleted storage file",
        "cached_products": 0,
        "file_deleted": True
    }

@app.get("/health")
async def health_check():
    """Health check with file info"""
    file_exists = Path(PRODUCTS_FILE).exists()
    file_size = Path(PRODUCTS_FILE).stat().st_size if file_exists else 0

    return {
        "status": "healthy",
        "cached_products": len(products_cache),
        "scraping_active": scraping_in_progress,
        "last_scraped": last_scraped,
        "storage_file": PRODUCTS_FILE,
        "file_exists": file_exists,
        "file_size_kb": round(file_size / 1024, 2) if file_exists else 0
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)