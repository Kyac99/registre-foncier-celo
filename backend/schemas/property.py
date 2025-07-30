"""
Schémas Pydantic pour la validation des données des propriétés
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class PropertyType(str, Enum):
    """Types de propriétés disponibles"""
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

class PropertyBase(BaseModel):
    """Schéma de base pour les propriétés"""
    location: str = Field(..., min_length=1, max_length=500, description="Localisation de la propriété")
    coordinates: Optional[str] = Field(None, description="Coordonnées GPS ou GeoJSON")
    area: float = Field(..., gt=0, description="Surface en m²")
    value: Optional[float] = Field(None, ge=0, description="Valeur estimée en cUSD")
    property_type: PropertyType = Field(..., description="Type de propriété")
    
    @validator('location')
    def validate_location(cls, v):
        if not v.strip():
            raise ValueError('La localisation ne peut pas être vide')
        return v.strip()

class PropertyCreate(PropertyBase):
    """Schéma pour la création d'une propriété"""
    owner_address: str = Field(..., min_length=42, max_length=42, description="Adresse Ethereum du propriétaire")
    
    @validator('owner_address')
    def validate_ethereum_address(cls, v):
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError('Adresse Ethereum invalide')
        return v.lower()

class PropertyUpdate(BaseModel):
    """Schéma pour la mise à jour d'une propriété"""
    value: Optional[float] = Field(None, ge=0)
    status: Optional[PropertyStatus] = None
    is_verified: Optional[bool] = None

class PropertyResponse(PropertyBase):
    """Schéma de réponse pour une propriété"""
    id: int
    blockchain_id: int
    owner_address: str
    status: PropertyStatus
    registration_date: Optional[datetime]
    last_transfer_date: Optional[datetime]
    document_hash: Optional[str]
    ipfs_hash: Optional[str]
    registrar_address: Optional[str]
    is_verified: bool = False
    verified_by: Optional[str]
    verification_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class PropertyListResponse(BaseModel):
    """Schéma de réponse pour la liste paginée des propriétés"""
    properties: List[PropertyResponse]
    total: int
    skip: int
    limit: int
    
    @property
    def has_next(self) -> bool:
        return (self.skip + self.limit) < self.total
    
    @property
    def has_prev(self) -> bool:
        return self.skip > 0

class PropertySearchParams(BaseModel):
    """Paramètres de recherche pour les propriétés"""
    q: Optional[str] = Field(None, min_length=1, description="Terme de recherche")
    property_type: Optional[PropertyType] = None
    status: Optional[PropertyStatus] = None
    owner_address: Optional[str] = None
    verified_only: bool = False
    min_area: Optional[float] = Field(None, ge=0)
    max_area: Optional[float] = Field(None, ge=0)
    min_value: Optional[float] = Field(None, ge=0)
    max_value: Optional[float] = Field(None, ge=0)
    
    @validator('max_area')
    def validate_area_range(cls, v, values):
        if v is not None and 'min_area' in values and values['min_area'] is not None:
            if v < values['min_area']:
                raise ValueError('max_area doit être supérieur à min_area')
        return v
    
    @validator('max_value')
    def validate_value_range(cls, v, values):
        if v is not None and 'min_value' in values and values['min_value'] is not None:
            if v < values['min_value']:
                raise ValueError('max_value doit être supérieur à min_value')
        return v

class GeospatialSearchParams(BaseModel):
    """Paramètres pour la recherche géospatiale"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude du point central")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude du point central")
    radius_km: float = Field(1.0, gt=0, le=50, description="Rayon de recherche en kilomètres")

class PropertyStatsResponse(BaseModel):
    """Statistiques sur les propriétés"""
    total_properties: int
    verified_properties: int
    unique_owners: int
    total_area: float
    average_area: float
    by_type: Dict[str, int]
    by_status: Dict[str, int]

class PropertyTransferRequest(BaseModel):
    """Demande de transfert de propriété"""
    new_owner_address: str = Field(..., min_length=42, max_length=42)
    transfer_value: Optional[float] = Field(None, ge=0)
    
    @validator('new_owner_address')
    def validate_ethereum_address(cls, v):
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError('Adresse Ethereum invalide')
        return v.lower()

class PropertyDocumentResponse(BaseModel):
    """Réponse pour les documents de propriété"""
    filename: str
    size: int
    mime_type: str
    ipfs_hash: str
    upload_date: datetime
    encrypted: bool
    
class PropertyHistoryEntry(BaseModel):
    """Entrée dans l'historique d'une propriété"""
    timestamp: datetime
    event_type: str  # 'created', 'transferred', 'verified', 'disputed'
    from_address: Optional[str]
    to_address: Optional[str]
    transaction_hash: Optional[str]
    block_number: Optional[int]
    value: Optional[float]
    details: Optional[Dict[str, Any]]

class PropertyHistoryResponse(BaseModel):
    """Historique complet d'une propriété"""
    property_id: int
    blockchain_id: int
    history: List[PropertyHistoryEntry]
    
class PropertyVerificationRequest(BaseModel):
    """Demande de vérification de propriété"""
    verified: bool = True
    verification_notes: Optional[str] = Field(None, max_length=1000)

class PropertyMapData(BaseModel):
    """Données de propriété pour affichage sur carte"""
    id: int
    blockchain_id: int
    location: str
    coordinates: Optional[Dict[str, Any]]
    owner_address: str
    property_type: PropertyType
    status: PropertyStatus
    is_verified: bool
    area: float
    value: Optional[float]
    
class BulkPropertyResponse(BaseModel):
    """Réponse pour les opérations en lot sur les propriétés"""
    successful: List[int]
    failed: List[Dict[str, Any]]
    total_processed: int
    
class PropertyValidationError(BaseModel):
    """Erreur de validation pour une propriété"""
    field: str
    message: str
    value: Any

class PropertyAnalytics(BaseModel):
    """Données analytiques pour les propriétés"""
    period: str  # 'day', 'week', 'month', 'year'
    registrations_count: int
    transfers_count: int
    verifications_count: int
    total_value: float
    average_area: float
    top_locations: List[Dict[str, Any]]
    
class PropertyExportRequest(BaseModel):
    """Demande d'export de données"""
    format: str = Field(..., regex="^(csv|xlsx|json)$")
    filters: Optional[PropertySearchParams] = None
    include_documents: bool = False
    
class PropertyImportRequest(BaseModel):
    """Demande d'import de données"""
    source_type: str = Field(..., regex="^(csv|xlsx|json)$")
    validate_only: bool = False
    auto_verify: bool = False
