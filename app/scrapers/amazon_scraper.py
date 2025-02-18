from typing import List, Dict, Any, Optional
import logging
import aiohttp
from bs4 import BeautifulSoup

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
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")

                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    items = soup.select('div[data-component-type="s-search-result"]')
                    logging.info(f"Found {len(items)} items on Amazon for query: {query}")

                    for item in items[:limit]:
                        product = self.parse_item(item)
                        if product:
                            products.append(product)

        except Exception as e:
            logging.error(f"Error scraping Amazon: {str(e)}")
            raise

        return products

    def parse_item(self, item) -> Optional[Dict[str, Any]]:
        try:
            # Title
            title = item.h2.text.strip() if item.h2 else ""
            # product url
            href = item.select_one('div[data-cy="title-recipe"] a.a-text-normal').get('href', '')
            product_url = self.BASE_URL + href if href and not href.startswith('http') else href
            image_url = item.select_one('img.s-image').get('src', '') if item.select_one('img.s-image') else ""
            # procudt price
            price = item.find('span', 'a-offscreen').text.strip() if item.find('span', 'a-offscreen') else ""
            # stock availability
            stock = not bool(item.select_one('.s-item__out-of-stock'))

            if title and product_url:
                logging.info(f"🛒 {title} - {price} - {stock} - {product_url[:10]}... -")
                return {
                    "name": title,
                    "price": price,
                    "stock": stock,
                    "image_url": image_url,
                    "product_url": product_url,
                    "source": "amazon"
                }
        except Exception as e:
            logging.error(f"Error parsing Amazon item: {str(e)}")
            return None

amazon_scraper = AmazonScraper()
