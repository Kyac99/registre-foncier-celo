"""
Routeur API pour la gestion des propriétés foncières
Endpoints CRUD avec intégration blockchain et IPFS
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional, Dict, Any
import json
from io import BytesIO
import logging

from config.database import get_database, cache_manager
from models.property import Property, PropertyType, PropertyStatus, PropertySearch
from models.user import User, UserRole
from services.blockchain_service import blockchain_service
from services.ipfs_service import ipfs_service
from middleware.auth import get_current_user, require_role
from schemas.property import (
    PropertyCreate, PropertyUpdate, PropertyResponse, 
    PropertyListResponse, PropertySearchParams
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    location: str = Form(...),
    coordinates: str = Form(...),
    area: float = Form(...),
    value: float = Form(...),
    property_type: str = Form(...),
    owner_address: str = Form(...),
    document: UploadFile = File(...),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_role([UserRole.NOTARY, UserRole.ADMIN]))
):
    """
    Enregistre une nouvelle propriété sur la blockchain et en base de données
    Nécessite le rôle NOTARY ou ADMIN
    """
    try:
        logger.info(f"🏠 Création propriété par {current_user.wallet_address}")
        
        # Validation des données
        if not PropertyType.__members__.get(property_type.upper()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type de propriété invalide: {property_type}"
            )
        
        # Vérification que la propriété n'existe pas déjà
        existing = await db.execute(
            select(Property).where(Property.location == location)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Une propriété existe déjà à cette localisation"
            )
        
        # Upload du document sur IPFS
        document_content = await document.read()
        ipfs_result = await ipfs_service.upload_file(
            file_content=document_content,
            filename=document.filename,
            metadata={
                "property_location": location,
                "uploaded_by": current_user.wallet_address,
                "document_type": "property_deed"
            },
            encrypt=True  # Chiffrement pour les documents sensibles
        )
        
        if not ipfs_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur upload document: {ipfs_result.get('error')}"
            )
        
        # Conversion de la valeur en Wei (cUSD)
        value_wei = int(value * 10**18)
        
        # Enregistrement sur la blockchain
        blockchain_result = await blockchain_service.register_property(
            owner_address=owner_address,
            location=location,
            coordinates=coordinates,
            area=int(area),
            value=value_wei,
            property_type=PropertyType[property_type.upper()].value,
            document_hash=ipfs_result["ipfs_hash"],
            token_uri=f"{ipfs_result['gateway_url']}/metadata.json"
        )
        
        if not blockchain_result["success"]:
            # Nettoyer IPFS en cas d'échec blockchain
            await ipfs_service.unpin_file(ipfs_result["ipfs_hash"])
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur blockchain: {blockchain_result.get('error')}"
            )
        
        # Sauvegarde en base de données
        new_property = Property(
            blockchain_id=blockchain_result["property_id"],
            owner_address=owner_address,
            location=location,
            coordinates=f"POLYGON(({coordinates}))",  # Conversion en PostGIS
            area=area,
            value=value_wei,
            property_type=property_type.upper(),
            status=PropertyStatus.ACTIVE,
            document_hash=ipfs_result["ipfs_hash"],
            ipfs_hash=ipfs_result["ipfs_hash"],
            registrar_address=current_user.wallet_address
        )
        
        db.add(new_property)
        await db.commit()
        await db.refresh(new_property)
        
        # Invalidation du cache
        await cache_manager.clear_pattern("properties:*")
        
        logger.info(f"✅ Propriété créée - ID: {new_property.id}, Blockchain ID: {blockchain_result['property_id']}")
        
        return PropertyResponse(**new_property.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur création propriété: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la création de la propriété"
        )

@router.get("/", response_model=PropertyListResponse)
async def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    property_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    owner_address: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    db: AsyncSession = Depends(get_database)
):
    """
    Liste les propriétés avec filtres et pagination
    """
    try:
        # Construction de la requête avec filtres
        query = select(Property)
        conditions = []
        
        if property_type:
            conditions.append(Property.property_type == property_type.upper())
        
        if status:
            conditions.append(Property.status == status.upper())
        
        if owner_address:
            conditions.append(Property.owner_address == owner_address.lower())
        
        if verified_only:
            conditions.append(Property.is_verified == True)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Ajout pagination
        query = query.offset(skip).limit(limit).order_by(Property.created_at.desc())
        
        # Exécution
        result = await db.execute(query)
        properties = result.scalars().all()
        
        # Comptage total
        count_query = select(func.count(Property.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return PropertyListResponse(
            properties=[PropertyResponse(**prop.to_dict()) for prop in properties],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur liste propriétés: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des propriétés"
        )

@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère une propriété par son ID
    """
    try:
        # Vérification cache
        cache_key = f"property:{property_id}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return PropertyResponse(**cached)
        
        # Requête base de données
        result = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        property_obj = result.scalar_one_or_none()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Propriété non trouvée"
            )
        
        # Mise en cache
        property_data = property_obj.to_dict()
        await cache_manager.set(cache_key, property_data, ttl=300)  # 5 minutes
        
        return PropertyResponse(**property_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur récupération propriété {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de la propriété"
        )

@router.put("/{property_id}/verify", response_model=PropertyResponse)
async def verify_property(
    property_id: int,
    verified: bool = Form(True),
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_role([UserRole.SURVEYOR, UserRole.ADMIN]))
):
    """
    Vérifie ou annule la vérification d'une propriété
    Nécessite le rôle SURVEYOR ou ADMIN
    """
    try:
        # Récupération de la propriété
        result = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        property_obj = result.scalar_one_or_none()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Propriété non trouvée"
            )
        
        # Mise à jour de la vérification
        property_obj.is_verified = verified
        property_obj.verified_by = current_user.wallet_address if verified else None
        property_obj.verification_date = func.now() if verified else None
        
        # Interaction blockchain si nécessaire
        if hasattr(blockchain_service.contract, 'functions') and blockchain_service.contract:
            try:
                await blockchain_service.verify_property(
                    property_obj.blockchain_id,
                    verified
                )
            except Exception as e:
                logger.warning(f"Erreur vérification blockchain: {e}")
        
        await db.commit()
        await db.refresh(property_obj)
        
        # Invalidation cache
        await cache_manager.delete(f"property:{property_id}")
        await cache_manager.clear_pattern("properties:*")
        
        action = "vérifiée" if verified else "non-vérifiée"
        logger.info(f"✅ Propriété {property_id} {action} par {current_user.wallet_address}")
        
        return PropertyResponse(**property_obj.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur vérification propriété {property_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la vérification"
        )

@router.get("/{property_id}/document")
async def download_property_document(
    property_id: int,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Télécharge le document associé à une propriété
    """
    try:
        # Récupération de la propriété
        result = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        property_obj = result.scalar_one_or_none()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Propriété non trouvée"
            )
        
        if not property_obj.ipfs_hash:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun document associé à cette propriété"
            )
        
        # Vérification des droits d'accès
        if (current_user.wallet_address != property_obj.owner_address and 
            current_user.role not in [UserRole.NOTARY, UserRole.ADMIN, UserRole.SURVEYOR]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce document"
            )
        
        # Téléchargement depuis IPFS
        download_result = await ipfs_service.download_file(
            property_obj.ipfs_hash,
            decrypt=True  # Les documents sont chiffrés
        )
        
        if not download_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors du téléchargement du document"
            )
        
        # Préparation de la réponse streaming
        file_content = download_result["content"]
        file_stream = BytesIO(file_content)
        
        # Détermination du type de contenu
        metadata = download_result.get("metadata", {})
        filename = metadata.get("keyvalues", {}).get("filename", f"document_{property_id}")
        mime_type = metadata.get("keyvalues", {}).get("mimetype", "application/octet-stream")
        
        return StreamingResponse(
            BytesIO(file_content),
            media_type=mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement document {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du téléchargement"
        )

@router.get("/search/geospatial")
async def search_properties_by_location(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = Query(1.0, ge=0.1, le=50),
    db: AsyncSession = Depends(get_database)
):
    """
    Recherche géospatiale de propriétés dans un rayon donné
    """
    try:
        # Conversion du rayon en mètres
        radius_meters = radius_km * 1000
        
        # Requête PostGIS pour recherche géospatiale
        query = f"""
            SELECT p.*, 
                   ST_Distance(
                       ST_GeomFromText('POINT({longitude} {latitude})', 4326)::geography,
                       p.coordinates::geography
                   ) as distance
            FROM properties p
            WHERE ST_DWithin(
                p.coordinates::geography,
                ST_GeomFromText('POINT({longitude} {latitude})', 4326)::geography,
                {radius_meters}
            )
            ORDER BY distance
            LIMIT 50
        """
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Formatage des résultats
        properties = []
        for row in rows:
            prop_data = {
                "id": row.id,
                "blockchain_id": row.blockchain_id,
                "owner_address": row.owner_address,
                "location": row.location,
                "area": float(row.area),
                "value": float(row.value) / 10**18 if row.value else 0,
                "property_type": row.property_type,
                "status": row.status,
                "is_verified": row.is_verified,
                "distance_km": round(row.distance / 1000, 2)
            }
            properties.append(prop_data)
        
        return {
            "properties": properties,
            "search_center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "total_found": len(properties)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur recherche géospatiale: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la recherche géospatiale"
        )

@router.get("/owner/{owner_address}", response_model=PropertyListResponse)
async def get_properties_by_owner(
    owner_address: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère toutes les propriétés d'un propriétaire
    """
    try:
        # Requête avec pagination
        query = select(Property).where(
            Property.owner_address == owner_address.lower()
        ).offset(skip).limit(limit).order_by(Property.created_at.desc())
        
        result = await db.execute(query)
        properties = result.scalars().all()
        
        # Comptage total
        count_result = await db.execute(
            select(func.count(Property.id)).where(
                Property.owner_address == owner_address.lower()
            )
        )
        total = count_result.scalar()
        
        return PropertyListResponse(
            properties=[PropertyResponse(**prop.to_dict()) for prop in properties],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur propriétés owner {owner_address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des propriétés"
        )

@router.get("/stats/summary")
async def get_property_stats(
    db: AsyncSession = Depends(get_database)
):
    """
    Statistiques générales sur les propriétés
    """
    try:
        # Requêtes statistiques
        stats_query = """
            SELECT 
                COUNT(*) as total_properties,
                COUNT(CASE WHEN is_verified = true THEN 1 END) as verified_properties,
                COUNT(DISTINCT owner_address) as unique_owners,
                SUM(area) as total_area,
                AVG(area) as average_area,
                COUNT(CASE WHEN property_type = 'RESIDENTIAL' THEN 1 END) as residential,
                COUNT(CASE WHEN property_type = 'COMMERCIAL' THEN 1 END) as commercial,
                COUNT(CASE WHEN property_type = 'AGRICULTURAL' THEN 1 END) as agricultural,
                COUNT(CASE WHEN property_type = 'INDUSTRIAL' THEN 1 END) as industrial
            FROM properties
        """
        
        result = await db.execute(stats_query)
        stats = result.fetchone()
        
        return {
            "total_properties": stats.total_properties,
            "verified_properties": stats.verified_properties,
            "unique_owners": stats.unique_owners,
            "total_area": float(stats.total_area) if stats.total_area else 0,
            "average_area": float(stats.average_area) if stats.average_area else 0,
            "by_type": {
                "residential": stats.residential,
                "commercial": stats.commercial,
                "agricultural": stats.agricultural,
                "industrial": stats.industrial
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur stats propriétés: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du calcul des statistiques"
        )
