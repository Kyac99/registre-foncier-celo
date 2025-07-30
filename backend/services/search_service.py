"""
Service pour la recherche avancée de propriétés
Logique métier pour filtrage, géolocalisation et statistiques
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import json
import re
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SearchFilters:
    text_query: Optional[str] = None
    property_type: Optional[str] = None
    status: Optional[str] = None
    verified_only: bool = False
    city: Optional[str] = None
    region: Optional[str] = None
    country: str = "BF"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 10.0
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    registered_after: Optional[date] = None
    registered_before: Optional[date] = None

class SearchService:
    def __init__(self):
        self.search_weights = {
            'title': 3.0,
            'description': 2.0,
            'city': 2.5,
            'region': 1.5,
            'address': 2.0,
            'property_type': 1.0
        }
    
    async def search_properties(
        self,
        filters: SearchFilters,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        db = None
    ) -> List[Dict[str, Any]]:
        """Recherche de propriétés avec filtres avancés"""
        try:
            # Construction de la requête SQL
            query_parts = []
            where_clauses = []
            params = []
            param_count = 0
            
            # Sélection de base
            base_query = """
            SELECT DISTINCT p.*, u.name as owner_name,
                   ST_X(p.coordinates) as latitude,
                   ST_Y(p.coordinates) as longitude
            FROM properties p
            LEFT JOIN users u ON p.owner_id = u.user_id
            """
            
            # Jointures supplémentaires si nécessaire
            if filters.verified_only:
                where_clauses.append("p.verified = true")
            
            # Filtres textuels
            if filters.text_query:
                text_conditions = []
                param_count += 1
                search_term = f"%{filters.text_query.lower()}%"
                
                text_conditions.extend([
                    f"LOWER(p.title) LIKE ${param_count}",
                    f"LOWER(p.description) LIKE ${param_count}",
                    f"LOWER(p.city) LIKE ${param_count}",
                    f"LOWER(p.address) LIKE ${param_count}"
                ])
                
                where_clauses.append(f"({' OR '.join(text_conditions)})")
                params.append(search_term)
            
            # Filtres par propriétés
            if filters.property_type:
                param_count += 1
                where_clauses.append(f"p.property_type = ${param_count}")
                params.append(filters.property_type)
            
            if filters.status:
                param_count += 1
                where_clauses.append(f"p.status = ${param_count}")
                params.append(filters.status)
            
            if filters.city:
                param_count += 1
                where_clauses.append(f"LOWER(p.city) LIKE ${param_count}")
                params.append(f"%{filters.city.lower()}%")
            
            if filters.region:
                param_count += 1
                where_clauses.append(f"LOWER(p.region) LIKE ${param_count}")
                params.append(f"%{filters.region.lower()}%")
            
            # Filtres par superficie
            if filters.min_area:
                param_count += 1
                where_clauses.append(f"p.area >= ${param_count}")
                params.append(filters.min_area)
            
            if filters.max_area:
                param_count += 1
                where_clauses.append(f"p.area <= ${param_count}")
                params.append(filters.max_area)
            
            # Filtres par prix
            if filters.min_price:
                param_count += 1
                where_clauses.append(f"p.price >= ${param_count}")
                params.append(filters.min_price)
            
            if filters.max_price:
                param_count += 1
                where_clauses.append(f"p.price <= ${param_count}")
                params.append(filters.max_price)
            
            # Filtres temporels
            if filters.registered_after:
                param_count += 1
                where_clauses.append(f"p.created_at >= ${param_count}")
                params.append(filters.registered_after)
            
            if filters.registered_before:
                param_count += 1
                where_clauses.append(f"p.created_at <= ${param_count}")
                params.append(filters.registered_before)
            
            # Filtrage géographique
            distance_select = ""
            if filters.latitude and filters.longitude:
                param_count += 2
                # Calcul de la distance en km
                distance_select = f"""
                , ST_Distance(
                    ST_GeogFromText('POINT({filters.longitude} {filters.latitude})'),
                    ST_GeogFromText('POINT(' || ST_X(p.coordinates) || ' ' || ST_Y(p.coordinates) || ')')
                ) / 1000.0 as distance_km
                """
                
                where_clauses.append(f"""
                ST_DWithin(
                    ST_GeogFromText('POINT({filters.longitude} {filters.latitude})'),
                    ST_GeogFromText('POINT(' || ST_X(p.coordinates) || ' ' || ST_Y(p.coordinates) || ')'),
                    ${param_count - 1} * 1000
                )
                """)
                params.extend([filters.radius_km])
            
            # Assemblage de la requête
            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)
            
            # Ajout de la sélection de distance
            if distance_select:
                base_query = base_query.replace("p.*, u.name", f"p.*, u.name{distance_select}")
            
            # Tri
            sort_column = self._get_sort_column(sort_by)
            sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
            
            if filters.latitude and filters.longitude and sort_by == "distance":
                base_query += " ORDER BY distance_km ASC"
            else:
                base_query += f" ORDER BY {sort_column} {sort_direction}"
            
            # Pagination
            param_count += 2
            base_query += f" LIMIT ${param_count - 1} OFFSET ${param_count}"
            params.extend([limit, skip])
            
            # Exécution de la requête
            results = await db.fetch(base_query, *params)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {str(e)}")
            raise
    
    async def count_search_results(
        self,
        filters: SearchFilters,
        db
    ) -> int:
        """Comptage des résultats de recherche"""
        try:
            where_clauses = []
            params = []
            param_count = 0
            
            # Même logique de filtrage que search_properties mais pour COUNT
            if filters.verified_only:
                where_clauses.append("verified = true")
            
            if filters.text_query:
                param_count += 1
                search_term = f"%{filters.text_query.lower()}%"
                text_conditions = [
                    f"LOWER(title) LIKE ${param_count}",
                    f"LOWER(description) LIKE ${param_count}",
                    f"LOWER(city) LIKE ${param_count}",
                    f"LOWER(address) LIKE ${param_count}"
                ]
                where_clauses.append(f"({' OR '.join(text_conditions)})")
                params.append(search_term)
            
            if filters.property_type:
                param_count += 1
                where_clauses.append(f"property_type = ${param_count}")
                params.append(filters.property_type)
            
            if filters.status:
                param_count += 1
                where_clauses.append(f"status = ${param_count}")
                params.append(filters.status)
            
            if filters.city:
                param_count += 1
                where_clauses.append(f"LOWER(city) LIKE ${param_count}")
                params.append(f"%{filters.city.lower()}%")
            
            if filters.region:
                param_count += 1
                where_clauses.append(f"LOWER(region) LIKE ${param_count}")
                params.append(f"%{filters.region.lower()}%")
            
            if filters.min_area:
                param_count += 1
                where_clauses.append(f"area >= ${param_count}")
                params.append(filters.min_area)
            
            if filters.max_area:
                param_count += 1
                where_clauses.append(f"area <= ${param_count}")
                params.append(filters.max_area)
            
            if filters.min_price:
                param_count += 1
                where_clauses.append(f"price >= ${param_count}")
                params.append(filters.min_price)
            
            if filters.max_price:
                param_count += 1
                where_clauses.append(f"price <= ${param_count}")
                params.append(filters.max_price)
            
            if filters.registered_after:
                param_count += 1
                where_clauses.append(f"created_at >= ${param_count}")
                params.append(filters.registered_after)
            
            if filters.registered_before:
                param_count += 1
                where_clauses.append(f"created_at <= ${param_count}")
                params.append(filters.registered_before)
            
            # Filtrage géographique
            if filters.latitude and filters.longitude:
                param_count += 1
                where_clauses.append(f"""
                ST_DWithin(
                    ST_GeogFromText('POINT({filters.longitude} {filters.latitude})'),
                    ST_GeogFromText('POINT(' || ST_X(coordinates) || ' ' || ST_Y(coordinates) || ')'),
                    ${param_count} * 1000
                )
                """)
                params.append(filters.radius_km)
            
            query = "SELECT COUNT(*) FROM properties"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            result = await db.fetchval(query, *params)
            return result or 0
            
        except Exception as e:
            logger.error(f"Erreur lors du comptage: {str(e)}")
            return 0
    
    async def get_suggestions(
        self,
        query: str,
        suggestion_type: str = "all",
        limit: int = 10,
        db = None
    ) -> List[str]:
        """Génération de suggestions de recherche"""
        try:
            suggestions = []
            search_term = f"%{query.lower()}%"
            
            if suggestion_type in ["all", "city"]:
                # Suggestions de villes
                city_query = """
                SELECT DISTINCT city, COUNT(*) as count 
                FROM properties 
                WHERE LOWER(city) LIKE $1 
                GROUP BY city 
                ORDER BY count DESC, city ASC 
                LIMIT $2
                """
                city_results = await db.fetch(city_query, search_term, limit // 3)
                suggestions.extend([row['city'] for row in city_results])
            
            if suggestion_type in ["all", "region"]:
                # Suggestions de régions
                region_query = """
                SELECT DISTINCT region, COUNT(*) as count 
                FROM properties 
                WHERE LOWER(region) LIKE $1 
                GROUP BY region 
                ORDER BY count DESC, region ASC 
                LIMIT $2
                """
                region_results = await db.fetch(region_query, search_term, limit // 3)
                suggestions.extend([row['region'] for row in region_results])
            
            if suggestion_type in ["all", "property_type"]:
                # Suggestions de types de propriété
                type_suggestions = [
                    "Résidentiel", "Commercial", "Industriel", 
                    "Agricole", "Terrain nu", "Autre"
                ]
                matching_types = [
                    t for t in type_suggestions 
                    if query.lower() in t.lower()
                ]
                suggestions.extend(matching_types[:limit//3])
            
            # Suppression des doublons et limitation
            unique_suggestions = list(dict.fromkeys(suggestions))
            return unique_suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de suggestions: {str(e)}")
            return []
    
    async def get_filter_options(self, db) -> Dict[str, List[Dict[str, Any]]]:
        """Options disponibles pour les filtres"""
        try:
            options = {}
            
            # Types de propriété
            type_query = """
            SELECT property_type, COUNT(*) as count 
            FROM properties 
            GROUP BY property_type 
            ORDER BY count DESC
            """
            type_results = await db.fetch(type_query)
            options['property_types'] = [
                {'value': row['property_type'], 'label': row['property_type'], 'count': row['count']}
                for row in type_results
            ]
            
            # Statuts
            status_query = """
            SELECT status, COUNT(*) as count 
            FROM properties 
            GROUP BY status 
            ORDER BY count DESC
            """
            status_results = await db.fetch(status_query)
            options['status_options'] = [
                {'value': row['status'], 'label': row['status'], 'count': row['count']}
                for row in status_results
            ]
            
            # Villes populaires
            city_query = """
            SELECT city, COUNT(*) as count 
            FROM properties 
            GROUP BY city 
            ORDER BY count DESC 
            LIMIT 20
            """
            city_results = await db.fetch(city_query)
            options['cities'] = [
                {'value': row['city'], 'label': row['city'], 'count': row['count']}
                for row in city_results
            ]
            
            # Régions
            region_query = """
            SELECT region, COUNT(*) as count 
            FROM properties 
            GROUP BY region 
            ORDER BY count DESC
            """
            region_results = await db.fetch(region_query)
            options['regions'] = [
                {'value': row['region'], 'label': row['region'], 'count': row['count']}
                for row in region_results
            ]
            
            # Gammes de prix
            price_ranges = [
                {'value': '0-5000000', 'label': '0 - 5M FCFA', 'min': 0, 'max': 5000000},
                {'value': '5000000-15000000', 'label': '5M - 15M FCFA', 'min': 5000000, 'max': 15000000},
                {'value': '15000000-50000000', 'label': '15M - 50M FCFA', 'min': 15000000, 'max': 50000000},
                {'value': '50000000+', 'label': '50M+ FCFA', 'min': 50000000, 'max': None}
            ]
            
            # Compter les propriétés dans chaque gamme
            for price_range in price_ranges:
                if price_range['max']:
                    count_query = """
                    SELECT COUNT(*) FROM properties 
                    WHERE price >= $1 AND price <= $2
                    """
                    count = await db.fetchval(count_query, price_range['min'], price_range['max'])
                else:
                    count_query = """
                    SELECT COUNT(*) FROM properties 
                    WHERE price >= $1
                    """
                    count = await db.fetchval(count_query, price_range['min'])
                
                price_range['count'] = count or 0
            
            options['price_ranges'] = price_ranges
            
            # Gammes de superficie
            area_ranges = [
                {'value': '0-500', 'label': '0 - 500 m²', 'min': 0, 'max': 500},
                {'value': '500-1000', 'label': '500 - 1000 m²', 'min': 500, 'max': 1000},
                {'value': '1000-5000', 'label': '1000 - 5000 m²', 'min': 1000, 'max': 5000},
                {'value': '5000+', 'label': '5000+ m²', 'min': 5000, 'max': None}
            ]
            
            for area_range in area_ranges:
                if area_range['max']:
                    count_query = """
                    SELECT COUNT(*) FROM properties 
                    WHERE area >= $1 AND area <= $2
                    """
                    count = await db.fetchval(count_query, area_range['min'], area_range['max'])
                else:
                    count_query = """
                    SELECT COUNT(*) FROM properties 
                    WHERE area >= $1
                    """
                    count = await db.fetchval(count_query, area_range['min'])
                
                area_range['count'] = count or 0
            
            options['area_ranges'] = area_ranges
            
            return options
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des options: {str(e)}")
            return {}
    
    async def find_nearby_properties(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        property_type: Optional[str] = None,
        limit: int = 20,
        db = None
    ) -> List[Dict[str, Any]]:
        """Recherche de propriétés à proximité"""
        try:
            where_clauses = []
            params = []
            param_count = 0
            
            # Filtre géographique obligatoire
            param_count += 1
            where_clauses.append(f"""
            ST_DWithin(
                ST_GeogFromText('POINT({longitude} {latitude})'),
                ST_GeogFromText('POINT(' || ST_X(coordinates) || ' ' || ST_Y(coordinates) || ')'),
                ${param_count} * 1000
            )
            """)
            params.append(radius_km)
            
            # Filtre par type si spécifié
            if property_type:
                param_count += 1
                where_clauses.append(f"property_type = ${param_count}")
                params.append(property_type)
            
            where_clause = " AND ".join(where_clauses)
            
            query = f"""
            SELECT *, 
                   ST_X(coordinates) as latitude,
                   ST_Y(coordinates) as longitude,
                   ST_Distance(
                       ST_GeogFromText('POINT({longitude} {latitude})'),
                       ST_GeogFromText('POINT(' || ST_X(coordinates) || ' ' || ST_Y(coordinates) || ')')
                   ) / 1000.0 as distance_km
            FROM properties 
            WHERE {where_clause}
            ORDER BY distance_km ASC
            LIMIT ${param_count + 1}
            """
            
            params.append(limit)
            
            results = await db.fetch(query, *params)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de proximité: {str(e)}")
            return []
    
    async def get_search_stats(
        self,
        filters: SearchFilters,
        db
    ) -> Dict[str, Any]:
        """Statistiques de recherche"""
        try:
            start_time = datetime.now()
            
            # Temps de requête simulé
            query_time_ms = 50  # Placeholder
            
            stats = {
                'query_time_ms': query_time_ms,
                'filters_applied': self._count_active_filters(filters),
                'search_complexity': self._calculate_search_complexity(filters)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des stats: {str(e)}")
            return {}
    
    async def get_registry_statistics(
        self,
        region: Optional[str] = None,
        property_type: Optional[str] = None,
        db = None
    ) -> Dict[str, Any]:
        """Statistiques générales du registre"""
        try:
            where_clauses = []
            params = []
            param_count = 0
            
            if region:
                param_count += 1
                where_clauses.append(f"region = ${param_count}")
                params.append(region)
            
            if property_type:
                param_count += 1
                where_clauses.append(f"property_type = ${param_count}")
                params.append(property_type)
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            # Statistiques générales
            general_query = f"""
            SELECT 
                COUNT(*) as total_properties,
                COUNT(CASE WHEN verified = true THEN 1 END) as verified_properties,
                AVG(area) as average_area,
                AVG(price) as average_price
            FROM properties {where_clause}
            """
            
            general_stats = await db.fetchrow(general_query, *params)
            
            # Répartition par type
            type_query = f"""
            SELECT property_type, COUNT(*) as count 
            FROM properties {where_clause}
            GROUP BY property_type 
            ORDER BY count DESC
            """
            
            type_stats = await db.fetch(type_query, *params)
            
            # Répartition par région
            region_query = f"""
            SELECT region, COUNT(*) as count 
            FROM properties {where_clause}
            GROUP BY region 
            ORDER BY count DESC
            """
            
            region_stats = await db.fetch(region_query, *params)
            
            # Répartition par statut
            status_query = f"""
            SELECT status, COUNT(*) as count 
            FROM properties {where_clause}
            GROUP BY status 
            ORDER BY count DESC
            """
            
            status_stats = await db.fetch(status_query, *params)
            
            # Tendances d'enregistrement (6 derniers mois)
            trends_query = f"""
            SELECT 
                DATE_TRUNC('month', created_at) as month,
                COUNT(*) as count
            FROM properties 
            WHERE created_at >= NOW() - INTERVAL '6 months' {('AND ' + ' AND '.join(where_clauses)) if where_clauses else ''}
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY month ASC
            """
            
            trends_stats = await db.fetch(trends_query, *params)
            
            return {
                'total_properties': general_stats['total_properties'],
                'verified_properties': general_stats['verified_properties'],
                'average_area': float(general_stats['average_area'] or 0),
                'average_price': float(general_stats['average_price'] or 0),
                'by_type': {row['property_type']: row['count'] for row in type_stats},
                'by_region': {row['region']: row['count'] for row in region_stats},
                'by_status': {row['status']: row['count'] for row in status_stats},
                'registration_trends': [
                    {
                        'month': row['month'].strftime('%Y-%m'),
                        'count': row['count']
                    } for row in trends_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
            return {}
    
    def _get_sort_column(self, sort_by: str) -> str:
        """Mapping des colonnes de tri"""
        sort_mapping = {
            'created_at': 'p.created_at',
            'updated_at': 'p.updated_at',
            'title': 'p.title',
            'city': 'p.city',
            'area': 'p.area',
            'price': 'p.price',
            'distance': 'distance_km'
        }
        return sort_mapping.get(sort_by, 'p.created_at')
    
    def _count_active_filters(self, filters: SearchFilters) -> int:
        """Comptage des filtres actifs"""
        count = 0
        if filters.text_query:
            count += 1
        if filters.property_type:
            count += 1
        if filters.status:
            count += 1
        if filters.verified_only:
            count += 1
        if filters.city:
            count += 1
        if filters.region:
            count += 1
        if filters.latitude and filters.longitude:
            count += 1
        if filters.min_area or filters.max_area:
            count += 1
        if filters.min_price or filters.max_price:
            count += 1
        if filters.registered_after or filters.registered_before:
            count += 1
        
        return count
    
    def _calculate_search_complexity(self, filters: SearchFilters) -> str:
        """Calcul de la complexité de recherche"""
        active_filters = self._count_active_filters(filters)
        
        if active_filters == 0:
            return "simple"
        elif active_filters <= 3:
            return "medium"
        else:
            return "complex"