# E-commerce Scraping API

API permettant de récupérer des informations produits depuis différentes plateformes e-commerce françaises.

## Plateformes supportées

- Leboncoin.fr
- Amazon.fr
- Vinted.fr
- Temu.com
- SNCF Connect
- Shein.com
- Cdiscount.com

## Installation

1. Cloner le repository
2. Installer les dépendances :
```bash
pip install -r requirements.txt
```
3. Installer les dépendances de Playwright :
```bash
playwright install
```

## Démarrage

```bash
uvicorn app.main:app --reload
```

L'API sera accessible à l'adresse : http://localhost:8000

## Documentation API

La documentation Swagger est disponible à l'adresse : http://localhost:8000/docs

### Endpoints

#### GET /search/{platform}/{query}

Recherche des produits sur une plateforme spécifique.

Paramètres :
- platform : nom de la plateforme (leboncoin, amazon, vinted, etc.)
- query : terme de recherche
- limit : nombre maximum de résultats (défaut: 1000)

Exemple de réponse :
```json
[
    {
        "name": "Nom du produit",
        "price": 99.99,
        "stock": true,
        "image_url": "https://example.com/image.jpg",
        "product_url": "https://example.com/product",
        "source": "leboncoin"
    }
]
```

## Notes de sécurité

Cette API utilise undetected-playwright pour contourner les protections anti-bot. Utilisez-la de manière responsable et respectez les conditions d'utilisation des sites concernés.
# arbooks_scraping
# arbooks_scraping
