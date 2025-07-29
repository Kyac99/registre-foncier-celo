"""
Routeur API pour la gestion des propriétés foncières
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json

from config.database import get_database, cache_manager
from models import Property, PropertyType, PropertyStatus, User, PropertySearch
from middleware.auth import verify_token, get_current_user
from services.blockchain import CeloBlockchainService
from services.ipfs import IPFSService

router = APIRouter()

# Schémas Pydantic pour la validation
class PropertyCreate(BaseModel):
    """Schéma pour créer une propriété"""
    location: str = Field(..., min_length=5, max_length=500)
    coordinates: Optional[Dict[str, Any]] = None  # GeoJSON
    area: float = Field(..., gt=0)
    value: Optional[float] = Field(None, ge=0)
    property_type: PropertyType = PropertyType.RESIDENTIAL
    document_file: Optional[str] = None  # Base64 ou référence fichier
    
    @validator('coordinates')
    def validate_coordinates(cls, v):
        if v is not None:
            # Validation basique du GeoJSON
            if not isinstance(v, dict) or 'type' not in v or 'coordinates' not in v:
                raise ValueError("Format GeoJSON invalide")
            if v['type'] not in ['Polygon', 'Point']:
                raise ValueError("Type de géométrie non supporté")
        return v

class PropertyUpdate(BaseModel):
    """Schéma pour mettre à jour une propriété"""
    location: Optional[str] = Field(None, min_length=5, max_length=500)
    coordinates: Optional[Dict[str, Any]] = None
    area: Optional[float] = Field(None, gt=0)
    value: Optional[float] = Field(None, ge=0)
    property_type: Optional[PropertyType] = None
    status: Optional[PropertyStatus] = None

class PropertyFilter(BaseModel):
    """Schéma pour filtrer les propriétés"""
    property_type: Optional[PropertyType] = None
    status: Optional[PropertyStatus] = None
    min_area: Optional[float] = Field(None, ge=0)
    max_area: Optional[float] = Field(None, ge=0)
    min_value: Optional[float] = Field(None, ge=0)
    max_value: Optional[float] = Field(None, ge=0)
    owner_address: Optional[str] = None
    verified_only: Optional[bool] = False
    location_search: Optional[str] = None

class PropertyResponse(BaseModel):
    """Schéma de réponse pour une propriété"""
    id: int
    blockchain_id: int
    owner_address: str
    location: str
    area: float
    area_formatted: str
    value: Optional[float]
    value_formatted: str
    property_type: str
    type_display: str
    status: str
    status_display: str
    is_verified: bool
    registration_date: Optional[datetime]
    last_transfer_date: Optional[datetime]
    created_at: datetime
    coordinates: Optional[Dict[str, Any]] = None

# Services injectés
async def get_blockchain_service() -> CeloBlockchainService:
    return CeloBlockchainService()

async def get_ipfs_service() -> IPFSService:
    return IPFSService()

# Endpoints

@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
    blockchain_service: CeloBlockchainService = Depends(get_blockchain_service),
    ipfs_service: IPFSService = Depends(get_ipfs_service)
):
    """
    Enregistre une nouvelle propriété sur la blockchain et en base de données
    Nécessite le rôle notaire
    """
    # Vérification des permissions
    if not current_user.is_notary and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les notaires peuvent enregistrer des propriétés"
        )
    
    try:
        # Vérification si la localisation existe déjà
        existing_query = select(Property).where(Property.location == property_data.location)
        existing = await db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Une propriété existe déjà à cette localisation"
            )
        
        # Upload du document principal sur IPFS si fourni
        document_hash = None
        ipfs_hash = None
        if property_data.document_file:
            ipfs_result = await ipfs_service.upload_document(
                property_data.document_file,
                f"property_{property_data.location.replace(' ', '_')}.pdf"
            )
            document_hash = ipfs_result["hash"]
            ipfs_hash = ipfs_result["hash"]
        
        # Conversion des coordonnées GeoJSON vers PostGIS
        coordinates_wkt = None
        if property_data.coordinates:
            from services.geospatial import GeospatialService
            geo_service = GeospatialService()
            coordinates_wkt = geo_service.geojson_to_wkt(property_data.coordinates)
        
        # Enregistrement sur la blockchain CELO
        tx_result = await blockchain_service.register_property(
            owner_address=current_user.wallet_address,
            location=property_data.location,
            coordinates=json.dumps(property_data.coordinates) if property_data.coordinates else "",
            area=int(property_data.area),
            value=int(property_data.value * 10**18) if property_data.value else 0,  # Conversion en wei
            property_type=property_data.property_type.value,
            document_hash=document_hash or "",
            registrar_address=current_user.wallet_address
        )
        
        # Création de l'enregistrement en base de données
        new_property = Property(
            blockchain_id=tx_result["property_id"],
            owner_address=current_user.wallet_address,
            location=property_data.location,
            coordinates=coordinates_wkt,
            area=property_data.area,
            value=property_data.value,
            property_type=property_data.property_type,
            status=PropertyStatus.ACTIVE,
            registration_date=datetime.utcnow(),
            last_transfer_date=datetime.utcnow(),
            document_hash=document_hash,
            ipfs_hash=ipfs_hash,
            registrar_address=current_user.wallet_address,
            is_verified=False
        )
        
        db.add(new_property)
        await db.commit()
        await db.refresh(new_property)
        
        # Invalidation du cache
        await cache_manager.clear_pattern("properties:*")
        
        return PropertyResponse(**new_property.to_dict(include_geom=True))
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'enregistrement: {str(e)}"
        )

@router.get("/", response_model=List[PropertyResponse])
async def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    property_filter: PropertyFilter = Depends(),
    db: AsyncSession = Depends(get_database)
):
    """
    Liste les propriétés avec filtres et pagination
    """
    cache_key = f"properties:list:{skip}:{limit}:{hash(str(property_filter.dict()))}"
    
    # Vérification du cache
    cached_result = await cache_manager.get(cache_key)
    if cached_result:
        return cached_result
    
    # Construction de la requête
    query = select(Property).options(selectinload(Property.owner))
    
    # Application des filtres
    if property_filter.property_type:
        query = query.where(Property.property_type == property_filter.property_type)
    
    if property_filter.status:
        query = query.where(Property.status == property_filter.status)
    
    if property_filter.min_area is not None:
        query = query.where(Property.area >= property_filter.min_area)
    
    if property_filter.max_area is not None:
        query = query.where(Property.area <= property_filter.max_area)
    
    if property_filter.min_value is not None:
        query = query.where(Property.value >= property_filter.min_value)
    
    if property_filter.max_value is not None:
        query = query.where(Property.value <= property_filter.max_value)
    
    if property_filter.owner_address:
        query = query.where(Property.owner_address == property_filter.owner_address)
    
    if property_filter.verified_only:
        query = query.where(Property.is_verified == True)
    
    if property_filter.location_search:
        # Recherche full-text sur la localisation
        search_term = f"%{property_filter.location_search}%"
        query = query.where(Property.location.ilike(search_term))
    
    # Pagination et tri
    query = query.order_by(Property.created_at.desc()).offset(skip).limit(limit)
    
    # Exécution de la requête
    result = await db.execute(query)
    properties = result.scalars().all()
    
    # Conversion en réponse
    response_data = [PropertyResponse(**prop.to_dict(include_geom=True)) for prop in properties]
    
    # Mise en cache
    await cache_manager.set(cache_key, response_data, ttl=300)  # 5 minutes
    
    return response_data

@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère une propriété par son ID
    """
    cache_key = f"property:{property_id}"
    
    # Vérification du cache
    cached_result = await cache_manager.get(cache_key)
    if cached_result:
        return cached_result
    
    # Requête en base
    query = select(Property).options(
        selectinload(Property.owner),
        selectinload(Property.documents),
        selectinload(Property.transactions)
    ).where(Property.id == property_id)
    
    result = await db.execute(query)
    property_obj = result.scalar_one_or_none()
    
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriété non trouvée"
        )
    
    response_data = PropertyResponse(**property_obj.to_dict(include_geom=True))
    
    # Mise en cache
    await cache_manager.set(cache_key, response_data, ttl=600)  # 10 minutes
    
    return response_data

