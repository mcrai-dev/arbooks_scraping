from typing import List, Dict, Any
import logging
import json
import urllib.parse
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

class AmazonScraper:
    BASE_URL = "https://www.amazon.fr"
    SEARCH_URL = "https://www.amazon.fr/s"
    
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        products = []
        params = {
            'k': query,
            'ref': 'nb_sb_noss',
            'sprefix': f'{query},aps,283',
            'crid': '2M7LQQC1YQLR0'
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
            'rtt': '50',
            'downlink': '10',
            'ect': '4g',
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.SEARCH_URL, params=params, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Parse the HTML with BeautifulSoup
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Find all product items
                        items = soup.select('div[data-component-type="s-search-result"]')
                        
                        logging.info(f"Found {len(items)} items on Amazon for query: {query}")
                        
                        for item in items[:limit]:
                            try:
                                # Extract title
                                title_elem = item.select_one('h2 a span')
                                title = title_elem.text.strip() if title_elem else ""
                                
                                # Extract price
                                price = 0.0
                                price_whole = item.select_one('.a-price-whole')
                                price_fraction = item.select_one('.a-price-fraction')
                                
                                if price_whole:
                                    price_text = price_whole.text.strip()
                                    if price_fraction:
                                        price_text += "." + price_fraction.text.strip()
                                    try:
                                        price = float(price_text.replace(',', '').replace('€', ''))
                                    except:
                                        pass
                                
                                # Extract link
                                link_elem = item.select_one('h2 a')
                                product_url = ""
                                if link_elem:
                                    href = link_elem.get('href', '')
                                    if href:
                                        product_url = self.BASE_URL + href if not href.startswith('http') else href
                                
                                # Extract image
                                img_elem = item.select_one('img.s-image')
                                image_url = img_elem.get('src', '') if img_elem else ""
                                
                                # Extract stock status
                                stock = True
                                unavailable = item.select_one('.s-item__out-of-stock')
                                if unavailable:
                                    stock = False
                                
                                if title and product_url:
                                    products.append({
                                        "name": title,
                                        "price": price,
                                        "stock": stock,
                                        "image_url": image_url,
                                        "product_url": product_url,
                                        "source": "amazon"
                                    })
                                
                            except Exception as e:
                                logging.error(f"Error parsing Amazon item: {str(e)}")
                                continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                        
        except Exception as e:
            logging.error(f"Error scraping Amazon: {str(e)}")
            raise Exception(f"Error scraping Amazon: {str(e)}")
            
        return products

amazon_scraper = AmazonScraper()
