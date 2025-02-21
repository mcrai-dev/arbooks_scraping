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
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
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

    async def get_page_content(self, url: str, wait_for: str) -> str:
        """Récupérer le contenu de la page avec Selenium et gestion des erreurs."""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
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
            content = await self.get_page_content(url, "div.feed-grid__item-content")
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
            product_url = (link_element.get("href")
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

    def parse_detail(self, item) -> List[Dict[str, Any]]:
        detail_container = item.select_one("div.details-list.details-list--details")
        if not detail_container:
            return []

        details = {}
        status = item.select_one('div[data-testid="item-status--content"]')
        details["status"] = status.text.strip() if status else "Disponible"

        price = item.select_one('div[data-testid="item-price"]')
        details["price"] = price.text.strip().replace("\xa0", " ") if price else None

        price_protection = item.select_one('button[aria-label*="Protection"] > div')
        details["price_with_protection"] = (
            price_protection.text.strip().replace("\xa0", " ")
            if price_protection
            else None
        )

        # Extract Brand
        brand_element = detail_container.select_one('span[itemprop="name"]')
        details["brand"] = brand_element.text.strip() if brand_element else None

        # Extract Size
        size_element = detail_container.select_one('div[itemprop="size"]')
        details["size"] = size_element.text.strip() if size_element else None

        condition_element = detail_container.select_one('div[itemprop="status"]')
        details["condition"] = (
            condition_element.text.strip() if condition_element else None
        )

        color_element = detail_container.select_one('div[itemprop="color"]')
        details["color"] = color_element.text.strip() if color_element else None

        views_element = detail_container.select_one('div[itemprop="view_count"]')
        details["views"] = int(views_element.text.strip()) if views_element else None

        interested_element = detail_container.select_one('div[itemprop="interested"]')
        details["interested"] = (
            int(interested_element.text.strip().split(" ")[0])
            if interested_element
            else None
        )

        payment_element = detail_container.select_one('div[itemprop="payment_methods"]')
        details["payment"] = payment_element.text.strip() if payment_element else None

        # Extract Uploaded Date
        uploaded_element = detail_container.select_one(
            'div[data-testid="item-attributes-upload_date"] [itemprop="upload_date"]'
        )
        details["uploaded"] = (
            uploaded_element.text.strip() if uploaded_element else None
        )
        # Extract Delivery Price
        delivery_element = item.select_one('[data-testid="item-shipping-banner-price"]')
        details["delivery"] = (
            delivery_element.text.strip().replace("\xa0", " ")
            if delivery_element
            else None
        )

        description_element = item.select_one('div[itemprop="description"]')
        details["description"] = (
            description_element.text.strip().replace('\n', '') if description_element else None
        )

        owner_name = item.select_one('[data-testid="profile-username"]')
        details["owner_name"] = owner_name.text.strip() if owner_name else ""

        owner_link_element = item.select_one(
            "a.web_ui__Cell__cell.web_ui__Cell__default.web_ui__Cell__navigating.web_ui__Cell__with-chevron.web_ui__Cell__link"
        )
        owner_url = owner_link_element.get("href") if owner_link_element else None
        if owner_url:
            owner_url = self.BASE_URL + owner_url
        details["owner_profile_url"] = owner_url
        return [details]

        return [details]

    async def get_detail(self, product_url: str) -> List[Dict[str, Any]]:
        logging.info("Obtenir la page contenant les detail du produits")
        content = await self.get_page_content(product_url, "aside")
        if not content:
            return []
        soup = BeautifulSoup(content, "html.parser")

        aside = soup.select_one("aside")
        if not aside:
            return []
        logging.info("Extraction des informatons importante")
        return self.parse_detail(aside)


vinted_scraper = VintedScraper()
