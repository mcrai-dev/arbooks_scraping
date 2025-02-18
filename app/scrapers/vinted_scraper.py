# from typing import List, Dict, Any
# import logging
# import json
# import urllib.parse
# import asyncio
# import aiohttp
# from bs4 import BeautifulSoup
# import re

# class VintedScraper:
#     BASE_URL = "https://www.vinted.fr"
#     SEARCH_URL = "https://www.vinted.fr/catalog"
    
#     async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
#         products = []
#         params = {
#             'search_text': query,
#             'order': 'newest_first'
#         }
        
#         # Headers that mimic a real browser
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
#             'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
#             'Accept-Encoding': 'gzip, deflate, br',
#             'Connection': 'keep-alive',
#             'Upgrade-Insecure-Requests': '1',
#             'Sec-Fetch-Dest': 'document',
#             'Sec-Fetch-Mode': 'navigate',
#             'Sec-Fetch-Site': 'none',
#             'Sec-Fetch-User': '?1',
#             'Cache-Control': 'max-age=0',
#             'Cookie': '_vinted_fr_session=test',  # Ajoutez un cookie de session valide ici
#         }
        
#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(self.SEARCH_URL, params=params, headers=headers, ssl=False) as response:
#                     if response.status == 200:
#                         content = await response.text()
                        
#                         # Parse the HTML with BeautifulSoup
#                         soup = BeautifulSoup(content, 'html.parser')
                        
#                         # Find all product items
#                         items = (
#                             soup.select('.feed-grid__item') or
#                             soup.select('.feed-grid__item--small') or
#                             soup.select('[data-testid="item-card"]')
#                         )
                        
#                         logging.info(f"Found {len(items)} items on Vinted for query: {query}")
                        
#                         for item in items[:limit]:
#                             try:
#                                 # Extract title
#                                 title_elem = (
#                                     item.select_one('.web_ui__Text__text') or
#                                     item.select_one('.Text_text__QBn1m') or
#                                     item.select_one('h3')
#                                 )
#                                 title = title_elem.text.strip() if title_elem else ""
                                
#                                 # Extract price
#                                 price_elem = (
#                                     item.select_one('.web_ui__Text--subtitle-2') or
#                                     item.select_one('[data-testid="item-price"]')
#                                 )
                                
#                                 price = 0.0
#                                 if price_elem:
#                                     price_text = price_elem.text.strip()
#                                     try:
#                                         # Remove currency symbols and spaces, replace comma with dot
#                                         price_text = price_text.replace('€', '').replace(' ', '').replace(',', '.')
#                                         # Extract first number found
#                                         number = re.search(r'\d+\.?\d*', price_text)
#                                         if number:
#                                             price = float(number.group())
#                                     except:
#                                         pass
                                
#                                 # Extract link
#                                 link_elem = item.select_one('a')
#                                 product_url = ""
#                                 if link_elem:
#                                     href = link_elem.get('href', '')
#                                     if href:
#                                         product_url = self.BASE_URL + href if not href.startswith('http') else href
                                
#                                 # Extract image
#                                 img_elem = item.select_one('img')
#                                 image_url = ""
#                                 if img_elem:
#                                     image_url = (
#                                         img_elem.get('src') or
#                                         img_elem.get('data-src') or
#                                         ""
#                                     )
                                
#                                 if title and product_url:
#                                     products.append({
#                                         "name": title,
#                                         "price": price,
#                                         "stock": True,  # Sur Vinted, si l'article est listé, il est disponible
#                                         "image_url": image_url,
#                                         "product_url": product_url,
#                                         "source": "vinted"
#                                     })
                                
#                             except Exception as e:
#                                 logging.error(f"Error parsing Vinted item: {str(e)}")
#                                 continue
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"HTTP {response.status}: {error_text}")
                        
#         except Exception as e:
#             logging.error(f"Error scraping Vinted: {str(e)}")
#             raise Exception(f"Error scraping Vinted: {str(e)}")
            
#         return products

# vinted_scraper = VintedScraper()





import time
import json
import asyncio
import logging
import concurrent.futures
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class VintedScraper:
    BASE_URL = "https://www.vinted.fr"
    SEARCH_URL = "https://www.vinted.fr/catalog"

    def __init__(self):
        """Initialisation du navigateur avec les options optimisées."""
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")  # Masquer Selenium
        options.add_argument("--headless")  # Exécuter en arrière-plan (mettre False pour voir le navigateur)
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--log-level=3")  # Réduit les logs inutiles

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def _search_sync(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Méthode synchrone pour exécuter le scraping dans un thread séparé."""
        products = []
        search_url = f"{self.SEARCH_URL}?search_text={query}&order=newest_first"
        print(f"🔍 URL demandée : {search_url}")
        self.driver.get(search_url)

        # Attendre que la page charge entièrement
        time.sleep(10)

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'p[data-testid*="description-title"]'))
            )
        except:
            logging.error(" Aucun produit trouvé ! Vérifie si Vinted te bloque.")

        # Récupérer le HTML après chargement
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        # Sauvegarde pour debug
        with open("debug_vinted.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        # Extraire les produits
        items = soup.select('p[data-testid*="description-title"]')
        print(f" Nombre d'éléments trouvés : {len(items)}")

        for item in items[:limit]:
            try:
                title = item.text.strip()

                # Récupérer le prix
                price_elem = item.find_next("p", {"data-testid": lambda x: x and "price-text" in x})
                price_text = price_elem.text.strip().replace("\xa0", " ") if price_elem else "Prix inconnu"

                # Récupérer la taille
                size_elem = item.find_next("p", {"data-testid": lambda x: x and "description-subtitle" in x})
                size_text = size_elem.text.strip() if size_elem else "Taille inconnue"

                # Récupérer le lien du produit
                product_container = item.find_parent("div", {"data-testid": lambda x: x and "description" in x})
                link_elem = product_container.find_previous("a") if product_container else None
                href = link_elem.get('href', '') if link_elem else ""
                product_url = href if href.startswith("http") else self.BASE_URL + href

                # Récupérer l'image
                img_elem = product_container.find_previous("img") if product_container else None
                image_url = img_elem.get("src") if img_elem else ""

                logger.info(f"🛒 {title} - {price_text} - {size_text} - {product_url}")

                products.append({
                    "name": title,
                    "price": price_text,
                    "size": size_text,
                    "image_url": image_url,
                    "product_url": product_url,
                    "source": "vinted"
                })
            except Exception as e:
                logging.error(f" Erreur lors de l'extraction d'un produit : {str(e)}")

        return products

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Méthode asynchrone pour FastAPI."""
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, self._search_sync, query, limit)

    def close(self):
        """Ferme proprement le navigateur."""
        self.driver.quit()


# Création d'une instance utilisable
vinted_scraper = VintedScraper()
