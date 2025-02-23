

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.bd_scraping_arbook.models_vinted import Product
from app.bd_scraping_arbook.models_amazon import AmazonProduct
import asyncio

async def init_db():
    """Initialise la connexion à MongoDB avec Beanie"""
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        database = client["scraping_arbook"]  

        # IMPORTANT : Initialiser TOUS les modèles ensemble
        await init_beanie(database, document_models=[Product, AmazonProduct])

        print(" Connexion à MongoDB réussie !")
        return client
    except Exception as e:
        print(f" Erreur de connexion à MongoDB: {e}")

