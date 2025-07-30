"""
Modèle de données pour les utilisateurs du système
Gestion des rôles et authentification Web3
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from enum import Enum

from config.database import Base

class UserRole(str, Enum):
    """Rôles des utilisateurs dans le système"""
    CITIZEN = "citizen"
    NOTARY = "notary"
    SURVEYOR = "surveyor"
    TAX_AUTHORITY = "tax_authority"
    ADMIN = "admin"

class User(Base):
    """
    Modèle pour les utilisateurs du système
    Lié aux adresses de wallet pour l'authentification Web3
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identité blockchain
    wallet_address = Column(String(42), unique=True, nullable=False, index=True)
    
    # Informations personnelles
    email = Column(String(255), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Rôle et statut
    role = Column(String(50), nullable=False, default=UserRole.CITIZEN)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Métadonnées de vérification
    verified_by = Column(String(42), nullable=True)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    verification_documents = Column(Text, nullable=True)  # Hash IPFS des documents
    
    # Métadonnées système
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(wallet_address='{self.wallet_address}', role='{self.role}')>"
    
    @property
    def full_name(self):
        """Nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.wallet_address[:10] + "..."
    
    @property
    def can_register_property(self):
        """Vérifie si l'utilisateur peut enregistrer des propriétés"""
        return self.role in [UserRole.NOTARY, UserRole.ADMIN] and self.is_verified
    
    @property
    def can_verify_property(self):
        """Vérifie si l'utilisateur peut vérifier des propriétés"""
        return self.role in [UserRole.SURVEYOR, UserRole.ADMIN] and self.is_verified
    
    @property
    def can_manage_users(self):
        """Vérifie si l'utilisateur peut gérer d'autres utilisateurs"""
        return self.role == UserRole.ADMIN
    
    def to_dict(self, include_sensitive=False):
        """Convertit le modèle en dictionnaire pour l'API"""
        data = {
            "id": str(self.id),
            "wallet_address": self.wallet_address,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "role": self.role,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "permissions": {
                "can_register_property": self.can_register_property,
                "can_verify_property": self.can_verify_property,
                "can_manage_users": self.can_manage_users
            }
        }
        
        # Informations sensibles (seulement pour l'utilisateur lui-même ou admin)
        if include_sensitive:
            data.update({
                "email": self.email,
                "phone": self.phone,
                "verified_by": self.verified_by,
                "verification_date": self.verification_date.isoformat() if self.verification_date else None,
                "last_login": self.last_login.isoformat() if self.last_login else None
            })
        
        return data
