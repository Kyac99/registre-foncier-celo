"""
Modèle SQLAlchemy pour les propriétés foncières
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from config.database import Base
import uuid as uuid_pkg
from enum import Enum

class PropertyType(str, Enum):
    """Types de propriétés"""
    RESIDENTIAL = "RESIDENTIAL"
    COMMERCIAL = "COMMERCIAL"
    INDUSTRIAL = "INDUSTRIAL"
    AGRICULTURAL = "AGRICULTURAL"
    FOREST = "FOREST"
    OTHER = "OTHER"

class PropertyStatus(str, Enum):
    """Statuts de propriétés"""
    ACTIVE = "ACTIVE"
    DISPUTED = "DISPUTED"
    FROZEN = "FROZEN"
    TRANSFERRED = "TRANSFERRED"

class Property(Base):
    """Modèle pour les propriétés foncières"""
    
    __tablename__ = "properties"
    
    # Clé primaire
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # ID sur la blockchain (référence au smart contract)
    blockchain_id = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Propriétaire actuel
    owner_address = Column(String(42), ForeignKey("users.wallet_address"), nullable=False, index=True)
    
    # Informations géographiques
    location = Column(Text, nullable=False)
    coordinates = Column(Geometry('POLYGON', srid=4326), nullable=True)
    area = Column(Numeric(15, 2), nullable=False)  # Surface en m²
    
    # Informations économiques
    value = Column(Numeric(20, 2), nullable=True)  # Valeur en cUSD
    
    # Classification
    property_type = Column(String(50), nullable=False, default=PropertyType.RESIDENTIAL)
    status = Column(String(50), nullable=False, default=PropertyStatus.ACTIVE)
    
    # Dates importantes
    registration_date = Column(DateTime(timezone=True), nullable=True)
    last_transfer_date = Column(DateTime(timezone=True), nullable=True)
    
    # Documents et vérification
    document_hash = Column(String(100), nullable=True)  # Hash du document principal
    ipfs_hash = Column(String(100), nullable=True)      # Hash IPFS
    registrar_address = Column(String(42), nullable=True)  # Notaire qui a enregistré
    is_verified = Column(Boolean, default=False, nullable=False)  # Vérifié par géomètre
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    owner = relationship("User", back_populates="properties")
    transactions = relationship("PropertyTransaction", back_populates="property", lazy="dynamic")
    documents = relationship("Document", back_populates="property", lazy="dynamic")
    search_data = relationship("PropertySearch", back_populates="property", uselist=False)
    
    def __repr__(self):
        return f"<Property {self.blockchain_id} - {self.location[:50]}>"
    
    @property
    def area_formatted(self):
        """Surface formatée avec unité"""
        if self.area:
            if self.area >= 10000:  # 1 hectare = 10000 m²
                return f"{float(self.area) / 10000:.2f} ha"
            else:
                return f"{float(self.area)} m²"
        return "Non défini"
    
    @property
    def value_formatted(self):
        """Valeur formatée en cUSD"""
        if self.value:
            return f"{float(self.value):,.2f} cUSD"
        return "Non évaluée"
    
    @property
    def coordinates_geojson(self):
        """Retourne les coordonnées au format GeoJSON"""
        if self.coordinates:
            # Conversion WKT vers GeoJSON
            from geoalchemy2.shape import to_shape
            geom = to_shape(self.coordinates)
            return {
                "type": "Polygon",
                "coordinates": [list(geom.exterior.coords)]
            }
        return None
    
    @property
    def status_display(self):
        """Statut affiché en français"""
        status_map = {
            PropertyStatus.ACTIVE: "Active",
            PropertyStatus.DISPUTED: "En litige",
            PropertyStatus.FROZEN: "Gelée",
            PropertyStatus.TRANSFERRED: "Transférée"
        }
        return status_map.get(self.status, self.status)
    
    @property
    def type_display(self):
        """Type affiché en français"""
        type_map = {
            PropertyType.RESIDENTIAL: "Résidentiel",
            PropertyType.COMMERCIAL: "Commercial",
            PropertyType.INDUSTRIAL: "Industriel",
            PropertyType.AGRICULTURAL: "Agricole",
            PropertyType.FOREST: "Forestier",
            PropertyType.OTHER: "Autre"
        }
        return type_map.get(self.property_type, self.property_type)
    
    def calculate_distance_to(self, other_property):
        """Calcule la distance vers une autre propriété"""
        if self.coordinates and other_property.coordinates:
            from geoalchemy2 import func as geo_func
            from sqlalchemy import select
            # Cette méthode nécessiterait une session DB pour l'exécution
            # Retourne la distance en mètres
            pass
    
    def is_within_radius(self, point_lat: float, point_lon: float, radius_meters: int):
        """Vérifie si la propriété est dans un rayon donné"""
        # Logique à implémenter avec PostGIS
        pass
    
    def to_dict(self, include_sensitive=False, include_geom=True):
        """Convertit le modèle en dictionnaire"""
        data = {
            "id": self.id,
            "blockchain_id": self.blockchain_id,
            "owner_address": self.owner_address,
            "location": self.location,
            "area": float(self.area) if self.area else None,
            "area_formatted": self.area_formatted,
            "value": float(self.value) if self.value else None,
            "value_formatted": self.value_formatted,
            "property_type": self.property_type,
            "type_display": self.type_display,
            "status": self.status,
            "status_display": self.status_display,
            "is_verified": self.is_verified,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "last_transfer_date": self.last_transfer_date.isoformat() if self.last_transfer_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_geom and self.coordinates_geojson:
            data["coordinates"] = self.coordinates_geojson
        
        if include_sensitive:
            data.update({
                "document_hash": self.document_hash,
                "ipfs_hash": self.ipfs_hash,
                "registrar_address": self.registrar_address,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            })
        
        return data
    
    def to_geojson_feature(self):
        """Convertit la propriété en Feature GeoJSON"""
        return {
            "type": "Feature",
            "id": self.id,
            "properties": {
                "blockchain_id": self.blockchain_id,
                "location": self.location,
                "area": float(self.area) if self.area else None,
                "value": float(self.value) if self.value else None,
                "property_type": self.property_type,
                "status": self.status,
                "is_verified": self.is_verified,
                "owner_address": self.owner_address
            },
            "geometry": self.coordinates_geojson
        }

# Table d'association pour les recherches full-text
class PropertySearch(Base):
    """Table pour l'indexation et la recherche des propriétés"""
    
    __tablename__ = "property_search"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    property_id = Column(BigInteger, ForeignKey("properties.id"), unique=True, nullable=False)
    
    # Données de recherche
    search_vector = Column(Text)  # Vector de recherche PostgreSQL
    keywords = Column(Text)       # Mots-clés séparés par des espaces
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    property = relationship("Property", back_populates="search_data")
