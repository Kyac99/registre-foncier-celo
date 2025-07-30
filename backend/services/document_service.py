"""
Service pour la gestion des documents
Logique métier pour upload, vérification et accès aux documents
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import mimetypes
import hashlib

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.allowed_mime_types = {
            'application/pdf',
            'image/jpeg',
            'image/jpg', 
            'image/png',
            'image/tiff',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.document_types = {
            'title_deed': {
                'name': 'Acte de propriété',
                'required': True,
                'description': 'Document officiel attestant de la propriété'
            },
            'survey_plan': {
                'name': 'Plan d\'arpentage',
                'required': True,
                'description': 'Plan technique de délimitation du terrain'
            },
            'tax_receipt': {
                'name': 'Reçu de taxe foncière',
                'required': False,
                'description': 'Justificatif de paiement des taxes'
            },
            'cadastral_map': {
                'name': 'Plan cadastral',
                'required': False,
                'description': 'Carte cadastrale officielle'
            },
            'building_permit': {
                'name': 'Permis de construire',
                'required': False,
                'description': 'Autorisation de construction'
            },
            'identity_document': {
                'name': 'Pièce d\'identité',
                'required': False,
                'description': 'Document d\'identité du propriétaire'
            },
            'other': {
                'name': 'Autre document',
                'required': False,
                'description': 'Tout autre document pertinent'
            }
        }
    
    async def create_document(
        self,
        property_id: str,
        document_type: str,
        title: str,
        description: Optional[str],
        ipfs_hash: str,
        metadata: Dict[str, Any],
        is_public: bool,
        uploader_id: str,
        db
    ) -> str:
        """Création d'un nouveau document en base"""
        try:
            document_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO documents (
                document_id, property_id, document_type, title, description,
                ipfs_hash, metadata, is_public, uploader_id, verification_status,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending', NOW(), NOW()
            ) RETURNING document_id
            """
            
            result = await db.execute(
                query,
                document_id, property_id, document_type, title, description,
                ipfs_hash, metadata, is_public, uploader_id
            )
            
            # Log de l'activité
            await self._log_document_activity(
                document_id, uploader_id, 'upload', 
                {'filename': metadata.get('filename')}, db
            )
            
            logger.info(f"Document {document_id} créé pour la propriété {property_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du document: {str(e)}")
            raise
    
    async def get_document(self, document_id: str, db) -> Optional[Dict[str, Any]]:
        """Récupération d'un document par ID"""
        try:
            query = """
            SELECT d.*, u.name as uploader_name, v.name as verifier_name
            FROM documents d
            LEFT JOIN users u ON d.uploader_id = u.user_id
            LEFT JOIN users v ON d.verifier_id = v.user_id
            WHERE d.document_id = $1 AND d.deleted_at IS NULL
            """
            
            result = await db.fetchrow(query, document_id)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du document: {str(e)}")
            raise
    
    async def get_property_documents(
        self,
        property_id: str,
        document_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        user_id: Optional[str] = None,
        db = None
    ) -> List[Dict[str, Any]]:
        """Récupération des documents d'une propriété"""
        try:
            # Construction de la requête avec filtres
            where_clauses = ["d.property_id = $1", "d.deleted_at IS NULL"]
            params = [property_id]
            param_count = 1
            
            if document_type:
                param_count += 1
                where_clauses.append(f"d.document_type = ${param_count}")
                params.append(document_type)
            
            # Filtrage selon les permissions
            if user_id:
                # Vérifier si l'utilisateur a accès à cette propriété
                has_access = await self.verify_property_access(property_id, user_id, db)
                if not has_access:
                    param_count += 1
                    where_clauses.append(f"d.is_public = true")
            
            where_clause = " AND ".join(where_clauses)
            
            query = f"""
            SELECT d.*, u.name as uploader_name, v.name as verifier_name
            FROM documents d
            LEFT JOIN users u ON d.uploader_id = u.user_id
            LEFT JOIN users v ON d.verifier_id = v.user_id
            WHERE {where_clause}
            ORDER BY d.created_at DESC
            LIMIT $@{param_count + 1} OFFSET $@{param_count + 2}
            """
            
            params.extend([limit, skip])
            
            result = await db.fetch(query, *params)
            
            return [dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des documents: {str(e)}")
            raise
    
    async def count_property_documents(
        self,
        property_id: str,
        document_type: Optional[str],
        user_id: Optional[str],
        db
    ) -> int:
        """Comptage des documents d'une propriété"""
        try:
            where_clauses = ["property_id = $1", "deleted_at IS NULL"]
            params = [property_id]
            param_count = 1
            
            if document_type:
                param_count += 1
                where_clauses.append(f"document_type = ${param_count}")
                params.append(document_type)
            
            if user_id:
                has_access = await self.verify_property_access(property_id, user_id, db)
                if not has_access:
                    where_clauses.append("is_public = true")
            
            where_clause = " AND ".join(where_clauses)
            
            query = f"SELECT COUNT(*) FROM documents WHERE {where_clause}"
            
            result = await db.fetchval(query, *params)
            return result or 0
            
        except Exception as e:
            logger.error(f"Erreur lors du comptage des documents: {str(e)}")
            return 0
    
    async def update_verification_status(
        self,
        document_id: str,
        status: str,
        comment: Optional[str],
        verifier_id: str,
        db
    ) -> Optional[Dict[str, Any]]:
        """Mise à jour du statut de vérification"""
        try:
            valid_statuses = ['pending', 'approved', 'rejected', 'pending_review']
            if status not in valid_statuses:
                raise ValueError(f"Statut invalide: {status}")
            
            query = """
            UPDATE documents 
            SET verification_status = $1, verification_comment = $2, 
                verifier_id = $3, verification_date = NOW(), updated_at = NOW()
            WHERE document_id = $4 AND deleted_at IS NULL
            RETURNING *
            """
            
            result = await db.fetchrow(
                query, status, comment, verifier_id, document_id
            )
            
            if result:
                # Log de l'activité
                await self._log_document_activity(
                    document_id, verifier_id, 'verification',
                    {'status': status, 'comment': comment}, db
                )
                
                # Récupération avec les noms
                verified_doc = await self.get_document(document_id, db)
                
                logger.info(f"Document {document_id} vérification mise à jour: {status}")
                return verified_doc
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de vérification: {str(e)}")
            raise
    
    async def delete_document(
        self,
        document_id: str,
        user_id: str,
        db
    ) -> bool:
        """Suppression (soft delete) d'un document"""
        try:
            query = """
            UPDATE documents 
            SET deleted_at = NOW(), deleted_by = $1, updated_at = NOW()
            WHERE document_id = $2 AND deleted_at IS NULL
            """
            
            result = await db.execute(query, user_id, document_id)
            
            if result:
                # Log de l'activité
                await self._log_document_activity(
                    document_id, user_id, 'delete', {}, db
                )
                
                logger.info(f"Document {document_id} supprimé par {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du document: {str(e)}")
            raise
    
    async def verify_property_access(
        self,
        property_id: str,
        user_id: str,
        db
    ) -> bool:
        """Vérification des droits d'accès à une propriété"""
        try:
            # Vérifier si l'utilisateur est propriétaire
            query = """
            SELECT COUNT(*) FROM properties 
            WHERE property_id = $1 AND owner_id = $2
            """
            
            owner_count = await db.fetchval(query, property_id, user_id)
            if owner_count > 0:
                return True
            
            # Vérifier si l'utilisateur est admin ou vérificateur
            query = """
            SELECT is_admin, is_verifier FROM users 
            WHERE user_id = $1
            """
            
            user_info = await db.fetchrow(query, user_id)
            if user_info and (user_info['is_admin'] or user_info['is_verifier']):
                return True
            
            # Vérifier les permissions spécifiques accordées
            query = """
            SELECT COUNT(*) FROM property_permissions 
            WHERE property_id = $1 AND user_id = $2 AND access_type IN ('read', 'write', 'admin')
            """
            
            permission_count = await db.fetchval(query, property_id, user_id)
            return permission_count > 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'accès: {str(e)}")
            return False
    
    async def verify_document_access(
        self,
        document_id: str,
        user_id: str,
        db
    ) -> bool:
        """Vérification des droits d'accès à un document"""
        try:
            # Récupérer les infos du document
            query = """
            SELECT property_id, is_public, uploader_id 
            FROM documents 
            WHERE document_id = $1 AND deleted_at IS NULL
            """
            
            doc_info = await db.fetchrow(query, document_id)
            if not doc_info:
                return False
            
            # Document public
            if doc_info['is_public']:
                return True
            
            # Uploader du document
            if doc_info['uploader_id'] == user_id:
                return True
            
            # Accès via la propriété
            return await self.verify_property_access(doc_info['property_id'], user_id, db)
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'accès document: {str(e)}")
            return False
    
    async def get_by_hash(self, file_hash: str, db) -> Optional[Dict[str, Any]]:
        """Récupération d'un document par son hash"""
        try:
            query = """
            SELECT * FROM documents 
            WHERE metadata->>'hash_sha256' = $1 AND deleted_at IS NULL
            """
            
            result = await db.fetchrow(query, file_hash)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par hash: {str(e)}")
            return None
    
    async def log_download(
        self,
        document_id: str,
        user_id: str,
        db
    ):
        """Enregistrement d'un téléchargement"""
        try:
            await self._log_document_activity(
                document_id, user_id, 'download', {}, db
            )
            
            # Mise à jour du compteur de téléchargements
            query = """
            UPDATE documents 
            SET download_count = COALESCE(download_count, 0) + 1,
                last_downloaded_at = NOW()
            WHERE document_id = $1
            """
            
            await db.execute(query, document_id)
            
        except Exception as e:
            logger.error(f"Erreur lors du log de téléchargement: {str(e)}")
    
    async def _log_document_activity(
        self,
        document_id: str,
        user_id: str,
        action: str,
        details: Dict[str, Any],
        db
    ):
        """Enregistrement d'une activité sur un document"""
        try:
            query = """
            INSERT INTO document_activity_logs (
                document_id, user_id, action, details, created_at
            ) VALUES ($1, $2, $3, $4, NOW())
            """
            
            await db.execute(query, document_id, user_id, action, details)
            
        except Exception as e:
            logger.error(f"Erreur lors du log d'activité: {str(e)}")
    
    def validate_file(
        self,
        filename: str,
        content: bytes,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validation d'un fichier"""
        errors = []
        warnings = []
        
        # Vérification de la taille
        if len(content) > self.max_file_size:
            errors.append(f"Fichier trop volumineux ({len(content)} bytes > {self.max_file_size})")
        
        # Vérification du type MIME
        detected_mime = mimetypes.guess_type(filename)[0] or mime_type
        if detected_mime not in self.allowed_mime_types:
            errors.append(f"Type de fichier non autorisé: {detected_mime}")
        
        # Vérification de l'extension
        if '.' not in filename:
            warnings.append("Fichier sans extension")
        
        # Vérification du contenu (basique)
        if len(content) == 0:
            errors.append("Fichier vide")
        
        # Vérification de signatures de fichiers (magic numbers)
        if detected_mime == 'application/pdf' and not content.startswith(b'%PDF'):
            warnings.append("Fichier PDF potentiellement corrompu")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'detected_mime_type': detected_mime
        }
    
    async def get_document_statistics(
        self,
        property_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db = None
    ) -> Dict[str, Any]:
        """Statistiques sur les documents"""
        try:
            where_clauses = ["deleted_at IS NULL"]
            params = []
            param_count = 0
            
            if property_id:
                param_count += 1
                where_clauses.append(f"property_id = ${param_count}")
                params.append(property_id)
            
            if user_id:
                param_count += 1
                where_clauses.append(f"uploader_id = ${param_count}")
                params.append(user_id)
            
            where_clause = " AND ".join(where_clauses)
            
            # Statistiques générales
            query = f"""
            SELECT 
                COUNT(*) as total_documents,
                COUNT(CASE WHEN verification_status = 'approved' THEN 1 END) as approved_documents,
                COUNT(CASE WHEN verification_status = 'rejected' THEN 1 END) as rejected_documents,
                COUNT(CASE WHEN verification_status = 'pending' THEN 1 END) as pending_documents,
                COUNT(CASE WHEN is_public = true THEN 1 END) as public_documents,
                SUM(COALESCE(download_count, 0)) as total_downloads
            FROM documents
            WHERE {where_clause}
            """
            
            general_stats = await db.fetchrow(query, *params)
            
            # Répartition par type
            query = f"""
            SELECT document_type, COUNT(*) as count
            FROM documents
            WHERE {where_clause}
            GROUP BY document_type
            ORDER BY count DESC
            """
            
            type_stats = await db.fetch(query, *params)
            
            # Taille totale
            query = f"""
            SELECT SUM((metadata->>'size')::bigint) as total_size
            FROM documents
            WHERE {where_clause} AND metadata->>'size' IS NOT NULL
            """
            
            size_result = await db.fetchval(query, *params)
            
            return {
                'total_documents': general_stats['total_documents'],
                'approved_documents': general_stats['approved_documents'],
                'rejected_documents': general_stats['rejected_documents'],
                'pending_documents': general_stats['pending_documents'],
                'public_documents': general_stats['public_documents'],
                'total_downloads': general_stats['total_downloads'],
                'total_size_bytes': size_result or 0,
                'by_type': {row['document_type']: row['count'] for row in type_stats},
                'verification_rate': (
                    general_stats['approved_documents'] / general_stats['total_documents'] * 100
                    if general_stats['total_documents'] > 0 else 0
                )
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
            return {}
    
    def get_document_types(self) -> Dict[str, Dict[str, Any]]:
        """Récupération des types de documents disponibles"""
        return self.document_types.copy()
    
    async def check_required_documents(
        self,
        property_id: str,
        db
    ) -> Dict[str, Any]:
        """Vérification des documents requis pour une propriété"""
        try:
            # Récupération des documents existants
            existing_docs = await self.get_property_documents(property_id, db=db)
            existing_types = {doc['document_type'] for doc in existing_docs}
            
            # Vérification des types requis
            required_types = {
                doc_type for doc_type, info in self.document_types.items()
                if info['required']
            }
            
            missing_required = required_types - existing_types
            has_all_required = len(missing_required) == 0
            
            return {
                'has_all_required': has_all_required,
                'missing_required': list(missing_required),
                'existing_types': list(existing_types),
                'required_types': list(required_types),
                'completion_rate': (
                    len(existing_types & required_types) / len(required_types) * 100
                    if required_types else 100
                )
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des documents requis: {str(e)}")
            return {
                'has_all_required': False,
                'missing_required': [],
                'existing_types': [],
                'required_types': [],
                'completion_rate': 0
            }