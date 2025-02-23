from beanie import Document 
from typing import Optional
from pydantic import HttpUrl

class AmazonProduct(Document):
    source: str
    product_id: str
    name: str
    price: str
    delivery: Optional[str]
    stock: bool
    is_exclusive: bool
    rating: Optional[str]
    product_url: HttpUrl
    image_url: HttpUrl

    class Settings:
        collection = "amazon_products"
