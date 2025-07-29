"""
Configuration de la base de données PostgreSQL avec SQLAlchemy
Support asyncio et PostGIS pour les données géospatiales
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from .settings import settings

# Configuration du logging
logger = logging.getLogger(__name__)

# Métadonnées pour les tables
metadata = MetaData()

class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy"""
    metadata = metadata

# Création du moteur de base de données
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    poolclass=QueuePool,
    pool_pre_ping=True,  # Vérification des connexions
    pool_recycle=3600,   # Recyclage des connexions après 1h
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency pour obtenir une session de base de données
async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Générateur de session de base de données pour les endpoints FastAPI
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Erreur de base de données: {e}")
            raise
        finally:
            await session.close()

# Gestionnaire de contexte pour les transactions
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Gestionnaire de contexte pour les opérations de base de données
    en dehors des endpoints FastAPI
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Erreur de transaction: {e}")
            raise
        finally:
            await session.close()

# Fonction d'initialisation de la base de données
async def init_db():
    """
    Initialise la base de données et crée les tables
    """
    try:
        logger.info("🔄 Initialisation de la base de données...")
        
        # Import des modèles pour s'assurer qu'ils sont enregistrés
        from models import user, property, transaction, document, blockchain_event
        
        # Création des tables si elles n'existent pas
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Base de données initialisée avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        raise

# Fonction pour tester la connexion
async def test_connection():
    """
    Teste la connexion à la base de données
    """
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("✅ Connexion à la base de données réussie")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        return False

# Fonction pour fermer les connexions
async def close_db():
    """
    Ferme toutes les connexions à la base de données
    """
    await engine.dispose()
    logger.info("🔌 Connexions à la base de données fermées")

# Configuration des événements SQLAlchemy
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configure les pragmas SQLite si utilisé (pour les tests)
    """
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Helper pour les requêtes géospatiales
class GeospatialHelper:
    """
    Helper pour les requêtes géospatiales avec PostGIS
    """
    
    @staticmethod
    def point_from_coords(longitude: float, latitude: float) -> str:
        """
        Crée un point PostGIS à partir des coordonnées
        """
        return f"POINT({longitude} {latitude})"
    
    @staticmethod
    def polygon_from_coords(coordinates: list) -> str:
        """
        Crée un polygone PostGIS à partir d'une liste de coordonnées
        """
        coords_str = ",".join([f"{lon} {lat}" for lon, lat in coordinates])
        return f"POLYGON(({coords_str}))"
    
    @staticmethod
    def distance_query(point1: str, point2: str) -> str:
        """
        Calcule la distance entre deux points en mètres
        """
        return f"ST_Distance(ST_GeomFromText('{point1}', 4326)::geography, ST_GeomFromText('{point2}', 4326)::geography)"
    
    @staticmethod
    def within_radius_query(point: str, radius_meters: int) -> str:
        """
        Requête pour trouver les propriétés dans un rayon donné
        """
        return f"ST_DWithin(coordinates::geography, ST_GeomFromText('{point}', 4326)::geography, {radius_meters})"

# Cache Redis pour les requêtes fréquentes
class CacheManager:
    """
    Gestionnaire de cache Redis pour optimiser les performances
    """
    
    def __init__(self):
        import redis.asyncio as redis
        self.redis = redis.from_url(settings.REDIS_URL)
    
    async def get(self, key: str):
        """Récupère une valeur du cache"""
        try:
            value = await self.redis.get(key)
            if value:
                import json
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Erreur cache Redis: {e}")
        return None
    
    async def set(self, key: str, value: any, ttl: int = None):
        """Stocke une valeur dans le cache"""
        try:
            import json
            ttl = ttl or settings.REDIS_TTL
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Erreur stockage cache Redis: {e}")
    
    async def delete(self, key: str):
        """Supprime une clé du cache"""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Erreur suppression cache Redis: {e}")
    
    async def clear_pattern(self, pattern: str):
        """Supprime toutes les clés correspondant au pattern"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Erreur nettoyage cache Redis: {e}")

# Instance globale du cache
cache_manager = CacheManager()

# Fonctions utilitaires pour les requêtes
async def execute_raw_query(query: str, params: dict = None):
    """
    Exécute une requête SQL brute
    """
    async with get_db_session() as db:
        result = await db.execute(query, params or {})
        return result.fetchall()

async def count_records(model_class, filters: dict = None):
    """
    Compte le nombre d'enregistrements pour un modèle
    """
    from sqlalchemy import select, func
    
    async with get_db_session() as db:
        query = select(func.count(model_class.id))
        
        if filters:
            for key, value in filters.items():
                if hasattr(model_class, key):
                    query = query.where(getattr(model_class, key) == value)
        
        result = await db.execute(query)
        return result.scalar()
