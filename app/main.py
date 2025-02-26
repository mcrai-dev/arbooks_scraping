
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any, Union
import logging
import asyncio
from .bd_scraping_arbook.database import DatabaseManager
from .scrapers.vinted_scraper import VintedScraper
from .scrapers.amazon_scraper import AmazonScraper

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Multi-Platform Product Search API")

# Initialisation globale du gestionnaire de base de données
db_manager = DatabaseManager()

vinted_scraper = VintedScraper(db_manager)
amazon_scraper = AmazonScraper(db_manager)

PLATFORM_SCRAPERS = {
    "vinted": vinted_scraper,
    "amazon": amazon_scraper,
    # "leboncoin": leboncoin_scraper,
}


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Multi-Platform Product Search API",
        "available_platforms": list(PLATFORM_SCRAPERS.keys()),
        "endpoints": {
            "search_platform": "/search/{platform}/{query}?limit={limit}",
            "platforms": "/platforms",
            "search_all": "/search/all/{query}?limit={limit}",
        },
    }


@app.get("/platforms")
async def get_platforms():
    """Get list of available platforms"""
    return {"platforms": list(PLATFORM_SCRAPERS.keys())}


@app.get("/search/{platform}/{query}")
async def search_products(
    platform: str, query: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search for products across specified platform

    Parameters:
    - platform: Platform to search on (leboncoin, amazon, vinted)
    - query: Search query
    - limit: Maximum number of results (default: 100)
    """
    print(
        f" API: Requête reçue pour {platform} avec query='{query}' et limit={limit}"
    ) 

    if platform=='all':
        return await search_all_platforms(query, limit)
    
    if platform not in list(PLATFORM_SCRAPERS.keys())+['all']:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' not supported. Available platforms: {['all']+list(PLATFORM_SCRAPERS.keys())}",
        )
    try:
        scraper = PLATFORM_SCRAPERS[platform]
        print(f" API: Lancement du scraping pour {platform}")  # Debug
        results = await scraper.search(query, limit)
        print(
            f" API: Scraping terminé pour {platform}, {len(results)} résultats trouvés"
        )  # Debug
        return results
    
    except Exception as e:
        logging.error(f" Erreur lors du scraping de {platform} : {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detail/{platform}/{product_url:path}")
async def get_product_detail(platform: str, product_url: str) -> List[Dict[str, Any]]:
    """
    Get details for a specific product on a platform

    Parameters:
    - platform: Platform to search on (leboncoin, amazon, vinted)
    - product_url: URL of the product to get details for
    """
    if platform not in PLATFORM_SCRAPERS:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' not supported. Available platforms: {list(PLATFORM_SCRAPERS.keys())}",
        )

    try:
        scraper = PLATFORM_SCRAPERS[platform]
        results = await scraper.get_detail(product_url)
        return results
    except Exception as e:
        logging.error(f"Error searching on {platform}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def search_all_platforms(
    query: str, limit: int = 10
) -> List[Dict[str, List[Dict[str, Any]]]]:
    """
     Recherche de produits sur toutes les plateformes disponibles
    - `query`: Nom du produit à rechercher
    - `limit`: Nombre maximum de résultats par plateforme (par défaut : 10)
    """
    results = {}
    errors = []

    for platform, scraper in PLATFORM_SCRAPERS.items():
        try:
            platform_results = await scraper.search(query, limit)
            results[platform] = platform_results

        except Exception as e:
            logging.error(f"🚨 Erreur lors du scraping de {platform} : {str(e)}")
            errors.append({"platform": platform, "error": str(e)})
            results[platform] = []

    if errors:
        return [{"results": results, "errors": errors}]

    return [results]


#  Lancer FastAPI avec uvicorn si le script est exécuté directement
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
