"""
Router pour la recherche de propriétés
Recherche avancée, filtres géographiques et textuels
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime, date
from geopy.distance import geodesic

from config.database import get_database
from config.settings import settings
from services.search_service import SearchService
from services.geocoding_service import GeocodingService
from schemas.search import (
    SearchRequest,
    SearchResponse, 
    PropertySearchResult,
    SearchFilters,
    GeographicBounds,
    SearchStats
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Services
search_service = SearchService()
geocoding_service = GeocodingService()

@router.get("/properties", response_model=SearchResponse)
async def search_properties(
    # Recherche textuelle
    q: Optional[str] = Query(None, description="Terme de recherche général"),
    
    # Filtres de base
    property_type: Optional[str] = Query(None, description="Type de propriété"),
    status: Optional[str] = Query(None, description="Statut de la propriété"),
    verified_only: Optional[bool] = Query(False, description="Propriétés vérifiées uniquement"),
    
    # Filtres géographiques
    city: Optional[str] = Query(None, description="Ville"),
    region: Optional[str] = Query(None, description="Région"),
    country: Optional[str] = Query("BF", description="Code pays (défaut: Burkina Faso)"),
    
    # Recherche par coordonnées
    latitude: Optional[float] = Query(None, description="Latitude du centre de recherche"),
    longitude: Optional[float] = Query(None, description="Longitude du centre de recherche"),
    radius_km: Optional[float] = Query(10.0, description="Rayon de recherche en km"),
    
    # Filtres par superficie
    min_area: Optional[float] = Query(None, description="Superficie minimale (m²)"),
    max_area: Optional[float] = Query(None, description="Superficie maximale (m²)"),
    
    # Filtres par prix
    min_price: Optional[float] = Query(None, description="Prix minimum"),
    max_price: Optional[float] = Query(None, description="Prix maximum"),
    
    # Filtres temporels
    registered_after: Optional[date] = Query(None, description="Enregistrées après cette date"),
    registered_before: Optional[date] = Query(None, description="Enregistrées avant cette date"),
    
    # Pagination et tri
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(20, ge=1, le=100, description="Nombre maximum d'éléments à retourner"),
    sort_by: Optional[str] = Query("created_at", description="Champ de tri"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Ordre de tri"),
    
    db=Depends(get_database)
):
    """Recherche avancée de propriétés avec filtres multiples"""
    try:
        # Construction des filtres
        filters = SearchFilters(
            text_query=q,
            property_type=property_type,
            status=status,
            verified_only=verified_only,
            city=city,
            region=region,
            country=country,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            min_area=min_area,
            max_area=max_area,
            min_price=min_price,
            max_price=max_price,
            registered_after=registered_after,
            registered_before=registered_before
        )
        
        # Exécution de la recherche
        results = await search_service.search_properties(
            filters=filters,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            db=db
        )
        
        # Comptage total
        total_count = await search_service.count_search_results(filters, db)
        
        # Statistiques de recherche
        stats = await search_service.get_search_stats(filters, db)
        
        return SearchResponse(
            properties=results,
            total_count=total_count,
            skip=skip,
            limit=limit,
            query_time_ms=stats.get("query_time_ms", 0),
            filters_applied=_build_applied_filters_summary(filters),
            statistics=stats
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )

@router.post("/advanced", response_model=SearchResponse)
async def advanced_search(
    request: SearchRequest,
    db=Depends(get_database)
):
    """Recherche avancée avec requête complexe"""
    try:
        # Validation des paramètres
        if request.geographic_bounds and not all([
            request.geographic_bounds.north_east.latitude,
            request.geographic_bounds.north_east.longitude,
            request.geographic_bounds.south_west.latitude,
            request.geographic_bounds.south_west.longitude
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coordonnées géographiques incomplètes"
            )
        
        # Exécution de la recherche avancée
        results = await search_service.advanced_search(request, db)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la recherche avancée: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche avancée: {str(e)}"
        )

@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    type: Optional[str] = Query("all", description="Type de suggestion (city, region, property_type)"),
    limit: int = Query(10, ge=1, le=20, description="Nombre de suggestions"),
    db=Depends(get_database)
):
    """Suggestions de recherche auto-complétées"""
    try:
        suggestions = await search_service.get_suggestions(
            query=q,
            suggestion_type=type,
            limit=limit,
            db=db
        )
        
        return {
            "query": q,
            "suggestions": suggestions,
            "count": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération des suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération des suggestions"
        )

@router.get("/filters/options")
async def get_filter_options(db=Depends(get_database)):
    """Options disponibles pour les filtres de recherche"""
    try:
        options = await search_service.get_filter_options(db)
        
        return {
            "property_types": options.get("property_types", []),
            "status_options": options.get("status_options", []),
            "cities": options.get("cities", []),
            "regions": options.get("regions", []),
            "price_ranges": options.get("price_ranges", []),
            "area_ranges": options.get("area_ranges", [])
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des options: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des options"
        )

@router.get("/geocode")
async def geocode_address(
    address: str = Query(..., description="Adresse à géocoder"),
    country: str = Query("BF", description="Code pays")
):
    """Géocodage d'une adresse"""
    try:
        result = await geocoding_service.geocode(address, country)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Adresse non trouvée"
            )
        
        return {
            "address": address,
            "coordinates": {
                "latitude": result["latitude"],
                "longitude": result["longitude"]
            },
            "formatted_address": result.get("formatted_address"),
            "components": result.get("components", {}),
            "confidence": result.get("confidence", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du géocodage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du géocodage"
        )

@router.get("/reverse-geocode")
async def reverse_geocode(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude")
):
    """Géocodage inverse (coordonnées vers adresse)"""
    try:
        result = await geocoding_service.reverse_geocode(latitude, longitude)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune adresse trouvée pour ces coordonnées"
            )
        
        return {
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude
            },
            "address": result.get("formatted_address"),
            "components": result.get("components", {}),
            "confidence": result.get("confidence", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du géocodage inverse: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du géocodage inverse"
        )

