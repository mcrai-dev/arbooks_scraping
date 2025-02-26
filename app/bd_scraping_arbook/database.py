import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.bd_scraping_arbook.models_vinted import Product
from app.bd_scraping_arbook.models_amazon import AmazonProduct
from app.bd_scraping_arbook.models_scraping import Product_scraping

class DatabaseManager:
    _instance = None  
    _initialized = False  # ✅ Flag global pour éviter plusieurs initialisations

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, connection_string="mongodb://localhost:27017", database_name="scraping_arbook"):
        if not hasattr(self, "_client"):  # ✅ Vérification unique
            self.connection_string = connection_string
            self.database_name = database_name
            self._client: Optional[AsyncIOMotorClient] = None

    async def initialize(self) -> bool:
        """Initialise MongoDB et Beanie si ce n'est pas déjà fait."""
        if DatabaseManager._initialized:
            logging.info("✅ MongoDB est déjà initialisé.")
            return True

        try:
            self._client = AsyncIOMotorClient(self.connection_string)
            database = self._client[self.database_name]

            # ✅ Initialiser Beanie une seule fois
            await init_beanie(database, document_models=[Product_scraping])

            DatabaseManager._initialized = True  # ✅ Mise à jour du flag global
            logging.info("🚀 MongoDB & Beanie initialisés avec succès !")
            return True
        except Exception as e:
            logging.error(f"🚨 Erreur d'initialisation de MongoDB : {e}")
            return False

    def get_client(self) -> Optional[AsyncIOMotorClient]:
        """Retourne le client MongoDB si connecté, sinon None."""
        if not DatabaseManager._initialized:
            logging.warning("⚠️ MongoDB n'est PAS initialisé ! Appelez `initialize()` d'abord.")
            return None
        return self._client

    def is_initialized(self) -> bool:
        """Retourne True si la base est initialisée, sinon False."""
        return DatabaseManager._initialized

    async def close(self):
        """Ferme la connexion à MongoDB."""
        if self._client:
            self._client.close()
            logging.info("🔌 Connexion MongoDB fermée.")
            self._client = None
            DatabaseManager._initialized = False  # Réinitialisation