@router.get("/{property_id}/geojson")
async def get_property_geojson(
    property_id: int,
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère une propriété au format GeoJSON
    """
    query = select(Property).where(Property.id == property_id)
    result = await db.execute(query)
    property_obj = result.scalar_one_or_none()
    
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriété non trouvée"
        )
    
    return property_obj.to_geojson_feature()

@router.get("/map/bounds")
async def get_properties_in_bounds(
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère les propriétés dans une zone géographique donnée
    Format: GeoJSON FeatureCollection
    """
    # Construction de la requête géospatiale avec PostGIS
    bbox_query = f"ST_MakeEnvelope({west}, {south}, {east}, {north}, 4326)"
    
    query = select(Property).where(
        func.ST_Intersects(
            Property.coordinates,
            func.ST_GeomFromText(bbox_query)
        )
    ).limit(1000)  # Limite pour les performances
    
    result = await db.execute(query)
    properties = result.scalars().all()
    
    # Construction de la FeatureCollection GeoJSON
    features = [prop.to_geojson_feature() for prop in properties if prop.coordinates]
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "count": len(features),
            "bounds": {
                "north": north,
                "south": south,
                "east": east,
                "west": west
            }
        }
    }

@router.patch("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: int,
    property_update: PropertyUpdate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
    blockchain_service: CeloBlockchainService = Depends(get_blockchain_service)
):
    """
    Met à jour une propriété
    Nécessite d'être propriétaire ou notaire
    """
    # Récupération de la propriété
    query = select(Property).where(Property.id == property_id)
    result = await db.execute(query)
    property_obj = result.scalar_one_or_none()
    
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriété non trouvée"
        )
    
    # Vérification des permissions
    if not (current_user.wallet_address == property_obj.owner_address or 
            current_user.is_notary or current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à modifier cette propriété"
        )
    
    try:
        # Mise à jour des champs
        update_data = property_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "coordinates" and value:
                # Conversion GeoJSON vers PostGIS
                from services.geospatial import GeospatialService
                geo_service = GeospatialService()
                coordinates_wkt = geo_service.geojson_to_wkt(value)
                setattr(property_obj, field, coordinates_wkt)
            else:
                setattr(property_obj, field, value)
        
        # Mise à jour sur la blockchain si nécessaire
        if "value" in update_data and current_user.is_admin:
            await blockchain_service.update_property_value(
                property_obj.blockchain_id,
                int(update_data["value"] * 10**18)  # Conversion en wei
            )
        
        await db.commit()
        await db.refresh(property_obj)
        
        # Invalidation du cache
        await cache_manager.delete(f"property:{property_id}")
        await cache_manager.clear_pattern("properties:*")
        
        return PropertyResponse(**property_obj.to_dict(include_geom=True))
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )

