"""
Schémas Pydantic pour la recherche de propriétés
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date
from enum import Enum

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class SortField(str, Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    AREA = "area"
    PRICE = "price"
    TITLE = "title"
    CITY = "city"

class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")

class GeographicBounds(BaseModel):
    north_east: Coordinates = Field(..., description="Coin nord-est")
    south_west: Coordinates = Field(..., description="Coin sud-ouest")
    
    @validator("north_east")
    def validate_bounds(cls, v, values):
        if "south_west" in values:
            sw = values["south_west"]
            if v.latitude <= sw.latitude or v.longitude <= sw.longitude:
                raise ValueError("Les coordonnées nord-est doivent être supérieures au sud-ouest")
        return v

class SearchFilters(BaseModel):
    # Recherche textuelle
    text_query: Optional[str] = Field(None, max_length=200, description="Recherche textuelle")
    
    # Filtres de base
    property_type: Optional[str] = Field(None, description="Type de propriété")
    status: Optional[str] = Field(None, description="Statut de la propriété")
    verified_only: bool = Field(False, description="Propriétés vérifiées uniquement")
    
    # Filtres géographiques
    city: Optional[str] = Field(None, max_length=100, description="Ville")
    region: Optional[str] = Field(None, max_length=100, description="Région")
    country: str = Field("BF", description="Code pays")
    
    # Recherche par coordonnées
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    radius_km: float = Field(10.0, ge=0.1, le=100.0, description="Rayon de recherche en km")
    
    # Filtres par superficie
    min_area: Optional[float] = Field(None, ge=0, description="Superficie minimale (m²)")
    max_area: Optional[float] = Field(None, ge=0, description="Superficie maximale (m²)")
    
    # Filtres par prix
    min_price: Optional[float] = Field(None, ge=0, description="Prix minimum")
    max_price: Optional[float] = Field(None, ge=0, description="Prix maximum")
    
    # Filtres temporels
    registered_after: Optional[date] = Field(None, description="Enregistrées après cette date")
    registered_before: Optional[date] = Field(None, description="Enregistrées avant cette date")
    
    @validator("max_area")
    def validate_area_range(cls, v, values):
        if v is not None and "min_area" in values and values["min_area"] is not None:
            if v <= values["min_area"]:
                raise ValueError("La superficie maximale doit être supérieure à la minimale")
        return v
    
    @validator("max_price")
    def validate_price_range(cls, v, values):
        if v is not None and "min_price" in values and values["min_price"] is not None:
            if v <= values["min_price"]:
                raise ValueError("Le prix maximum doit être supérieur au minimum")
        return v

class SearchRequest(BaseModel):
    filters: SearchFilters = Field(..., description="Filtres de recherche")
    geographic_bounds: Optional[GeographicBounds] = Field(None, description="Limites géographiques")
    
    # Pagination et tri
    skip: int = Field(0, ge=0, description="Éléments à ignorer")
    limit: int = Field(20, ge=1, le=100, description="Nombre maximum d'éléments")
    sort_by: SortField = Field(SortField.CREATED_AT, description="Champ de tri")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Ordre de tri")
    
    # Options avancées
    include_suggestions: bool = Field(False, description="Inclure les suggestions")
    highlight_search_terms: bool = Field(False, description="Surligner les termes recherchés")

class PropertySearchResult(BaseModel):
    property_id: str = Field(..., description="ID de la propriété")
    title: str = Field(..., description="Titre de la propriété")
    description: Optional[str] = Field(None, description="Description")
    property_type: str = Field(..., description="Type de propriété")
    status: str = Field(..., description="Statut")
    verified: bool = Field(..., description="Propriété vérifiée")
    
    # Localisation
    city: Optional[str] = Field(None, description="Ville")
    region: Optional[str] = Field(None, description="Région")
    country: str = Field(..., description="Pays")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    address: Optional[str] = Field(None, description="Adresse complète")
    
    # Caractéristiques
    area: Optional[float] = Field(None, description="Superficie en m²")
    price: Optional[float] = Field(None, description="Prix en FCFA")
    
    # Métadonnées
    owner_name: Optional[str] = Field(None, description="Nom du propriétaire")
    registration_date: datetime = Field(..., description="Date d'enregistrement")
    last_updated: datetime = Field(..., description="Dernière mise à jour")
    
    # Données de recherche
    distance_km: Optional[float] = Field(None, description="Distance depuis le point de recherche")
    relevance_score: Optional[float] = Field(None, description="Score de pertinence")
    highlighted_fields: Optional[Dict[str, str]] = Field(None, description="Champs surlignés")

class SearchResponse(BaseModel):
    properties: List[PropertySearchResult] = Field(..., description="Résultats de recherche")
    total_count: int = Field(..., ge=0, description="Nombre total de résultats")
    skip: int = Field(..., ge=0, description="Éléments ignorés")
    limit: int = Field(..., ge=1, description="Limite appliquée")
    query_time_ms: int = Field(..., ge=0, description="Temps de requête en ms")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filtres appliqués")
    statistics: Optional[Dict[str, Any]] = Field(None, description="Statistiques de recherche")
    suggestions: Optional[List[str]] = Field(None, description="Suggestions de recherche")

class SearchSuggestion(BaseModel):
    text: str = Field(..., description="Texte de la suggestion")
    type: str = Field(..., description="Type de suggestion")
    count: int = Field(..., ge=0, description="Nombre de résultats")
    highlighted: Optional[str] = Field(None, description="Texte surligné")

class SearchStats(BaseModel):
    total_properties: int = Field(..., description="Total des propriétés")
    verified_properties: int = Field(..., description="Propriétés vérifiées")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Répartition par type")
    by_region: Dict[str, int] = Field(default_factory=dict, description="Répartition par région")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Répartition par statut")
    price_stats: Dict[str, float] = Field(default_factory=dict, description="Statistiques des prix")
    area_stats: Dict[str, float] = Field(default_factory=dict, description="Statistiques des superficies")

class FilterOption(BaseModel):
    value: str = Field(..., description="Valeur de l'option")
    label: str = Field(..., description="Libellé affiché")
    count: int = Field(..., ge=0, description="Nombre d'éléments")
    selected: bool = Field(False, description="Option sélectionnée")

class FilterOptions(BaseModel):
    property_types: List[FilterOption] = Field(default_factory=list)
    status_options: List[FilterOption] = Field(default_factory=list)
    cities: List[FilterOption] = Field(default_factory=list)
    regions: List[FilterOption] = Field(default_factory=list)
    price_ranges: List[FilterOption] = Field(default_factory=list)
    area_ranges: List[FilterOption] = Field(default_factory=list)

class GeocodingResult(BaseModel):
    address: str = Field(..., description="Adresse recherchée")
    formatted_address: str = Field(..., description="Adresse formatée")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    confidence: float = Field(..., ge=0, le=1, description="Niveau de confiance")
    components: Dict[str, str] = Field(default_factory=dict, description="Composants de l'adresse")
    
class ProximitySearch(BaseModel):
    center: Coordinates = Field(..., description="Point central")
    radius_km: float = Field(..., ge=0.1, le=50.0, description="Rayon de recherche")
    property_type: Optional[str] = Field(None, description="Type de propriété")
    verified_only: bool = Field(False, description="Propriétés vérifiées uniquement")

class ExportRequest(BaseModel):
    filters: SearchFilters = Field(..., description="Filtres pour l'export")
    format: str = Field("csv", regex="^(csv|xlsx|json)$", description="Format d'export")
    fields: Optional[List[str]] = Field(None, description="Champs à exporter")
    max_records: int = Field(10000, ge=1, le=50000, description="Nombre maximum d'enregistrements")

class SavedSearch(BaseModel):
    search_id: str = Field(..., description="ID de la recherche sauvegardée")
    name: str = Field(..., min_length=3, max_length=100, description="Nom de la recherche")
    filters: SearchFilters = Field(..., description="Filtres de recherche")
    user_id: str = Field(..., description="ID de l'utilisateur")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = Field(None, description="Dernière exécution")
    notification_enabled: bool = Field(False, description="Notifications activées")
