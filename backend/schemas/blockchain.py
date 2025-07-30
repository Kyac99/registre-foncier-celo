"""
Schémas Pydantic pour les interactions blockchain
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

class TransactionRequest(BaseModel):
    property_id: str = Field(..., description="ID unique de la propriété")
    owner_address: str = Field(..., description="Adresse du propriétaire")
    property_data: Dict[str, Any] = Field(..., description="Données de la propriété")
    
    @validator("owner_address")
    def validate_ethereum_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Adresse Ethereum invalide")
        return v.lower()

class TransactionResponse(BaseModel):
    transaction_hash: str = Field(..., description="Hash de la transaction")
    status: TransactionStatus = Field(..., description="Statut de la transaction")
    block_number: Optional[int] = Field(None, description="Numéro de bloc")
    gas_used: Optional[int] = Field(None, description="Gas utilisé")
    confirmation_count: Optional[int] = Field(0, description="Nombre de confirmations")
    metadata_hash: Optional[str] = Field(None, description="Hash IPFS des métadonnées")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BlockchainStatus(BaseModel):
    network: str = Field(..., description="Réseau blockchain")
    connected: bool = Field(..., description="État de la connexion")
    latest_block: int = Field(..., description="Dernier bloc")
    contract_address: str = Field(..., description="Adresse du contrat")
    contract_deployed: bool = Field(..., description="Contrat déployé")
    gas_price: float = Field(..., description="Prix du gas actuel")

class ContractInteraction(BaseModel):
    property_id: str = Field(..., description="ID de la propriété")
    from_address: str = Field(..., description="Adresse expéditeur")
    to_address: str = Field(..., description="Adresse destinataire")
    
    @validator("from_address", "to_address")
    def validate_addresses(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Adresse Ethereum invalide")
        return v.lower()

class PropertyOnChain(BaseModel):
    property_id: str = Field(..., description="ID unique de la propriété")
    owner_address: str = Field(..., description="Adresse du propriétaire")
    metadata_hash: str = Field(..., description="Hash IPFS des métadonnées")
    registration_timestamp: datetime = Field(..., description="Date d'enregistrement")
    verified: bool = Field(False, description="Propriété vérifiée")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées")

class BlockchainEvent(BaseModel):
    event_type: str = Field(..., description="Type d'événement")
    property_id: str = Field(..., description="ID de la propriété")
    transaction_hash: str = Field(..., description="Hash de la transaction")
    block_number: int = Field(..., description="Numéro de bloc")
    timestamp: datetime = Field(..., description="Timestamp de l'événement")
    data: Dict[str, Any] = Field(default_factory=dict, description="Données de l'événement")

class GasEstimate(BaseModel):
    gas_limit: int = Field(..., description="Limite de gas estimée")
    gas_price: float = Field(..., description="Prix du gas")
    estimated_cost: float = Field(..., description="Coût estimé en CELO")
    
class NetworkInfo(BaseModel):
    name: str = Field(..., description="Nom du réseau")
    chain_id: int = Field(..., description="ID de la chaîne")
    rpc_url: str = Field(..., description="URL RPC")
    explorer_url: Optional[str] = Field(None, description="URL de l'explorateur")
    native_currency: Dict[str, str] = Field(..., description="Devise native")
