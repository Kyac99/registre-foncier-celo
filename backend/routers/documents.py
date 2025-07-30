"""
Router pour la gestion des documents
Upload, stockage IPFS, vérification et téléchargement
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import asyncio
import logging
import hashlib
import mimetypes
from datetime import datetime
import io

from config.database import get_database
from config.settings import settings
from services.ipfs_service import IPFSService
from services.document_service import DocumentService
from services.blockchain_service import BlockchainService
from schemas.documents import (
    DocumentResponse, 
    DocumentUpload, 
    DocumentVerification,
    DocumentMetadata,
    DocumentList
)
from middleware.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()

# Services
ipfs_service = IPFSService()
document_service = DocumentService()
blockchain_service = BlockchainService()

# Taille maximale des fichiers (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Types de fichiers autorisés
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
}

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    property_id: str = Form(...),
    document_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    is_public: bool = Form(False),
    db=Depends(get_database),
    current_user=Depends(verify_token)
):
    """Upload d'un document et stockage sur IPFS"""
    try:
        # Vérifications de base
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nom de fichier requis"
            )
        
        # Lecture du contenu du fichier
        content = await file.read()
        file_size = len(content)
        
        # Vérification de la taille
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Fichier trop volumineux. Taille maximale: {MAX_FILE_SIZE//1024//1024}MB"
            )
        
        # Vérification du type MIME
        mime_type = mimetypes.guess_type(file.filename)[0]
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type de fichier non autorisé: {mime_type}"
            )
        
        # Calcul du hash du fichier
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Vérification si le document existe déjà
        existing_doc = await document_service.get_by_hash(file_hash, db)
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce document a déjà été uploadé"
            )
        
        # Vérification des permissions sur la propriété
        property_exists = await document_service.verify_property_access(
            property_id, current_user["user_id"], db
        )
        if not property_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cette propriété"
            )
        
        # Upload sur IPFS
        ipfs_hash = await ipfs_service.upload_file(content, file.filename)
        
        # Création des métadonnées
        metadata = DocumentMetadata(
            filename=file.filename,
            mime_type=mime_type,
            size=file_size,
            hash_sha256=file_hash,
            upload_timestamp=datetime.utcnow(),
            uploader_id=current_user["user_id"]
        )
        
        # Sauvegarde en base de données
        document_id = await document_service.create_document(
            property_id=property_id,
            document_type=document_type,
            title=title,
            description=description,
            ipfs_hash=ipfs_hash,
            metadata=metadata.dict(),
            is_public=is_public,
            uploader_id=current_user["user_id"],
            db=db
        )
        
        # Enregistrement sur la blockchain en arrière-plan
        if settings.BLOCKCHAIN_DOCUMENT_REGISTRATION:
            background_tasks.add_task(
                register_document_on_blockchain,
                document_id,
                ipfs_hash,
                file_hash
            )
        
        return DocumentResponse(
            document_id=document_id,
            property_id=property_id,
            title=title,
            document_type=document_type,
            ipfs_hash=ipfs_hash,
            filename=file.filename,
            size=file_size,
            mime_type=mime_type,
            upload_timestamp=datetime.utcnow(),
            is_public=is_public,
            verification_status="pending",
            uploader_name=current_user.get("name", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'upload du document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'upload: {str(e)}"
        )

@router.get("/property/{property_id}", response_model=DocumentList)
async def get_property_documents(
    property_id: str,
    document_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_database),
    current_user=Depends(verify_token)
):
    """Liste des documents d'une propriété"""
    try:
        # Vérification des permissions
        has_access = await document_service.verify_property_access(
            property_id, current_user["user_id"], db
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cette propriété"
            )
        
        # Récupération des documents
        documents = await document_service.get_property_documents(
            property_id=property_id,
            document_type=document_type,
            skip=skip,
            limit=limit,
            user_id=current_user["user_id"],
            db=db
        )
        
        total_count = await document_service.count_property_documents(
            property_id, document_type, current_user["user_id"], db
        )
        
        return DocumentList(
            documents=documents,
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_info(
    document_id: str,
    db=Depends(get_database),
    current_user=Depends(verify_token)
):
    """Informations détaillées d'un document"""
    try:
        document = await document_service.get_document(document_id, db)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        # Vérification des permissions
        if not document["is_public"]:
            has_access = await document_service.verify_document_access(
                document_id, current_user["user_id"], db
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès non autorisé à ce document"
                )
        
        return DocumentResponse(**document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db=Depends(get_database),
    current_user=Depends(verify_token)
):
    """Téléchargement d'un document depuis IPFS"""
    try:
        # Récupération des informations du document
        document = await document_service.get_document(document_id, db)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        # Vérification des permissions
        if not document["is_public"]:
            has_access = await document_service.verify_document_access(
                document_id, current_user["user_id"], db
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès non autorisé à ce document"
                )
        
        # Téléchargement depuis IPFS
        file_content = await ipfs_service.download_file(document["ipfs_hash"])
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non trouvé sur IPFS"
            )
        
        # Vérification de l'intégrité
        file_hash = hashlib.sha256(file_content).hexdigest()
        if file_hash != document["metadata"].get("hash_sha256"):
            logger.error(f"Intégrité compromise pour le document {document_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Intégrité du fichier compromise"
            )
        
        # Enregistrement du téléchargement
        await document_service.log_download(
            document_id, current_user["user_id"], db
        )
        
        # Retour du fichier
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=document["mime_type"],
            headers={
                "Content-Disposition": f"attachment; filename=\"{document['filename']}\""
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du téléchargement: {str(e)}"
        )

