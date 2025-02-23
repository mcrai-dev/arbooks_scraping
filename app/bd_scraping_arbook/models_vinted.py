from beanie import Document, Indexed
from typing import Optional
from pydantic import HttpUrl

class Product(Document):
    source: str
    product_id: str
    title: str
    price: str
    price_with_protection : str
    description : str
    product_url: HttpUrl
    image_url: HttpUrl
    

    class Settings:
        collection = "products"  
