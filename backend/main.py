"""
API Backend pour le Registre Foncier Décentralisé
FastAPI + PostgreSQL + CELO Blockchain + IPFS
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

# Import des modules locaux
from config.settings import settings
from config.database import get_database, init_db
from routers import properties, users, blockchain, documents, search
from middleware.auth import verify_token
from middleware.logging import setup_logging
from services.blockchain_monitor import BlockchainMonitor

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logging
setup_logging()

# Gestionnaire de cycle de vie de l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire du cycle de vie de l'application"""
    # Démarrage
    print("🚀 Démarrage de l'API Registre Foncier Décentralisé")
    
    # Initialisation de la base de données
    await init_db()
    
    # Démarrage du monitoring blockchain
    blockchain_monitor = BlockchainMonitor()
    await blockchain_monitor.start()
    
    print("✅ API prête à recevoir des requêtes")
    yield
    
    # Arrêt
    print("🛑 Arrêt de l'API en cours...")
    await blockchain_monitor.stop()
    print("✅ API arrêtée proprement")

# Création de l'application FastAPI
app = FastAPI(
    title="Registre Foncier Décentralisé - API",
    description="API REST pour la gestion décentralisée des propriétés foncières sur CELO",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Middleware de sécurité pour les hosts autorisés
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Configuration de la sécurité JWT
security = HTTPBearer()

# Inclusion des routeurs
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["Utilisateurs"],
    dependencies=[Depends(get_database)]
)

app.include_router(
    properties.router,
    prefix="/api/v1/properties",
    tags=["Propriétés"],
    dependencies=[Depends(get_database)]
)

app.include_router(
    blockchain.router,
    prefix="/api/v1/blockchain",
    tags=["Blockchain"],
    dependencies=[Depends(get_database)]
)

app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["Documents"],
    dependencies=[Depends(get_database)]
)

app.include_router(
    search.router,
    prefix="/api/v1/search",
    tags=["Recherche"],
    dependencies=[Depends(get_database)]
)

# Routes de base
@app.get("/")
async def root():
    """Route racine - Informations sur l'API"""
    return {
        "name": "Registre Foncier Décentralisé - API",
        "version": "1.0.0",
        "description": "API REST pour la gestion décentralisée des propriétés foncières sur CELO",
        "docs": "/docs" if settings.DEBUG else "Documentation désactivée en production",
        "status": "active",
        "blockchain": {
            "network": settings.CELO_NETWORK,
            "contract_address": settings.CONTRACT_ADDRESS
        }
    }

@app.get("/health")
async def health_check():
    """Vérification de l'état de santé de l'API"""
    try:
        # Test de connexion à la base de données
        db = await get_database()
        await db.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "blockchain_network": settings.CELO_NETWORK,
            "environment": settings.ENVIRONMENT
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service temporairement indisponible: {str(e)}"
        )

@app.get("/api/v1/config")
async def get_public_config():
    """Configuration publique pour le frontend"""
    return {
        "blockchain": {
            "network": settings.CELO_NETWORK,
            "rpc_url": settings.CELO_RPC_URL,
            "contract_address": settings.CONTRACT_ADDRESS
        },
        "ipfs": {
            "gateway": settings.IPFS_GATEWAY
        },
        "features": {
            "registration": True,
            "search": True,
            "verification": True,
            "documents": True
        }
    }

# Gestionnaire d'erreurs global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Gestionnaire global des exceptions"""
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    logger.error(f"Erreur non gérée: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Erreur interne du serveur"
    )

# Point d'entrée pour le développement
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("BACKEND_PORT", 8000)),
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
