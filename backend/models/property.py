"""
Modèle de données pour les propriétés foncières
Intégration avec PostGIS pour les données géospatiales
"""

from sqlalchemy import Column, String, Integer, BigInteger, DECIMAL, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid
from datetime import datetime
from enum import Enum

from config.database import Base

class PropertyType(str, Enum):
    """Types de propriétés foncières"""
    RESIDENTIAL = "RESIDENTIAL"
    COMMERCIAL = "COMMERCIAL"
    INDUSTRIAL = "INDUSTRIAL"
    AGRICULTURAL = "AGRICULTURAL"
    FOREST = "FOREST"
    OTHER = "OTHER"

class PropertyStatus(str, Enum):
    """Statuts des propriétés"""
    ACTIVE = "ACTIVE"
    DISPUTED = "DISPUTED"
    FROZEN = "FROZEN"
    TRANSFERRED = "TRANSFERRED"

class Property(Base):
    """
    Modèle pour les propriétés foncières
    Cache local des données blockchain avec enrichissement
    """
    __tablename__ = "properties"

    id = Column(BigInteger, primary_key=True, index=True)
    blockchain_id = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Informations de propriété
    owner_address = Column(String(42), nullable=False, index=True)
    location = Column(Text, nullable=False)
    coordinates = Column(Geometry('POLYGON', srid=4326), nullable=True)
    area = Column(DECIMAL(15, 2), nullable=False)  # Surface en m²
    value = Column(DECIMAL(20, 2), nullable=True)  # Valeur en cUSD (wei)
    
    # Classification
    property_type = Column(String(50), nullable=False, default=PropertyType.RESIDENTIAL)
    status = Column(String(50), nullable=False, default=PropertyStatus.ACTIVE)
    
    # Métadonnées blockchain
    registration_date = Column(DateTime(timezone=True), nullable=True)
    last_transfer_date = Column(DateTime(timezone=True), nullable=True)
    document_hash = Column(String(100), nullable=True)
    ipfs_hash = Column(String(100), nullable=True)
    registrar_address = Column(String(42), nullable=True)
    
    # Vérification et validation
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(42), nullable=True)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    
    # Métadonnées système
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relations
    transactions = relationship("PropertyTransaction", back_populates="property")
    documents = relationship("Document", back_populates="property")
    
    def __repr__(self):
        return f"<Property(id={self.id}, blockchain_id={self.blockchain_id}, location='{self.location[:50]}')>"
    
    @property
    def coordinates_geojson(self):
        """Retourne les coordonnées au format GeoJSON"""
        if self.coordinates:
            from geoalchemy2.shape import to_shape
            geom = to_shape(self.coordinates)
            return {
                "type": "Polygon",
                "coordinates": [list(geom.exterior.coords)]
            }
        return None
    
    @property
    def value_cusd(self):
        """Convertit la valeur de wei vers cUSD"""
        if self.value:
            return float(self.value) / 10**18
        return 0.0
    
    def to_dict(self):
        """Convertit le modèle en dictionnaire pour l'API"""
        return {
            "id": self.id,
            "blockchain_id": self.blockchain_id,
            "owner_address": self.owner_address,
            "location": self.location,
            "coordinates": self.coordinates_geojson,
            "area": float(self.area) if self.area else 0,
            "value": self.value_cusd,
            "property_type": self.property_type,
            "status": self.status,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "last_transfer_date": self.last_transfer_date.isoformat() if self.last_transfer_date else None,
            "document_hash": self.document_hash,
            "ipfs_hash": self.ipfs_hash,
            "registrar_address": self.registrar_address,
            "is_verified": self.is_verified,
            "verified_by": self.verified_by,
            "verification_date": self.verification_date.isoformat() if self.verification_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class PropertySearch(Base):
    """
    Table d'indexation pour la recherche full-text des propriétés
    """
    __tablename__ = "property_search"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(BigInteger, ForeignKey("properties.id"), nullable=False, unique=True)
    search_vector = Column(Text, nullable=True)  # Utilise TSVECTOR en base
    keywords = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<PropertySearch(property_id={self.property_id})>"
