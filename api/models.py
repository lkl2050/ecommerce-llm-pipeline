from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Product(BaseModel):
    title: str
    price: str
    description: str
    url: str
    rating: Optional[str] = None
    image_url: Optional[str] = None
    scraped_at: datetime

class ProductWithSummary(Product):
    llm_summary: str
    llm_highlights: List[str]
    prompt_type: Optional[str] = None

class ProductResponse(BaseModel):
    products: List[ProductWithSummary]
    total_count: int
    category: str
    scraped_at: Optional[datetime]