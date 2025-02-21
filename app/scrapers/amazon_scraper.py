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
            if not content:
                return products

            soup = BeautifulSoup(content, "lxml")
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

    def parse_table(self, table):
        headers = [el.text.strip() for el in table.find_all("th")]
        rows = [el.text.strip() for el in table.find_all("td")]
        return {th: td for th, td in zip(headers, rows)}

    def parse_details(self, soup):
        details = {}
        
        price_element = soup.select_one('div[id*="corePrice"] .a-offscreen, div[id*="corePrice"] .aok-offscreen')  # Combine selectors
        details["price"] = price_element.text.strip() if price_element else None

        category_elements = soup.select("#wayfinding-breadcrumbs_feature_div a")
        details["categories"] = [cat.text.strip() for cat in category_elements] if category_elements else None

        title_element = soup.select_one("#productTitle")
        details["name"] = title_element.text.strip() if title_element else None
        
        image_elements = soup.select("#main-image-container img") + soup.select("#altImages img")
        details['photos'] = [img.get('src') for img in image_elements if img.get('src')] if image_elements else None

            
        product_table = soup.select_one("#productDetails_feature_div table") or soup.select_one("#prodDetails table")
        details["product_feature_table"] = self.parse_table(product_table) if product_table else None 

        sizes = soup.select_one("#variation_size_name")
        if sizes:
            options = sizes.find_all("option")
            details["sizes"] = [option.text for option in options[1:]] if options else None

        availability = soup.select_one('#availability')
        if availability:
            details['available'] = True if availability.text.strip()==' En stock' else False

        bullet_elements = soup.select("#feature-bullets li")
        details["bullet_feature"] = [li.text.strip() for li in bullet_elements] if bullet_elements else None

        color_elements = soup.select("#variation_color_name ul img")
        details["colors"] = [
            {"color": color.get("alt", ""), "img": color.get("src", "")}
            for color in color_elements
        ] if color_elements else None

        description_element = soup.select_one("#productDescription p")
        details["description"] = description_element.text.strip() if description_element else None

        return [details]

    async def get_detail(self, product_url) -> List[Dict[str, Any]]:
        content = await self.get_page_content(product_url)
        await self.__aexit__()
        if not content:
            return []
        soup = BeautifulSoup(content, "lxml")
        return self.parse_details(soup)


amazon_scraper = AmazonScraper()
