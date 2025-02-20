import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from .BaseScraper import BaseScraper  # Assuming this is your base class


class VintedScraper(BaseScraper):

    BASE_URL = "https://www.vinted.fr"
    SEARCH_URL = "https://www.vinted.fr/catalog"

    def __init__(self):
        """Initialisation du navigateur avec les options."""
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless")  # Set to False to see the browser
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--log-level=3")  # Reduce unnecessary logs

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        self.driver.quit()

    async def get_page_content(self, url: str) -> str:
        """Récupérer le contenu de la page avec Selenium et gestion des erreurs."""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.feed-grid__item-content")
                )  
            )
            return self.driver.page_source
        except Exception as e:
            logging.error(
                f"Erreur lors du chargement de la page {url} : {str(e)}"
            )  # More specific error message
            return ""

    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        produits = []
        params = {
            "search_text": query,
            "order": "newest_first",
        }
        url = f"{self.SEARCH_URL}?{self._encode_params(params)}"  # build the url here
        try:
            logging.info(f"🔍 Recherche de '{query}' sur Vinted...")
            content = await self.get_page_content(url)
            await self.__aexit__()
            if not content:
                return []

            soup = BeautifulSoup(content, "html.parser")
            items = soup.find_all(
                "div", class_="feed-grid__item-content"
            )  # use the more robust selector
            logging.info(f"Trouvé {len(items)} articles sur Vinted pour: {query}")

            for item in items[:limit]:
                produit = self.parse_item(item)
                if produit:
                    produits.append(produit)

        except Exception as e:
            logging.error(f"Erreur lors du scraping de Vinted: {str(e)}")
            raise

        return produits

    def parse_item(self, item) -> Optional[Dict[str, Any]]:
        try:
            # Vendeur
            # seller_element = item.select_one('div[data-testid*="owner"]')
            # seller = seller_element.text.strip() if seller_element else None
            # seller_url = seller_element.select_one("a").get("href") if seller_element else None

            # URL du produit
            link_element = item.select_one("a.new-item-box__overlay")
            product_url = (
                self.BASE_URL + link_element.get("href")
                if link_element and link_element.get("href")
                else None
            )

            # ID du produit (data-testid)
            product_id_element = item.select_one(
                '[data-testid*="product-item-id"]'
            )  # Select by partial attribute
            product_id = (
                product_id_element.get("data-testid").split("--")[0].split("-")[-1]
                if product_id_element
                else None
            )  # Extract ID

            # Image URL
            image_element = item.select_one("img.web_ui__Image__content")
            image_url = image_element.get("src") if image_element else None

            # Titre (plusieurs options car la structure peut varier)
            title_element = item.select_one(
                ".new-item-box__description p.web_ui__Text__text"
            )
            title = title_element.text.strip() if title_element else None

            # Prix
            price_element = item.select_one('p[data-testid*="--price-text"]')
            price = price_element.text.strip() if price_element else None
            price_element_pro = item.select_one(
                'button[aria-label*="Protection"]>span>span'
            )
            price_pro = price_element_pro.text.strip() if price_element else None

            #  Description (peut être absente)
            description = item.select_one('p[data-testid*="description-subtitle"]')
            description = description.text.strip() if description else None

            if product_url and product_id and title and price:
                logging.info(
                    f" Article Vinted: {title} - {price} - {product_url[:20]}..."
                )
                return {
                    "source": "vinted",
                    "product_id": product_id,
                    "title": title,
                    "price": price,
                    "price_with_protection": price_pro,
                    # "seller": seller,
                    # "seller_url": seller_url,
                    "description": description,
                    "product_url": product_url,
                    "image_url": image_url,
                }
            return None

        except Exception as e:
            logging.error(f"Erreur extraction article Vinted: {str(e)}")
            return None


vinted_scraper = VintedScraper()
