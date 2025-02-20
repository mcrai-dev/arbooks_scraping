from typing import List, Dict, Any, Optional
import logging
import aiohttp
from bs4 import BeautifulSoup
from .BaseScraper import BaseScraper


class AmazonScraper(BaseScraper):

    BASE_URL = "https://www.amazon.fr"
    SEARCH_URL = "https://www.amazon.fr/s"
    # Headers that mimic a real browser
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "rtt": "50",
        "downlink": "10",
        "ect": "4g",
    }

    async def __aenter__(self):
        """Initialisation de la session."""
        self.session = aiohttp.ClientSession(headers=self.HEADERS)
        return self

    async def __aexit__(self, *excinfo):
        """Fermeture de la session."""
        if hasattr(self, "session") and self.session:
            await self.session.close()

    async def get_page_content(self, url: str) -> str:
        """Obtenir le contenu d'une page."""
        await self.__aenter__()
        try:
            async with self.session.get(url, ssl=False) as response:
                if response.status >= 400:
                    text = await response.text()
                    logging.error(f"HTTP {response.status} pour {url}: {text}")
                    return ""
                return await response.text()

        except aiohttp.ClientError as e:
            logging.error(f"Erreur de requête pour {url}: {e}")

            return ""
        except Exception as e:
            logging.error(f"Erreur de chargement de la page {url}: {str(e)}")
            return ""

    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        products = []
        params = {
            "k": query,
            # "ref": "nb_sb_noss",
            # "sprefix": f"{query},aps,283",
            # "crid": "2M7LQQC1YQLR0",
        }
        try:
            logging.info(f"🔍 Recherche de '{query}' sur Amazon!")
            content = await self.get_page_content(
                f"{self.SEARCH_URL}?{self._encode_params(params)}"
            )
            await self.__aexit__()
            if not content:
                return products

            soup = BeautifulSoup(content, "html.parser")
            items = soup.select('div[data-component-type="s-search-result"]')
            logging.info(f"Trouvé {len(items)} éléments sur Amazon pour: {query}")

            for item in items[:limit]:
                product = self.parse_item(item)
                if product:
                    products.append(product)
        except Exception as e:
            logging.error(f"Erreur lors du scraping d'Amazon: {str(e)}")
            raise
        return products

    def parse_item(self, item) -> Optional[Dict[str, Any]]:
        try:
            asin = item.get("data-asin", "")
            # Titre
            title = item.h2.text.strip() if item.h2 else ""
            # URL du produit
            href = item.select_one("a.a-link-normal").get("href", "")

            livraison = item.select_one('div[data-cy="delivery-recipe"]')
            livraison = livraison.text if livraison else None
            livraison = "".join(livraison.strip().split(" ")[2:]) if livraison else None

            product_url = (
                self.BASE_URL + href if href and not href.startswith("http") else href
            )
            # URL de l'image
            image_url = (
                item.select_one("img.s-image")["src"]
                if item.select_one("img.s-image")
                else ""
            )
            # Prix
            price = (
                item.find("span", class_="a-offscreen").text.strip()
                if item.find("span", class_="a-offscreen")
                else ""
            )
            # Évaluation du produit
            rating = (
                item.select_one("span.a-icon-alt").text.strip()
                if item.select_one("span.a-icon-alt")
                else None
            )
            # Exclusivité Amazon
            is_exclusive = bool(
                item.select_one("span.a-badge-text")
                and "Exclusivité Amazon" in item.select_one("span.a-badge-text").text
            )

            # Disponibilité en stock
            stock = not bool(item.select_one(".s-item__out-of-stock"))

            if title and product_url and asin:
                logging.info(
                    f"🛒 {title} - {price} - {stock} - {product_url[:10]}... -"
                )
                return {
                    "source": "amazon",
                    "product_id": asin,
                    "name": title,
                    "price": price,
                    "delivery": livraison,
                    "stock": stock,
                    "is_exclusive": is_exclusive,
                    "rating": rating,
                    "product_url": product_url,
                    "image_url": image_url,
                }
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction d'un produit : {str(e)}")
            return None


amazon_scraper = AmazonScraper()
