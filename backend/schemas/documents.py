"""
Schémas Pydantic pour la gestion des documents
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    TITLE_DEED = "title_deed"
    SURVEY_PLAN = "survey_plan"
    TAX_RECEIPT = "tax_receipt"
    CADASTRAL_MAP = "cadastral_map"
    BUILDING_PERMIT = "building_permit"
    OTHER = "other"

class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"

class DocumentUpload(BaseModel):
    property_id: str = Field(..., description="ID de la propriété")
    document_type: DocumentType = Field(..., description="Type de document")
    title: str = Field(..., min_length=3, max_length=200, description="Titre du document")
    description: Optional[str] = Field(None, max_length=1000, description="Description du document")
    is_public: bool = Field(False, description="Document public")

class DocumentMetadata(BaseModel):
    filename: str = Field(..., description="Nom du fichier")
    mime_type: str = Field(..., description="Type MIME")
    size: int = Field(..., ge=0, description="Taille en octets")
    hash_sha256: str = Field(..., description="Hash SHA256 du fichier")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    uploader_id: str = Field(..., description="ID de l'utilisateur")

class DocumentResponse(BaseModel):
    document_id: str = Field(..., description="ID unique du document")
    property_id: str = Field(..., description="ID de la propriété")
    title: str = Field(..., description="Titre du document")
    document_type: DocumentType = Field(..., description="Type de document")
    ipfs_hash: str = Field(..., description="Hash IPFS")
    filename: str = Field(..., description="Nom du fichier")
    size: int = Field(..., description="Taille du fichier")
    mime_type: str = Field(..., description="Type MIME")
    upload_timestamp: datetime = Field(..., description="Date d'upload")
    is_public: bool = Field(..., description="Document public")
    verification_status: VerificationStatus = Field(..., description="Statut de vérification")
    uploader_name: str = Field(..., description="Nom de l'uploadeur")
    description: Optional[str] = None

class DocumentVerification(BaseModel):
    document_id: str = Field(..., description="ID du document")
    verification_status: VerificationStatus = Field(..., description="Statut de vérification")
    verifier_id: str = Field(..., description="ID du vérificateur")
    verifier_name: str = Field(..., description="Nom du vérificateur")
    verification_date: datetime = Field(default_factory=datetime.utcnow)
    comment: Optional[str] = Field(None, max_length=500, description="Commentaire de vérification")

class DocumentList(BaseModel):
    documents: List[DocumentResponse] = Field(..., description="Liste des documents")
    total_count: int = Field(..., ge=0, description="Nombre total de documents")
    skip: int = Field(..., ge=0, description="Éléments ignorés")
    limit: int = Field(..., ge=1, description="Limite par page")

class DocumentTypeInfo(BaseModel):
    id: str = Field(..., description="ID du type")
    name: str = Field(..., description="Nom du type")
    description: str = Field(..., description="Description")
    required: bool = Field(..., description="Document requis")
    allowed_mime_types: List[str] = Field(..., description="Types MIME autorisés")

class DocumentStats(BaseModel):
    total_documents: int = Field(..., description="Total des documents")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Répartition par type")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Répartition par statut")
    total_size_mb: float = Field(..., description="Taille totale en MB")
    verification_rate: float = Field(..., description="Taux de vérification")

class BulkUploadResult(BaseModel):
    successful_uploads: List[DocumentResponse] = Field(default_factory=list)
    failed_uploads: List[Dict[str, str]] = Field(default_factory=list)
    total_processed: int = Field(..., description="Total traité")
    success_count: int = Field(..., description="Nombre de succès")
    error_count: int = Field(..., description="Nombre d'erreurs")

class DocumentAccess(BaseModel):
    document_id: str = Field(..., description="ID du document")
    user_id: str = Field(..., description="ID de l'utilisateur")
    access_type: str = Field(..., description="Type d'accès (read, write, admin)")
    granted_by: str = Field(..., description="Accordé par")
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Date d'expiration")

class DocumentHistory(BaseModel):
    document_id: str = Field(..., description="ID du document")
    action: str = Field(..., description="Action effectuée")
    user_id: str = Field(..., description="ID de l'utilisateur")
    user_name: str = Field(..., description="Nom de l'utilisateur")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ip_address: Optional[str] = Field(None, description="Adresse IP")
