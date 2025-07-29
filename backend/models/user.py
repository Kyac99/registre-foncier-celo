"""
Modèle SQLAlchemy pour les utilisateurs
"""

from sqlalchemy import Column, String, Boolean, DateTime, UUID, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base
import uuid as uuid_pkg

class User(Base):
    """Modèle pour les utilisateurs du système"""
    
    __tablename__ = "users"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    
    # Informations blockchain
    wallet_address = Column(String(42), unique=True, nullable=False, index=True)
    
    # Informations personnelles
    email = Column(String(255), unique=True, nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Rôle et statut
    role = Column(String(50), default="citizen", nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    properties = relationship("Property", back_populates="owner", lazy="dynamic")
    transactions = relationship("PropertyTransaction", back_populates="user", lazy="dynamic")
    documents = relationship("Document", back_populates="uploader", lazy="dynamic")
    
    def __repr__(self):
        return f"<User {self.wallet_address[:10]}...>"
    
    @property
    def full_name(self):
        """Nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.wallet_address[:10] + "..."
    
    @property
    def is_notary(self):
        """Vérifie si l'utilisateur est un notaire"""
        return self.role == "notary"
    
    @property
    def is_admin(self):
        """Vérifie si l'utilisateur est un administrateur"""
        return self.role == "admin"
    
    @property
    def is_surveyor(self):
        """Vérifie si l'utilisateur est un géomètre"""
        return self.role == "surveyor"
    
    def to_dict(self, include_sensitive=False):
        """Convertit le modèle en dictionnaire"""
        data = {
            "id": str(self.id),
            "wallet_address": self.wallet_address,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "full_name": self.full_name
        }
        
        if include_sensitive:
            data.update({
                "email": self.email,
                "phone": self.phone,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "last_login": self.last_login.isoformat() if self.last_login else None
            })
        
        return data