@router.post("/{document_id}/verify", response_model=DocumentVerification)
async def verify_document(
    document_id: str,
    verification_status: str = Form(...),
    verification_comment: Optional[str] = Form(None),
    db=Depends(get_database),
    current_user=Depends(verify_token)
):
    """Vérification d'un document par une autorité compétente"""
    try:
        # Vérification des permissions de vérification
        if not current_user.get("is_verifier"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions de vérification requises"
            )
        
        # Vérification des statuts autorisés
        if verification_status not in ["approved", "rejected", "pending_review"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Statut de vérification invalide"
            )
        
        # Mise à jour du statut
        verification = await document_service.update_verification_status(
            document_id=document_id,
            status=verification_status,
            comment=verification_comment,
            verifier_id=current_user["user_id"],
            db=db
        )
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        return DocumentVerification(**verification)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la vérification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db=Depends(get_database),
    current_user=Depends(verify_token)
):
    """Suppression d'un document"""
    try:
        # Vérification de l'existence et des permissions
        document = await document_service.get_document(document_id, db)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        # Seul l'uploadeur ou un admin peut supprimer
        if (document["uploader_id"] != current_user["user_id"] and 
            not current_user.get("is_admin")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes pour supprimer ce document"
            )
        
        # Suppression (soft delete)
        success = await document_service.delete_document(
            document_id, current_user["user_id"], db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression"
            )
        
        return {"message": "Document supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )

@router.get("/types/available")
async def get_document_types():
    """Liste des types de documents disponibles"""
    return {
        "document_types": [
            {
                "id": "title_deed",
                "name": "Acte de propriété",
                "description": "Document officiel attestant de la propriété",
                "required": True
            },
            {
                "id": "survey_plan",
                "name": "Plan d'arpentage",
                "description": "Plan technique de délimitation du terrain",
                "required": True
            },
            {
                "id": "tax_receipt",
                "name": "Reçu de taxe foncière",
                "description": "Justificatif de paiement des taxes",
                "required": False
            },
            {
                "id": "cadastral_map",
                "name": "Plan cadastral",
                "description": "Carte cadastrale officielle",
                "required": False
            },
            {
                "id": "building_permit",
                "name": "Permis de construire",
                "description": "Autorisation de construction",
                "required": False
            },
            {
                "id": "other",
                "name": "Autre document",
                "description": "Tout autre document pertinent",
                "required": False
            }
        ]
    }

async def register_document_on_blockchain(
    document_id: str, 
    ipfs_hash: str, 
    file_hash: str
):
    """Enregistrement d'un document sur la blockchain"""
    try:
        # Enregistrement sur la blockchain
        tx_hash = await blockchain_service.register_document(
            document_id=document_id,
            ipfs_hash=ipfs_hash,
            file_hash=file_hash
        )
        
        logger.info(f"Document {document_id} enregistré sur blockchain: {tx_hash}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement blockchain du document {document_id}: {str(e)}")

@router.post("/bulk-verify")
async def bulk_verify_documents(
    document_ids: List[str],
    verification_status: str,
    comment: Optional[str] = None,
    db=Depends(get_database),
    current_user=Depends(verify_token)
):
    """Vérification en lot de documents"""
    try:
        if not current_user.get("is_verifier"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions de vérification requises"
            )
        
        results = []
        for doc_id in document_ids:
            try:
                verification = await document_service.update_verification_status(
                    document_id=doc_id,
                    status=verification_status,
                    comment=comment,
                    verifier_id=current_user["user_id"],
                    db=db
                )
                results.append({
                    "document_id": doc_id,
                    "status": "success",
                    "verification": verification
                })
            except Exception as e:
                results.append({
                    "document_id": doc_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification en lot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )
