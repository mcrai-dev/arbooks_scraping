from typing import List, Dict, Any, Optional
import logging
import aiohttp
from bs4 import BeautifulSoup
from .BaseScraper import BaseScraper
from app.bd_scraping_arbook.database import init_db
from app.bd_scraping_arbook.models_amazon import AmazonProduct
from .utils import Product


async def save_to_mongo(products: list[dict]):
    """Insère les produits scrappés dans MongoDB en évitant les doublons (mise à jour si déjà existant)."""
    await init_db()  # S'assurer que la DB est connectée

    if not products:
        print(" Aucun produit à enregistrer dans MongoDB.")
        return

    for item in products:
        try:
            # Utilisation de replace_one() avec upsert=True pour gérer la mise à jour et éviter les erreurs de duplication
            result = await AmazonProduct.get_motor_collection().replace_one(
                {"product_id": item["product_id"]},  # Vérifie l'existence
                item,  # Remplace le document s'il existe, insère sinon
                upsert=True  # Assure que l'opération est atomique
            )

            if result.matched_count > 0:
                print(f" Produit {item['name']} ({item['product_id']}) mis à jour avec succès !")
            else:
                print(f" Produit {item['name']} ({item['product_id']}) inséré avec succès !")

        except Exception as e:
            print(f" Erreur lors de l'insertion MongoDB : {e}")




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
            logging.info(f" Recherche de '{query}' sur Amazon!")
            content = await self.get_page_content(
                f"{self.SEARCH_URL}?{self._encode_params(params)}"
            )
            if not content:
                return products

            soup = BeautifulSoup(content, "lxml")
            items = soup.select('div[data-component-type="s-search-result"]')
            logging.info(f"Trouvé {len(items)} éléments sur Amazon pour: {query}")

            for item in items[:limit]:
                product = self.parse_item(item)
                if product:
                    products.append(product)
            
            if products :
                logging.info(" Enregistrement des produits dans MongoDB...")
                await save_to_mongo(products)

        except Exception as e:
            logging.error(f"Erreur lors du scraping d'Amazon: {str(e)}")
            raise
        return products

    def parse_item(self, item) -> Optional[Dict[str, Any]]:
        product = Product(source='amazon')
        try:
            # Get product id
            asin = item.get("data-asin", "")
            product.product_id = asin if asin else None

            # Titre
            product.name = item.h2.text.strip() if item.h2 else ""
            

            livraison = item.select_one('div[data-cy="delivery-recipe"]')
            livraison = livraison.text if livraison else None
            product.delivery_price = "".join(livraison.strip().split(" ")[2:]) if livraison else None

            # URL du produit
            href = item.select_one("a.a-link-normal").get("href", "")
            product.url = (
                self.BASE_URL + href if href and not href.startswith("http") else href
            )
            # URL de l'image
            product.main_photo = (
                item.select_one("img.s-image")["src"]
                if item.select_one("img.s-image")
                else None
            )
            # Prix
            product.price = (
                item.find("span", class_="a-offscreen").text.strip()
                if item.find("span", class_="a-offscreen")
                else None
            )
            # Évaluation du produit
            product.rating = (
                item.select_one("span.a-icon-alt").text.strip()
                if item.select_one("span.a-icon-alt")
                else None
            )
            # Exclusivité Amazon
            product.is_exclusive = bool(
                item.select_one("span.a-badge-text")
                and "Exclusivité Amazon" in item.select_one("span.a-badge-text").text
            )

            # Disponibilité en stock
            product.stock = not bool(item.select_one(".s-item__out-of-stock"))

            if product.is_valid():
                logging.info(product)
                return product.to_dict()

        except Exception as e:
            logging.error(f"Erreur lors de l'extraction d'un produit : {str(e)}")
            return None

    def parse_table(self, table):
        headers = [el.text.strip() for el in table.find_all("th")]
        rows = [el.text.strip() for el in table.find_all("td")]
        return {th: td for th, td in zip(headers, rows)}

    def parse_details(self, soup):
        product = Product(source='amazon')
        try:
            canonical_link = soup.select_one('link[rel="canonical"]')
            product.url = canonical_link.get('href') if canonical_link else None
            
            asin = soup.select_one('#all-offers-display-params')
            if asin:
                product.product_id = asin.get('data-asin')
            
            price_element = soup.select_one('div[id*="corePrice"] .a-offscreen, div[id*="corePrice"] .aok-offscreen')  # Combine selectors
            product.price = price_element.text.strip() if price_element else None

            category_elements = soup.select("#wayfinding-breadcrumbs_feature_div a")
            product.categories = [cat.text.strip() for cat in category_elements] if category_elements else None

            title_element = soup.select_one("#productTitle")
            product.name = title_element.text.strip() if title_element else None
            
            image_elements = soup.select("#main-image-container img") + soup.select("#altImages img")
            product.detailed_photos = [img.get('src') for img in image_elements if img.get('src')] if image_elements else None

                
            product_table = soup.select_one("#productDetails_feature_div table") or soup.select_one("#prodDetails table")
            product.feature_table = self.parse_table(product_table) if product_table else None 

            sizes = soup.select_one("#variation_size_name")
            if sizes:
                options = sizes.find_all("option")
                product.sizes= [option.text for option in options[1:]] if options else None

            availability = soup.select_one('#availability')
            if availability:
                product.stock = True if availability.text.strip()==' En stock' else False

            bullet_elements = soup.select("#feature-bullets li")
            product.feature_bullet = [li.text.strip() for li in bullet_elements] if bullet_elements else None

            color_elements = soup.select("#variation_color_name ul img")
            product.colors = [
                {"color": color.get("alt", ""), "img": color.get("src", "")}
                for color in color_elements
            ] if color_elements else None

            description_element = soup.select_one("#productDescription p")
            product.description = description_element.text.strip() if description_element else None

            return [product.to_dict()]
        
        except Exception as e:
            logging.error(f"Erreur extraction detail article Amazon: {str(e)}")
            return []
        
    async def get_detail(self, product_url) -> List[Dict[str, Any]]:
        content = await self.get_page_content(product_url)
        await self.__aexit__()
        if not content:
            return []
        soup = BeautifulSoup(content, "lxml")
        return self.parse_details(soup)


amazon_scraper = AmazonScraper()