@router.post("/{property_id}/verify")
async def verify_property(
    property_id: int,
    verification_note: Optional[str] = None,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user),
    blockchain_service: CeloBlockchainService = Depends(get_blockchain_service)
):
    """
    Vérifie une propriété (géomètre uniquement)
    """
    if not current_user.is_surveyor and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les géomètres peuvent vérifier les propriétés"
        )
    
    # Récupération de la propriété
    query = select(Property).where(Property.id == property_id)
    result = await db.execute(query)
    property_obj = result.scalar_one_or_none()
    
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriété non trouvée"
        )
    
    try:
        # Vérification sur la blockchain
        await blockchain_service.verify_property(
            property_obj.blockchain_id,
            True
        )
        
        # Mise à jour en base
        property_obj.is_verified = True
        await db.commit()
        
        # Invalidation du cache
        await cache_manager.delete(f"property:{property_id}")
        
        return {"message": "Propriété vérifiée avec succès"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )

@router.get("/stats/overview")
async def get_properties_stats(
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère les statistiques générales des propriétés
    """
    cache_key = "properties:stats:overview"
    
    # Vérification du cache
    cached_result = await cache_manager.get(cache_key)
    if cached_result:
        return cached_result
    
    # Requêtes de statistiques
    total_query = select(func.count(Property.id))
    verified_query = select(func.count(Property.id)).where(Property.is_verified == True)
    total_area_query = select(func.sum(Property.area))
    total_value_query = select(func.sum(Property.value))
    
    # Types de propriétés
    types_query = select(
        Property.property_type,
        func.count(Property.id).label('count')
    ).group_by(Property.property_type)
    
    # Exécution des requêtes
    total_result = await db.execute(total_query)
    verified_result = await db.execute(verified_query)
    area_result = await db.execute(total_area_query)
    value_result = await db.execute(total_value_query)
    types_result = await db.execute(types_query)
    
    total_properties = total_result.scalar() or 0
    verified_properties = verified_result.scalar() or 0
    total_area = area_result.scalar() or 0
    total_value = value_result.scalar() or 0
    types_data = {row.property_type: row.count for row in types_result}
    
    stats = {
        "total_properties": total_properties,
        "verified_properties": verified_properties,
        "verification_rate": (verified_properties / total_properties * 100) if total_properties > 0 else 0,
        "total_area": float(total_area),
        "total_area_formatted": f"{float(total_area):,.2f} m²",
        "total_value": float(total_value) if total_value else 0,
        "total_value_formatted": f"{float(total_value):,.2f} cUSD" if total_value else "0 cUSD",
        "average_property_size": float(total_area / total_properties) if total_properties > 0 else 0,
        "types_distribution": types_data
    }
    
    # Mise en cache
    await cache_manager.set(cache_key, stats, ttl=1800)  # 30 minutes
    
    return stats
