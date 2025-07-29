"""
Configuration centralisée pour l'application FastAPI
Utilise Pydantic Settings pour la validation des variables d'environnement
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Configuration générale
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    API_SECRET_KEY: str = Field(..., env="API_SECRET_KEY")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Configuration serveur
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="BACKEND_PORT")
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"], 
        env="ALLOWED_HOSTS"
    )
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"], 
        env="CORS_ORIGINS"
    )
    
    # Configuration base de données
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=30, env="DB_MAX_OVERFLOW")
    
    # Configuration Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_TTL: int = Field(default=3600, env="REDIS_TTL")  # 1 heure
    
    # Configuration JWT
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRE_HOURS: int = Field(default=24, env="JWT_EXPIRE_HOURS")
    
    # Configuration CELO Blockchain
    CELO_NETWORK: str = Field(default="alfajores", env="CELO_NETWORK")
    CELO_RPC_URL: str = Field(..., env="CELO_RPC_URL")
    CELO_MAINNET_RPC_URL: Optional[str] = Field(None, env="CELO_MAINNET_RPC_URL")
    PRIVATE_KEY: Optional[str] = Field(None, env="PRIVATE_KEY")
    CONTRACT_ADDRESS: Optional[str] = Field(None, env="CONTRACT_ADDRESS")
    
    # Configuration IPFS
    IPFS_GATEWAY: str = Field(
        default="https://gateway.pinata.cloud", 
        env="IPFS_GATEWAY"
    )
    PINATA_API_KEY: Optional[str] = Field(None, env="PINATA_API_KEY")
    PINATA_SECRET_KEY: Optional[str] = Field(None, env="PINATA_SECRET_KEY")
    IPFS_PROJECT_ID: Optional[str] = Field(None, env="IPFS_PROJECT_ID")
    IPFS_PROJECT_SECRET: Optional[str] = Field(None, env="IPFS_PROJECT_SECRET")
    
    # Configuration sécurité
    ENCRYPTION_KEY: str = Field(..., env="ENCRYPTION_KEY")
    SALT_ROUNDS: int = Field(default=12, env="SALT_ROUNDS")
    
    # Configuration email (optionnel)
    SMTP_HOST: Optional[str] = Field(None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    
    # Configuration monitoring (optionnel)
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    TENDERLY_ACCESS_KEY: Optional[str] = Field(None, env="TENDERLY_ACCESS_KEY")
    
    # Configuration upload de fichiers
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "jpg", "jpeg", "png", "doc", "docx"],
        env="ALLOWED_FILE_TYPES"
    )
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("DEBUG", pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @property
    def is_production(self) -> bool:
        """Vérifie si l'environnement est en production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def database_config(self) -> dict:
        """Configuration pour la base de données"""
        return {
            "url": self.DATABASE_URL,
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW
        }
    
    @property
    def redis_config(self) -> dict:
        """Configuration pour Redis"""
        return {
            "url": self.REDIS_URL,
            "default_ttl": self.REDIS_TTL
        }
    
    @property
    def blockchain_config(self) -> dict:
        """Configuration pour la blockchain CELO"""
        return {
            "network": self.CELO_NETWORK,
            "rpc_url": self.CELO_RPC_URL,
            "contract_address": self.CONTRACT_ADDRESS,
            "private_key": self.PRIVATE_KEY
        }
    
    @property
    def ipfs_config(self) -> dict:
        """Configuration pour IPFS"""
        return {
            "gateway": self.IPFS_GATEWAY,
            "pinata_api_key": self.PINATA_API_KEY,
            "pinata_secret_key": self.PINATA_SECRET_KEY,
            "project_id": self.IPFS_PROJECT_ID,
            "project_secret": self.IPFS_PROJECT_SECRET
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Instance globale des settings
settings = Settings()

# Validation des configurations critiques
def validate_critical_settings():
    """Valide les configurations critiques au démarrage"""
    errors = []
    
    # Vérification des clés de sécurité
    if not settings.API_SECRET_KEY or len(settings.API_SECRET_KEY) < 32:
        errors.append("API_SECRET_KEY doit contenir au moins 32 caractères")
    
    if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 32:
        errors.append("JWT_SECRET doit contenir au moins 32 caractères")
    
    if not settings.ENCRYPTION_KEY or len(settings.ENCRYPTION_KEY) < 32:
        errors.append("ENCRYPTION_KEY doit contenir au moins 32 caractères")
    
    # Vérification de la configuration blockchain
    if not settings.CELO_RPC_URL:
        errors.append("CELO_RPC_URL est requis")
    
    # Vérification de la base de données
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL est requis")
    
    if errors:
        raise ValueError(f"Erreurs de configuration: {', '.join(errors)}")

# Validation au chargement du module
try:
    validate_critical_settings()
except ValueError as e:
    print(f"❌ {e}")
    exit(1)
