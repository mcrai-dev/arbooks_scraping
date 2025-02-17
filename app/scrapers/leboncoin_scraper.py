# from typing import List, Dict, Any
# import logging
# import json
# import urllib.parse
# import asyncio
# import aiohttp
# from bs4 import BeautifulSoup

# class LeboncoinScraper:
#     BASE_URL = "https://www.leboncoin.fr"
    
#     async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
#         products = []
#         encoded_query = urllib.parse.quote(query)
#         search_url = f"{self.BASE_URL}/recherche?text={encoded_query}&sort=time&order=desc"
        
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
#             'Cache-Control': 'max-age=0'
#         }
        
#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(search_url, headers=headers, ssl=False) as response:
#                     if response.status == 200:
#                         content = await response.text()
                        
#                         # Parse the HTML with BeautifulSoup
#                         soup = BeautifulSoup(content, 'html.parser')
                        
#                         # Find all product items
#                         items = (
#                             soup.find_all("div", {"data-qa-id": "aditem_container"}) or
#                             soup.find_all("a", {"data-qa-id": "aditem_container"}) or
#                             soup.find_all("article", {"data-qa-id": "aditem_container"}) or
#                             soup.select("[data-test-id='ad-card']") or
#                             soup.select("div[class*='styles_adCard']")
#                         )
                        
#                         logging.info(f"Found {len(items)} items on Leboncoin for query: {query}")
                        
#                         for item in items[:limit]:
#                             try:
#                                 # Extract title
#                                 title_elem = (
#                                     item.find("p", {"data-qa-id": "aditem_title"}) or
#                                     item.find("span", {"data-qa-id": "aditem_title"}) or
#                                     item.select_one("[class*='AdCardTitle']") or
#                                     item.select_one("p[class*='title']") or
#                                     item.find("h3")
#                                 )
#                                 title = title_elem.text.strip() if title_elem else ""
                                
#                                 # Extract price
#                                 price_elem = (
#                                     item.find("span", {"data-qa-id": "aditem_price"}) or
#                                     item.find("div", {"data-qa-id": "aditem_price"}) or
#                                     item.select_one("[class*='AdCardPrice']") or
#                                     item.select_one("span[class*='price']")
#                                 )
                                
#                                 # Parse price
#                                 price = 0.0
#                                 if price_elem and price_elem.text:
#                                     price_text = price_elem.text.strip()
#                                     try:
#                                         # Remove currency symbols and spaces, replace comma with dot
#                                         price_text = price_text.replace('€', '').replace(' ', '').replace(',', '.')
#                                         # Extract first number found
#                                         import re
#                                         number = re.search(r'\d+\.?\d*', price_text)
#                                         if number:
#                                             price = float(number.group())
#                                     except:
#                                         price = 0.0
                                
#                                 # Extract link
#                                 link_elem = item.find("a") or item
#                                 product_url = ""
#                                 if link_elem:
#                                     href = link_elem.get("href", "")
#                                     if href:
#                                         product_url = self.BASE_URL + href if not href.startswith('http') else href
                                
#                                 # Extract image
#                                 img_elem = (
#                                     item.find("img") or
#                                     item.select_one("[class*='AdCardImage'] img")
#                                 )
#                                 image_url = ""
#                                 if img_elem:
#                                     image_url = (
#                                         img_elem.get("src") or
#                                         img_elem.get("data-src") or
#                                         img_elem.get("data-lazy-src") or
#                                         ""
#                                     )
                                
#                                 if title and product_url:
#                                     products.append({
#                                         "name": title,
#                                         "price": price,
#                                         "stock": True,
#                                         "image_url": image_url,
#                                         "product_url": product_url,
#                                         "source": "leboncoin"
#                                     })
                                
#                             except Exception as e:
#                                 logging.error(f"Error parsing Leboncoin item: {str(e)}")
#                                 continue
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"HTTP {response.status}: {error_text}")
                        
#         except Exception as e:
#             logging.error(f"Error scraping Leboncoin: {str(e)}")
#             raise Exception(f"Error scraping Leboncoin: {str(e)}")
            
#         return products

# leboncoin_scraper = LeboncoinScraper()





from app.scrapers.base_scraper_leboncoin import BaseScraper
import logging
import json
import asyncio

class LeboncoinScraper(BaseScraper):
    BASE_URL = "https://www.leboncoin.fr/recherche/?text="

    async def search(self, query: str, limit: int = 100):
        """Recherche des annonces sur Leboncoin en utilisant Playwright"""
        products = []
        search_url = f"{self.BASE_URL}{query.replace(' ', '+')}&sort=time&order=desc"

        try:
            logging.info(f" Scraping Leboncoin: {search_url}")

            #  Vérifier que le navigateur est bien lancé
            await self.init_browser()  # Ajouté ici

            html_content = await self.get_page_content(search_url, wait_for="section div.sc-bdVaJa.sc-hrWEMg.kVdJlA")

            if not html_content:
                raise Exception("Failed to load Leboncoin search results")

            # Analyser le JSON renvoyé par Leboncoin
            try:
                soup = json.loads(html_content)
            except json.JSONDecodeError:
                raise Exception("Invalid JSON response from Leboncoin")

            # Récupérer les annonces
            ads = soup.get("props", {}).get("pageProps", {}).get("annonces", [])

            for ad in ads[:limit]:
                try:
                    title = ad.get("subject", "N/A")
                    price = ad.get("price", 0)
                    product_url = f"https://www.leboncoin.fr/annonce/{ad.get('list_id')}"
                    image_url = ad.get("images", [{}])[0].get("url", "")

                    products.append({
                        "name": title,
                        "price": price,
                        "stock": True,
                        "image_url": image_url,
                        "product_url": product_url,
                        "source": "leboncoin"
                    })

                except Exception as e:
                    logging.error(f"Erreur en analysant une annonce Leboncoin: {str(e)}")
                    continue

        except Exception as e:
            logging.error(f" Erreur lors du scraping de Leboncoin: {str(e)}")
            raise Exception(f"Error scraping Leboncoin: {str(e)}")

        return products

# Instancier le scraper
leboncoin_scraper = LeboncoinScraper()
