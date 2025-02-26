
import logging
from datetime import datetime
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
#from app.bd_scraping_arbook.models_vinted import Product
from app.bd_scraping_arbook.models_scraping import Product_scraping
from .utils import Product


async def save_to_mongo(db_manager, products: list[dict]):
    """Insère les produits scrappés dans MongoDB en évitant les doublons (mise à jour si déjà existant)."""
    
    if not db_manager.is_initialized():  #  Vérifie l'initialisation
        success = await db_manager.initialize()
        if not success:
            logging.error("Échec de l'initialisation de la base de données. Annulation de l'insertion.")
            return
    
    if not products:
        logging.info("Aucun produit à enregistrer dans MongoDB.")
        return

    for item in products:
        try:
            # Vérifier si le produit existe déjà
            existing_product = await Product_scraping.find_one({"product_id": item["product_id"]})

            if existing_product:
                await existing_product.set(item)  #  Mise à jour
                logging.info(f"Produit {item['name']} ({item['product_id']}) mis à jour avec succès !")
            else:
                new_product = Product_scraping(**item)
                await new_product.insert()  #  Insertion
                logging.info(f"Produit {item['name']} ({item['product_id']}) inséré avec succès !")

        except Exception as e:
            logging.error(f"Erreur lors de l'insertion du produit {item.get('product_id', 'inconnu')}: {e}")



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

    def __init__(self,db_manager):
        self.db_manager = db_manager
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
        products = []
        params = {
            "k": query,
            "ref": "nb_sb_noss",
            "sprefix": f"{query},aps,283",
            "crid": "2M7LQQC1YQLR0",
        }
        try:
            logging.info(f" Recherche de '{query}' sur Amazon!")
            content = await self.get_page_content(
                f"{self.SEARCH_URL}?{self._encode_params(params)}",
            'div[data-component-type="s-search-result"]')
            if not content:
                return products

            soup = BeautifulSoup(content, "lxml")
            items = soup.select('div[data-component-type="s-search-result"]')
            logging.info(f"Trouvé {len(items)} éléments sur Amazon pour: {query}")

            for item in items[:limit]:
                product = self.parse_item(item)
                if product:
                    products.append(product)

            if products:
                logging.info(" Enregistrement des produits dans MongoDB...")
                await save_to_mongo(self.db_manager,products)

        except Exception as e:
            logging.error(f"Erreur lors du scraping d'Amazon: {str(e)}")
            raise
        return products

    def parse_item(self, item) -> Optional[Dict[str, Any]]:
        product = Product(source="amazon")
        try:
            # Get product id
            asin = item.get("data-asin", "")
            product.product_id = asin if asin else None

            # Titre
            product.name = item.h2.text.strip() if item.h2 else ""

            livraison = item.select_one('div[data-cy="delivery-recipe"]')
            livraison = livraison.text if livraison else None
            product.delivery_price = (
                "".join(livraison.strip().split(" ")[2:]) if livraison else None
            )

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
        product = Product(source="amazon")
        try:
            # Récupérer l'URL canonique du produit
            canonical_link = soup.select_one('link[rel="canonical"]')
            product.url = canonical_link.get("href") if canonical_link else None

            #  Extraction de l'ASIN (ID du produit)
            product.product_id = None

            #  Méthode principale : `#all-offers-display-params`
            asin_element = soup.select_one("#all-offers-display-params")
            if asin_element:
                product.product_id = asin_element.get("data-asin")

            #  Méthode alternative : `input[name="ASIN"]`
            if not product.product_id:
                asin_input = soup.select_one('input[name="ASIN"]')
                if asin_input:
                    product.product_id = asin_input.get("value")

            #  Vérification finale
            if not product.product_id:
                logging.warning(f" Impossible de récupérer l'ID du produit pour {product.url}.")

            # Récupérer le prix du produit
            price_element = soup.select_one(
                'div[id*="corePrice"] .a-offscreen, div[id*="corePrice"] .aok-offscreen'
            )
            product.price = price_element.text.strip() if price_element else None

            # Catégories
            category_elements = soup.select("#wayfinding-breadcrumbs_feature_div a")
            product.categories = (
                [cat.text.strip() for cat in category_elements] if category_elements else None
            )

            # Nom du produit
            title_element = soup.select_one("#productTitle")
            product.name = title_element.text.strip() if title_element else None

            # Photos détaillées
            image_elements = soup.select("#main-image-container img") + soup.select("#altImages img")
            product.detailed_photos = (
                [img.get("src") for img in image_elements if img.get("src")] if image_elements else None
            )

            # Table des caractéristiques
            product_table = soup.select_one("#productDetails_feature_div table") or soup.select_one("#prodDetails table")
            product.feature_table = self.parse_table(product_table) if product_table else None

            # Couleurs disponibles
            color_elements = soup.select("#variation_color_name ul img")

            # Extraire uniquement le nom des couleurs (List[str])
            product.colors = (
                [color.get("alt", "").strip() for color in color_elements if color.get("alt")]
                if color_elements
                else None
            )

            # Si tu veux stocker aussi les images, utilise un autre champ `colors_images`
            product.colors_images = (
                {color.get("alt", "").strip(): color.get("src", "") for color in color_elements if color.get("alt")}
                if color_elements
                else None
            )



            # Description du produit
            description_element = soup.select_one("#productDescription p")
            product.description = description_element.text.strip() if description_element else None

            return [product.to_dict()]

        except Exception as e:
            logging.error(f" Erreur extraction détail article Amazon : {str(e)}")
            return []


    # async def get_detail(self, product_url) -> List[Dict[str, Any]]:
    #     content = await self.get_page_content(product_url, "#navFooter")
    #     await self.__aexit__()
    #     if not content:
    #         return []
    #     soup = BeautifulSoup(content, "lxml")
    #     return self.parse_details(soup)

    async def get_detail(self, product_url: str) -> List[Dict[str, Any]]:
        """Récupère et met à jour les détails d'un produit Amazon."""
        
        logging.info(f" Récupération du produit : {product_url}")
        content = await self.get_page_content(product_url, "#navFooter")
        
        if not content:
            logging.warning(f" Aucun contenu récupéré pour {product_url}.")
            return []

        soup = BeautifulSoup(content, "lxml")
        details = self.parse_details(soup)

        if not details:
            logging.warning(f" Impossible d'extraire les détails du produit {product_url}.")
            return []

        logging.info(f" Détails extraits : {details}")

        #  Correction : Utilisation de update_product_details()
        updated_details = await self.update_product_details(details[0])  

        return [updated_details]  # Toujours retourner une liste

    
    async def update_product_details(self, detailed_product: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour MongoDB avec les nouvelles données du produit Amazon."""
        try:
            if not isinstance(detailed_product, dict):
                logging.error(f" Erreur: `detailed_product` n'est pas un dictionnaire ! Type reçu : {type(detailed_product)}")
                return {}

            product_id = detailed_product.get("product_id")
            if not product_id:
                logging.warning(" Impossible de récupérer l'ID du produit.")
                return {}

            #  Vérifier que MongoDB est bien initialisé
            if not self.db_manager.is_initialized():
                logging.info("🛠️ Initialisation de MongoDB avec Beanie...")
                await self.db_manager.initialize()

            #  Correction : Convertir `uploaded` en `str` si c'est un `dict`
            if "uploaded" in detailed_product and isinstance(detailed_product["uploaded"], dict):
                uploaded_data = detailed_product["uploaded"]
                detailed_product["uploaded"] = f"{uploaded_data.get('scraped', 'N/A')} - {uploaded_data.get('time', 'N/A')}"

            #  Rechercher si le produit existe déjà en base
            existing_product = await Product_scraping.find_one({"product_id": product_id})

            if existing_product:
                updated_fields = {
                    k: v for k, v in detailed_product.items()
                    if getattr(existing_product, k, None) != v and v is not None
                }

                if updated_fields:
                    try:
                        await existing_product.set(updated_fields)
                        logging.info(f" Produit {product_id} mis à jour avec {len(updated_fields)} nouvelles valeurs.")
                    except Exception as e:
                        logging.error(f" Erreur lors de la mise à jour du produit `{product_id}` dans MongoDB : {e}")
                else:
                    logging.info(f"ℹ️ Aucun changement détecté pour {product_id}.")
            else:
                try:
                    new_product = Product_scraping(**detailed_product)
                    await new_product.insert()
                    logging.info(f"🆕 Produit {product_id} ajouté en base.")
                except Exception as e:
                    logging.error(f" Erreur lors de l'insertion du produit `{product_id}` dans MongoDB : {e}")

            return detailed_product  

        except Exception as e:
            logging.error(f" Erreur inattendue lors de la mise à jour du produit `{product_id}` : {e}")
            return {}

