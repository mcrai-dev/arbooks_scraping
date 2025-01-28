from typing import List, Dict, Any
import logging
import json
import urllib.parse
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

class VintedScraper:
    BASE_URL = "https://www.vinted.fr"
    SEARCH_URL = "https://www.vinted.fr/catalog"
    
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        products = []
        params = {
            'search_text': query,
            'order': 'newest_first'
        }
        
        # Headers that mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Cookie': '_vinted_fr_session=test',  # Ajoutez un cookie de session valide ici
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.SEARCH_URL, params=params, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Parse the HTML with BeautifulSoup
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Find all product items
                        items = (
                            soup.select('.feed-grid__item') or
                            soup.select('.feed-grid__item--small') or
                            soup.select('[data-testid="item-card"]')
                        )
                        
                        logging.info(f"Found {len(items)} items on Vinted for query: {query}")
                        
                        for item in items[:limit]:
                            try:
                                # Extract title
                                title_elem = (
                                    item.select_one('.web_ui__Text__text') or
                                    item.select_one('.Text_text__QBn1m') or
                                    item.select_one('h3')
                                )
                                title = title_elem.text.strip() if title_elem else ""
                                
                                # Extract price
                                price_elem = (
                                    item.select_one('.web_ui__Text--subtitle-2') or
                                    item.select_one('[data-testid="item-price"]')
                                )
                                
                                price = 0.0
                                if price_elem:
                                    price_text = price_elem.text.strip()
                                    try:
                                        # Remove currency symbols and spaces, replace comma with dot
                                        price_text = price_text.replace('€', '').replace(' ', '').replace(',', '.')
                                        # Extract first number found
                                        number = re.search(r'\d+\.?\d*', price_text)
                                        if number:
                                            price = float(number.group())
                                    except:
                                        pass
                                
                                # Extract link
                                link_elem = item.select_one('a')
                                product_url = ""
                                if link_elem:
                                    href = link_elem.get('href', '')
                                    if href:
                                        product_url = self.BASE_URL + href if not href.startswith('http') else href
                                
                                # Extract image
                                img_elem = item.select_one('img')
                                image_url = ""
                                if img_elem:
                                    image_url = (
                                        img_elem.get('src') or
                                        img_elem.get('data-src') or
                                        ""
                                    )
                                
                                if title and product_url:
                                    products.append({
                                        "name": title,
                                        "price": price,
                                        "stock": True,  # Sur Vinted, si l'article est listé, il est disponible
                                        "image_url": image_url,
                                        "product_url": product_url,
                                        "source": "vinted"
                                    })
                                
                            except Exception as e:
                                logging.error(f"Error parsing Vinted item: {str(e)}")
                                continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                        
        except Exception as e:
            logging.error(f"Error scraping Vinted: {str(e)}")
            raise Exception(f"Error scraping Vinted: {str(e)}")
            
        return products

vinted_scraper = VintedScraper()
