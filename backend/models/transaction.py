"""
Modèles pour les transactions et événements blockchain
"""

from sqlalchemy import Column, String, BigInteger, Numeric, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base
import uuid as uuid_pkg
from enum import Enum

class TransactionType(str, Enum):
    """Types de transactions"""
    REGISTRATION = "REGISTRATION"
    TRANSFER = "TRANSFER"
    VERIFICATION = "VERIFICATION"
    STATUS_CHANGE = "STATUS_CHANGE"
    VALUE_UPDATE = "VALUE_UPDATE"

class PropertyTransaction(Base):
    """Modèle pour l'historique des transactions de propriétés"""
    
    __tablename__ = "property_transactions"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    
    # Références
    property_id = Column(BigInteger, ForeignKey("properties.id"), nullable=False, index=True)
    user_address = Column(String(42), ForeignKey("users.wallet_address"), nullable=True)
    
    # Informations blockchain
    transaction_hash = Column(String(66), unique=True, nullable=False, index=True)
    block_number = Column(BigInteger, nullable=True, index=True)
    
    # Détails de la transaction
    from_address = Column(String(42), nullable=True)
    to_address = Column(String(42), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    value = Column(Numeric(20, 2), nullable=True)  # Valeur en cUSD
    
    # Coûts de transaction
    gas_used = Column(BigInteger, nullable=True)
    gas_price = Column(Numeric(20, 2), nullable=True)
    transaction_fee = Column(Numeric(20, 2), nullable=True)
    
    # Dates
    transaction_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    property = relationship("Property", back_populates="transactions")
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction {self.transaction_hash[:10]}... - {self.transaction_type}>"
    
    @property
    def fee_formatted(self):
        """Frais de transaction formatés"""
        if self.transaction_fee:
            return f"{float(self.transaction_fee):.6f} CELO"
        return "N/A"
    
    @property
    def value_formatted(self):
        """Valeur formatée"""
        if self.value:
            return f"{float(self.value):,.2f} cUSD"
        return "N/A"
    
    def to_dict(self):
        """Convertit le modèle en dictionnaire"""
        return {
            "id": str(self.id),
            "property_id": self.property_id,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "transaction_type": self.transaction_type,
            "value": float(self.value) if self.value else None,
            "value_formatted": self.value_formatted,
            "gas_used": self.gas_used,
            "gas_price": float(self.gas_price) if self.gas_price else None,
            "transaction_fee": float(self.transaction_fee) if self.transaction_fee else None,
            "fee_formatted": self.fee_formatted,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class BlockchainEvent(Base):
    """Modèle pour les événements blockchain bruts"""
    
    __tablename__ = "blockchain_events"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    
    # Informations événement
    event_type = Column(String(50), nullable=False, index=True)
    contract_address = Column(String(42), nullable=False, index=True)
    transaction_hash = Column(String(66), nullable=False, index=True)
    block_number = Column(BigInteger, nullable=False, index=True)
    log_index = Column(BigInteger, nullable=True)
    
    # Données de l'événement (format JSON)
    event_data = Column(JSON, nullable=True)
    raw_log = Column(JSON, nullable=True)
    
    # Statut de traitement
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processing_error = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<BlockchainEvent {self.event_type} - Block {self.block_number}>"
    
    def mark_as_processed(self):
        """Marque l'événement comme traité"""
        self.processed = True
        self.processed_at = func.now()
        self.processing_error = None
    
    def mark_as_failed(self, error_message: str):
        """Marque l'événement comme échoué"""
        self.processed = False
        self.processing_error = error_message
        self.processed_at = func.now()
    
    def to_dict(self):
        """Convertit le modèle en dictionnaire"""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "contract_address": self.contract_address,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "log_index": self.log_index,
            "event_data": self.event_data,
            "processed": self.processed,
            "processing_error": self.processing_error,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class BlockchainSync(Base):
    """Modèle pour suivre la synchronisation avec la blockchain"""
    
    __tablename__ = "blockchain_sync"
    
    # Clé primaire
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    
    # Informations de synchronisation
    contract_address = Column(String(42), nullable=False, unique=True)
    last_processed_block = Column(BigInteger, nullable=False, default=0)
    last_sync_date = Column(DateTime(timezone=True), nullable=True)
    
    # Statistiques
    total_events_processed = Column(BigInteger, default=0)
    total_errors = Column(BigInteger, default=0)
    
    # Statut
    is_syncing = Column(Boolean, default=False)
    sync_error = Column(Text, nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<BlockchainSync {self.contract_address[:10]}... - Block {self.last_processed_block}>"
    
    def update_sync_status(self, block_number: int, success: bool = True, error: str = None):
        """Met à jour le statut de synchronisation"""
        if success:
            self.last_processed_block = max(self.last_processed_block, block_number)
            self.last_sync_date = func.now()
            self.total_events_processed += 1
            self.sync_error = None
        else:
            self.total_errors += 1
            self.sync_error = error
        
        self.updated_at = func.now()
    
    def to_dict(self):
        """Convertit le modèle en dictionnaire"""
        return {
            "id": str(self.id),
            "contract_address": self.contract_address,
            "last_processed_block": self.last_processed_block,
            "last_sync_date": self.last_sync_date.isoformat() if self.last_sync_date else None,
            "total_events_processed": self.total_events_processed,
            "total_errors": self.total_errors,
            "is_syncing": self.is_syncing,
            "sync_error": self.sync_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
