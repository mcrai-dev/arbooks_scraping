from playwright.async_api import async_playwright, Browser, Page, TimeoutError, Playwright
from typing import List, Dict, Any
import asyncio
import logging
import random
import json

class BaseScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self._playwright = None
        
    async def init_browser(self):
        if not self._playwright:
            self._playwright = await async_playwright().start()
        
        # Enhanced browser arguments for better stealth
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--hide-scrollbars',
            '--mute-audio',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-update',
            '--disable-default-apps',
            '--disable-domain-reliability',
            '--disable-extensions',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-notifications',
            '--disable-offer-store-unmasked-wallet-cards',
            '--disable-popup-blocking',
            '--disable-print-preview',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-speech-api',
            '--disable-sync',
            '--disable-translate',
            '--disable-webgl',
            '--metrics-recording-only',
            '--no-default-browser-check',
            '--no-experiments',
            '--no-pings',
            '--password-store=basic',
            '--use-gl=swiftshader',
            '--use-mock-keychain',
        ]
        
        self.browser = await self._playwright.chromium.launch(
            headless=True,
            args=browser_args
        )
        
        # Create an incognito context with enhanced privacy
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='fr-FR',
            timezone_id='Europe/Paris',
            geolocation={'latitude': 48.8566, 'longitude': 2.3522},
            permissions=['geolocation'],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
        )
        
        # Add stealth scripts
        await self.add_stealth_scripts()
        
    async def add_stealth_scripts(self):
        # Add various scripts to make automation harder to detect
        await self.context.add_init_script("""
            // Override properties
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en-US', 'en'] });
            
            // Add Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            
            // Add fake web APIs
            window.navigator.mediaDevices = {
                ...window.navigator.mediaDevices,
                enumerateDevices: async () => []
            };
        """)
        
    async def get_page_content(self, url: str, wait_for: str = None, timeout: int = 30000) -> str:
        if not self.browser:
            await self.init_browser()
            
        page = await self.context.new_page()
        
        try:
            # Add random delays
            await asyncio.sleep(random.uniform(1, 3))
            
            # Navigate with timeout
            response = await page.goto(url, timeout=timeout, wait_until='networkidle')
            if not response:
                raise Exception("Failed to load page")
            
            if response.status >= 400:
                raise Exception(f"HTTP {response.status}: {await response.text()}")
                
            # Wait for specific element if specified
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)
                
            # Simulate human-like scrolling
            await self.simulate_scrolling(page)
            
            # Get the page content
            content = await page.content()
            return content
            
        except TimeoutError as e:
            logging.error(f"Timeout while loading {url}: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error while loading {url}: {str(e)}")
            raise
        finally:
            await page.close()
            
    async def simulate_scrolling(self, page: Page):
        # Get page height
        height = await page.evaluate('document.documentElement.scrollHeight')
        
        # Scroll in chunks with random delays
        for i in range(0, height, random.randint(200, 800)):
            await page.evaluate(f'window.scrollTo(0, {i})')
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
        # Scroll back to top
        await page.evaluate('window.scrollTo(0, 0)')
        
    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
            self.browser = None
            self.context = None
            self._playwright = None
            
    def parse_price(self, price_str: str) -> float:
        """Convert price string to float"""
        try:
            # Remove currency symbols and spaces, replace comma with dot
            price_str = price_str.replace('€', '').replace(' ', '').replace(',', '.')
            # Extract first number found
            import re
            number = re.search(r'\d+\.?\d*', price_str)
            if number:
                return float(number.group())
            return 0.0
        except Exception:
            return 0.0
            
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Base search method to be implemented by each scraper"""
        raise NotImplementedError("Each scraper must implement its own search method")