@router.get("/nearby")
async def find_nearby_properties(
    latitude: float = Query(..., description="Latitude du point de référence"),
    longitude: float = Query(..., description="Longitude du point de référence"),
    radius_km: float = Query(5.0, ge=0.1, le=50.0, description="Rayon de recherche en km"),
    property_type: Optional[str] = Query(None, description="Type de propriété"),
    limit: int = Query(20, ge=1, le=100, description="Nombre maximum de résultats"),
    db=Depends(get_database)
):
    """Recherche de propriétés à proximité d'un point"""
    try:
        # Recherche des propriétés proches
        nearby_properties = await search_service.find_nearby_properties(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            property_type=property_type,
            limit=limit,
            db=db
        )
        
        # Calcul des distances
        reference_point = (latitude, longitude)
        for prop in nearby_properties:
            if prop.get("latitude") and prop.get("longitude"):
                prop_point = (prop["latitude"], prop["longitude"])
                distance = geodesic(reference_point, prop_point).kilometers
                prop["distance_km"] = round(distance, 2)
        
        # Tri par distance
        nearby_properties.sort(key=lambda x: x.get("distance_km", float('inf')))
        
        return {
            "reference_point": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_km": radius_km,
            "properties": nearby_properties,
            "count": len(nearby_properties)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de proximité: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la recherche de proximité"
        )

@router.get("/statistics")
async def get_search_statistics(
    region: Optional[str] = Query(None, description="Région pour les statistiques"),
    property_type: Optional[str] = Query(None, description="Type de propriété"),
    db=Depends(get_database)
):
    """Statistiques de recherche et du registre"""
    try:
        stats = await search_service.get_registry_statistics(
            region=region,
            property_type=property_type,
            db=db
        )
        
        return {
            "total_properties": stats.get("total_properties", 0),
            "verified_properties": stats.get("verified_properties", 0),
            "by_type": stats.get("by_type", {}),
            "by_region": stats.get("by_region", {}),
            "by_status": stats.get("by_status", {}),
            "registration_trends": stats.get("registration_trends", []),
            "average_area": stats.get("average_area", 0),
            "average_price": stats.get("average_price", 0),
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )

@router.get("/export")
async def export_search_results(
    # Même paramètres que search_properties mais pour export
    q: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    verified_only: Optional[bool] = Query(False),
    format: str = Query("csv", regex="^(csv|xlsx|json)$", description="Format d'export"),
    db=Depends(get_database)
):
    """Export des résultats de recherche"""
    try:
        # Construction des filtres
        filters = SearchFilters(
            text_query=q,
            property_type=property_type,
            city=city,
            verified_only=verified_only
        )
        
        # Limitation pour éviter les exports trop volumineux
        MAX_EXPORT_LIMIT = 10000
        
        # Génération du fichier d'export
        export_data = await search_service.export_search_results(
            filters=filters,
            format=format,
            limit=MAX_EXPORT_LIMIT,
            db=db
        )
        
        # Headers pour le téléchargement
        headers = {
            "Content-Disposition": f"attachment; filename=\"properties_export.{format}\""
        }
        
        if format == "csv":
            media_type = "text/csv"
        elif format == "xlsx":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:  # json
            media_type = "application/json"
        
        return StreamingResponse(
            io.BytesIO(export_data),
            media_type=media_type,
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'export: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'export"
        )

def _build_applied_filters_summary(filters: SearchFilters) -> Dict[str, Any]:
    """Construction du résumé des filtres appliqués"""
    applied = {}
    
    if filters.text_query:
        applied["text_search"] = filters.text_query
    if filters.property_type:
        applied["property_type"] = filters.property_type
    if filters.verified_only:
        applied["verified_only"] = True
    if filters.city:
        applied["city"] = filters.city
    if filters.region:
        applied["region"] = filters.region
    if filters.latitude and filters.longitude:
        applied["geographic_search"] = {
            "center": {"lat": filters.latitude, "lng": filters.longitude},
            "radius_km": filters.radius_km
        }
    if filters.min_area or filters.max_area:
        applied["area_range"] = {
            "min": filters.min_area,
            "max": filters.max_area
        }
    if filters.min_price or filters.max_price:
        applied["price_range"] = {
            "min": filters.min_price,
            "max": filters.max_price
        }
    if filters.registered_after or filters.registered_before:
        applied["date_range"] = {
            "after": filters.registered_after,
            "before": filters.registered_before
        }
    
    return applied
