import asyncio
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
from .BaseScraper import BaseScraper


class VintedScraper(BaseScraper):

    BASE_URL = "https://www.vinted.fr"
    SEARCH_URL = "https://www.vinted.fr/catalog"

    def __init__(self):
        """Initialisation du navigateur avec les options optimisées."""
        options = Options()
        options.add_argument(
            "--disable-blink-features=AutomationControlled"
        )  # Masquer Selenium
        options.add_argument(
            "--headless"
        )  # Exécuter en arrière-plan (mettre False pour voir le navigateur)
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--log-level=3")  # Réduit les logs inutiles

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    async def get_page_content(self, url: str) -> str:
        """Obtenir le contenu d'une page."""
        self.driver.get(url)

        # Attendre que la page charge entièrement
        # await asyncio.sleep(5)

        try:
            WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'p[data-testid*="description-title"]')
                )
            )
            return self.driver.page_source
        except Exception as e:
            logging.error("Aucun produit trouvé ! Vérifie si Vinted te bloque.")
            raise e

    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        products = []
        params = {
            "search_text": query,
            "order": "newest_first",
        }
        try:
            logging.info(f"🔍 Recherche de '{query}' sur Vinted!")
            content = await self.get_page_content(
                f"{self.SEARCH_URL}?{self._encode_params(params)}"
            )
            soup = BeautifulSoup(content, "html.parser")

            items = soup.select('p[data-testid*="description-title"]')
            logging.info(f"Trouvé {len(items)} éléments sur Vinted pour: {query}")
            for item in items[:limit]:
                product = self.parse_item(item)
                if product:
                    products.append(product)
        except Exception as e:
            logging.error(f"Erreur lors du scraping de Vinted: {str(e)}")
            raise e

        return products

    def parse_item(self, item) -> Optional[Dict[str, Any]]:
        try:
            title = item.text.strip()

            # Récupérer le prix
            price_elem = item.find_next(
                "p", {"data-testid": lambda x: x and "price-text" in x}
            )
            price_text = (
                price_elem.text.strip().replace("\xa0", " ")
                if price_elem
                else "Prix inconnu"
            )

            # Récupérer la taille
            size_elem = item.find_next(
                "p", {"data-testid": lambda x: x and "description-subtitle" in x}
            )
            size_text = size_elem.text.strip() if size_elem else "Taille inconnue"

            # Récupérer le lien du produit
            product_container = item.find_parent(
                "div", {"data-testid": lambda x: x and "description" in x}
            )
            link_elem = (
                product_container.find_previous("a") if product_container else None
            )
            href = link_elem.get("href", "") if link_elem else ""
            product_url = href if href.startswith("http") else self.BASE_URL + href

            # Product Id
            product_id = (
                product_url.split("/")[-1].split("-")[0] if product_url else None
            )

            # Récupérer l'image
            img_elem = (
                product_container.find_previous("img") if product_container else None
            )
            image_url = img_elem.get("src") if img_elem else ""

            logging.info(f"🛒 {title} - {price_text} - {size_text} - {product_url}")

            return {
                "product_id": product_id,
                "name": title,
                "price": price_text,
                "size": size_text,
                "image_url": image_url,
                "product_url": product_url,
                "source": "vinted",
            }
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction d'un produit : {str(e)}")
            return None


vinted_scraper = VintedScraper()
