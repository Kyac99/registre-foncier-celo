"""
Modèle pour les documents et fichiers IPFS
"""

from sqlalchemy import Column, String, BigInteger, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base
import uuid as uuid_pkg
from enum import Enum

class DocumentType(str, Enum):
    """Types de documents"""
    TITLE_DEED = "TITLE_DEED"           # Titre de propriété
    SURVEY_REPORT = "SURVEY_REPORT"     # Rapport d'arpentage
    VALUATION = "VALUATION"             # Évaluation
    LEGAL_DOCUMENT = "LEGAL_DOCUMENT"   # Document juridique
    PHOTO = "PHOTO"                     # Photo de la propriété
    MAP = "MAP"                         # Plan/carte
    CONTRACT = "CONTRACT"               # Contrat de vente
    OTHER = "OTHER"                     # Autre

class Document(Base):
    """Modèle pour les documents liés aux propriétés"""
    
    __tablename__ = "documents"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    
    # Références
    property_id = Column(BigInteger, ForeignKey("properties.id"), nullable=False, index=True)
    uploader_address = Column(String(42), ForeignKey("users.wallet_address"), nullable=True)
    
    # Informations du document
    document_type = Column(String(50), nullable=False, default=DocumentType.OTHER)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=True)  # Nom original du fichier
    file_size = Column(BigInteger, nullable=True)       # Taille en bytes
    mime_type = Column(String(100), nullable=True)      # Type MIME
    
    # Stockage IPFS
    ipfs_hash = Column(String(100), unique=True, nullable=False, index=True)
    ipfs_url = Column(Text, nullable=True)              # URL complète IPFS
    pin_status = Column(String(20), default="pinned")   # Statut du pin IPFS
    
    # Sécurité et accès
    encryption_key = Column(String(100), nullable=True) # Clé de chiffrement si document privé
    is_public = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Vérifié par autorité
    
    # Métadonnées
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)                  # Tags séparés par des virgules
    
    # Dates
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    property = relationship("Property", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
    
    def __repr__(self):
        return f"<Document {self.file_name} - {self.document_type}>"
    
    @property
    def size_formatted(self):
        """Taille formatée du fichier"""
        if not self.file_size:
            return "Inconnue"
        
        size = self.file_size
        units = ['B', 'KB', 'MB', 'GB']
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    @property
    def type_display(self):
        """Type de document affiché en français"""
        type_map = {
            DocumentType.TITLE_DEED: "Titre de propriété",
            DocumentType.SURVEY_REPORT: "Rapport d'arpentage",
            DocumentType.VALUATION: "Évaluation",
            DocumentType.LEGAL_DOCUMENT: "Document juridique",
            DocumentType.PHOTO: "Photo",
            DocumentType.MAP: "Plan/Carte",
            DocumentType.CONTRACT: "Contrat",
            DocumentType.OTHER: "Autre"
        }
        return type_map.get(self.document_type, self.document_type)
    
    @property
    def file_extension(self):
        """Extension du fichier"""
        if '.' in self.file_name:
            return self.file_name.split('.')[-1].lower()
        return ""
    
    @property
    def is_image(self):
        """Vérifie si le document est une image"""
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return self.file_extension in image_extensions
    
    @property
    def is_pdf(self):
        """Vérifie si le document est un PDF"""
        return self.file_extension == 'pdf'
    
    @property
    def gateway_url(self):
        """URL de la gateway IPFS"""
        from config.settings import settings
        if self.ipfs_hash:
            return f"{settings.IPFS_GATEWAY}/ipfs/{self.ipfs_hash}"
        return None
    
    @property
    def tags_list(self):
        """Liste des tags"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def add_tag(self, tag: str):
        """Ajoute un tag"""
        current_tags = self.tags_list
        if tag not in current_tags:
            current_tags.append(tag)
            self.tags = ', '.join(current_tags)
    
    def remove_tag(self, tag: str):
        """Supprime un tag"""
        current_tags = self.tags_list
        if tag in current_tags:
            current_tags.remove(tag)
            self.tags = ', '.join(current_tags)
    
    def to_dict(self, include_sensitive=False):
        """Convertit le modèle en dictionnaire"""
        data = {
            "id": str(self.id),
            "property_id": self.property_id,
            "document_type": self.document_type,
            "type_display": self.type_display,
            "file_name": self.file_name,
            "original_name": self.original_name,
            "file_size": self.file_size,
            "size_formatted": self.size_formatted,
            "mime_type": self.mime_type,
            "ipfs_hash": self.ipfs_hash,
            "gateway_url": self.gateway_url,
            "is_public": self.is_public,
            "is_verified": self.is_verified,
            "is_image": self.is_image,
            "is_pdf": self.is_pdf,
            "file_extension": self.file_extension,
            "description": self.description,
            "tags": self.tags_list,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None
        }
        
        if include_sensitive:
            data.update({
                "uploader_address": self.uploader_address,
                "encryption_key": self.encryption_key,
                "pin_status": self.pin_status,
                "ipfs_url": self.ipfs_url,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            })
        
        return data

class DocumentAccess(Base):
    """Modèle pour gérer l'accès aux documents privés"""
    
    __tablename__ = "document_access"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    
    # Références
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    user_address = Column(String(42), ForeignKey("users.wallet_address"), nullable=False)
    granted_by = Column(String(42), ForeignKey("users.wallet_address"), nullable=True)
    
    # Permissions
    can_view = Column(Boolean, default=True, nullable=False)
    can_download = Column(Boolean, default=False, nullable=False)
    can_share = Column(Boolean, default=False, nullable=False)
    
    # Période d'accès
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(String(42), nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    document = relationship("Document")
    user = relationship("User", foreign_keys=[user_address])
    grantor = relationship("User", foreign_keys=[granted_by])
    
    def __repr__(self):
        return f"<DocumentAccess {self.user_address[:10]}... -> Document {self.document_id}>"
    
    @property
    def is_valid(self):
        """Vérifie si l'accès est toujours valide"""
        from datetime import datetime
        now = datetime.utcnow()
        
        if not self.is_active:
            return False
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        return True
    
    def revoke_access(self, revoked_by_address: str):
        """Révoque l'accès"""
        self.is_active = False
        self.revoked_at = func.now()
        self.revoked_by = revoked_by_address
    
    def to_dict(self):
        """Convertit le modèle en dictionnaire"""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "user_address": self.user_address,
            "granted_by": self.granted_by,
            "can_view": self.can_view,
            "can_download": self.can_download,
            "can_share": self.can_share,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "is_active": self.is_active,
            "is_valid": self.is_valid,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_by": self.revoked_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
