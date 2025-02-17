from playwright.async_api import async_playwright
from playwright_stealth import stealth
import asyncio
import random
import logging

class BaseScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self._playwright = None

    async def init_browser(self):
        logging.info("Démarrage du navigateur Playwright avec mode furtif...")

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        self.browser = await self._playwright.chromium.launch(
            headless=False,  # False pour voir ce qu'il se passe
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-features=site-per-process",
                "--disable-extensions",
                "--incognito"
            ]
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        page = await self.context.new_page()
        
        logging.info("🔍 Chargement de Leboncoin pour récupérer les en-têtes HTTP...")
        await page.goto("https://www.leboncoin.fr/recherche/?text=maison&sort=time&order=desc", wait_until="domcontentloaded")

        # 📌 Capturer les en-têtes HTTP et chercher `Datadome`
        headers = await page.evaluate("() => Object.fromEntries([...new Headers(document.head.querySelectorAll('meta[http-equiv]'))])")

        datadome_token = headers.get("x-datadome") or headers.get("Datadome")

        if datadome_token:
            logging.info(f"✅ Token Datadome récupéré : {datadome_token}")
            self.datadome_token = datadome_token
        else:
            logging.warning("⚠️ Impossible de récupérer le token Datadome ! Leboncoin bloque peut-être l'accès.")

        await page.close()


    async def get_page_content(self, url: str, wait_for: str = None):
        if not self.browser:
            await self.init_browser()

        page = await self.context.new_page()
        await stealth(page)  # Active le mode furtif

        try:
            logging.info(f"🔍 Accès à : {url}")
            await asyncio.sleep(random.uniform(2, 5))  # Délai aléatoire
            
            # 📌 Ajouter le token Datadome si disponible
            if hasattr(self, "datadome_token"):
                headers = {
                    "x-datadome": self.datadome_token,
                    "Referer": "https://www.leboncoin.fr/",
                    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Cache-Control": "max-age=0"
                }
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000, headers=headers)
            else:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # ✅ Vérifier si la réponse est vide
            if response is None:
                logging.error("⚠️ La page n'a pas répondu (response=None)")
                raise Exception("⚠️ La page n'a pas répondu (response=None)")

            # ✅ Enregistrer le statut HTTP
            status_code = response.status
            body_text = await response.text()

            logging.info(f"📄 Réponse reçue : HTTP {status_code}")
            logging.info(f"🔎 Extrait de la réponse : {body_text[:500]}")  # Afficher les 500 premiers caractères

            if status_code >= 400:
                logging.error(f"🚨 Erreur HTTP {status_code} reçue ! Réponse: {body_text[:500]}")
                raise Exception(f"🚨 Leboncoin a renvoyé un code HTTP {status_code}")

            # ✅ Vérifier la présence d'un Captcha Datadome
            page_content = await page.content()
            if "captcha" in page_content.lower() or "Datadome" in page_content:
                logging.warning("⚠️ Captcha détecté !")
                await page.screenshot(path="captcha_detected.png")  # Capture d’écran du problème
                raise Exception("🚫 Leboncoin bloque l'accès via Captcha")

            logging.info("✅ Page chargée avec succès !")
            return page_content

        except Exception as e:
            logging.error(f"❌ Erreur lors du scraping de {url}: {str(e)}")
            raise Exception(f"Error scraping Leboncoin: {str(e)}")
        finally:
            await page.close()


    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
