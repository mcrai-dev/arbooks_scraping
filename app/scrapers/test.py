import asyncio
from vinted_scraper import vinted_scraper

async def test_vinted():
    results = await vinted_scraper.search("nike", limit=5)
    print("🔹 Résultats : ", results)

asyncio.run(test_vinted())
