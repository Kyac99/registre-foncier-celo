"""
Router pour les interactions blockchain CELO
Gestion des transactions, vérifications et monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import asyncio
import logging
from web3 import Web3
from eth_account import Account

from config.database import get_database
from config.settings import settings
from services.blockchain_service import BlockchainService
from services.ipfs_service import IPFSService
from schemas.blockchain import (
    TransactionRequest, 
    TransactionResponse, 
    BlockchainStatus,
    ContractInteraction,
    PropertyOnChain
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Service blockchain global
blockchain_service = BlockchainService()
ipfs_service = IPFSService()

@router.get("/status", response_model=BlockchainStatus)
async def get_blockchain_status():
    """Statut de la blockchain CELO et du contrat"""
    try:
        # Vérification de la connexion au réseau CELO
        latest_block = await blockchain_service.get_latest_block()
        contract_address = settings.CONTRACT_ADDRESS
        
        # Vérification du contrat
        contract_info = await blockchain_service.get_contract_info()
        
        return BlockchainStatus(
            network=settings.CELO_NETWORK,
            connected=True,
            latest_block=latest_block,
            contract_address=contract_address,
            contract_deployed=contract_info["deployed"],
            gas_price=await blockchain_service.get_gas_price()
        )
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut blockchain: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de se connecter à la blockchain: {str(e)}"
        )

@router.post("/register-property", response_model=TransactionResponse)
async def register_property_on_blockchain(
    request: TransactionRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_database)
):
    """Enregistrement d'une propriété sur la blockchain"""
    try:
        # Validation des données
        if not request.property_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Données de propriété requises"
            )
        
        # Stockage des métadonnées sur IPFS
        metadata_hash = await ipfs_service.store_metadata(request.property_data)
        
        # Interaction avec le smart contract
        tx_hash = await blockchain_service.register_property(
            property_id=request.property_id,
            owner_address=request.owner_address,
            metadata_hash=metadata_hash,
            coordinates=request.property_data.get("coordinates"),
            area=request.property_data.get("area")
        )
        
        # Enregistrement de la transaction en base
        background_tasks.add_task(
            store_transaction_record,
            tx_hash,
            request.property_id,
            "property_registration",
            db
        )
        
        return TransactionResponse(
            transaction_hash=tx_hash,
            status="pending",
            block_number=None,
            gas_used=None,
            metadata_hash=metadata_hash
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement sur blockchain: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'enregistrement: {str(e)}"
        )

@router.get("/property/{property_id}", response_model=PropertyOnChain)
async def get_property_from_blockchain(property_id: str):
    """Récupération des informations d'une propriété depuis la blockchain"""
    try:
        # Récupération depuis le smart contract
        property_data = await blockchain_service.get_property(property_id)
        
        if not property_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Propriété non trouvée sur la blockchain"
            )
        
        # Récupération des métadonnées depuis IPFS
        metadata = await ipfs_service.get_metadata(property_data["metadata_hash"])
        
        return PropertyOnChain(
            property_id=property_id,
            owner_address=property_data["owner"],
            metadata_hash=property_data["metadata_hash"],
            registration_timestamp=property_data["timestamp"],
            verified=property_data["verified"],
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la propriété: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.post("/verify-property", response_model=TransactionResponse)
async def verify_property_on_blockchain(
    property_id: str,
    verifier_address: str,
    background_tasks: BackgroundTasks
):
    """Vérification d'une propriété par une autorité compétente"""
    try:
        # Vérification des permissions
        is_authorized = await blockchain_service.is_authorized_verifier(verifier_address)
        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Adresse non autorisée pour la vérification"
            )
        
        # Vérification sur la blockchain
        tx_hash = await blockchain_service.verify_property(
            property_id=property_id,
            verifier_address=verifier_address
        )
        
        return TransactionResponse(
            transaction_hash=tx_hash,
            status="pending",
            block_number=None,
            gas_used=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la vérification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )

@router.post("/transfer-property", response_model=TransactionResponse)
async def transfer_property_on_blockchain(request: ContractInteraction):
    """Transfert de propriété sur la blockchain"""
    try:
        # Vérification de la propriété du bien
        current_owner = await blockchain_service.get_property_owner(request.property_id)
        if current_owner.lower() != request.from_address.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul le propriétaire peut transférer la propriété"
            )
        
        # Exécution du transfert
        tx_hash = await blockchain_service.transfer_property(
            property_id=request.property_id,
            from_address=request.from_address,
            to_address=request.to_address
        )
        
        return TransactionResponse(
            transaction_hash=tx_hash,
            status="pending",
            block_number=None,
            gas_used=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du transfert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du transfert: {str(e)}"
        )

@router.get("/transaction/{tx_hash}", response_model=TransactionResponse)
async def get_transaction_status(tx_hash: str):
    """Statut d'une transaction sur la blockchain"""
    try:
        # Récupération du statut de la transaction
        tx_info = await blockchain_service.get_transaction_status(tx_hash)
        
        if not tx_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction non trouvée"
            )
        
        return TransactionResponse(
            transaction_hash=tx_hash,
            status=tx_info["status"],
            block_number=tx_info.get("block_number"),
            gas_used=tx_info.get("gas_used"),
            confirmation_count=tx_info.get("confirmations", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/properties/by-owner/{owner_address}")
async def get_properties_by_owner(owner_address: str) -> List[PropertyOnChain]:
    """Liste des propriétés appartenant à une adresse"""
    try:
        # Validation de l'adresse
        if not Web3.is_address(owner_address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adresse Ethereum invalide"
            )
        
        # Récupération depuis la blockchain
        properties = await blockchain_service.get_properties_by_owner(owner_address)
        
        # Enrichissement avec les métadonnées IPFS
        enriched_properties = []
        for prop in properties:
            try:
                metadata = await ipfs_service.get_metadata(prop["metadata_hash"])
                enriched_properties.append(PropertyOnChain(
                    property_id=prop["property_id"],
                    owner_address=prop["owner"],
                    metadata_hash=prop["metadata_hash"],
                    registration_timestamp=prop["timestamp"],
                    verified=prop["verified"],
                    metadata=metadata
                ))
            except Exception as e:
                logger.warning(f"Impossible de récupérer les métadonnées pour {prop['property_id']}: {str(e)}")
                # Ajout sans métadonnées en cas d'erreur IPFS
                enriched_properties.append(PropertyOnChain(
                    property_id=prop["property_id"],
                    owner_address=prop["owner"],
                    metadata_hash=prop["metadata_hash"],
                    registration_timestamp=prop["timestamp"],
                    verified=prop["verified"],
                    metadata={}
                ))
        
        return enriched_properties
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des propriétés: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

async def store_transaction_record(
    tx_hash: str, 
    property_id: str, 
    transaction_type: str, 
    db
):
    """Stockage des informations de transaction en base de données"""
    try:
        query = """
        INSERT INTO blockchain_transactions 
        (transaction_hash, property_id, transaction_type, status, created_at)
        VALUES ($1, $2, $3, 'pending', NOW())
        ON CONFLICT (transaction_hash) DO NOTHING
        """
        await db.execute(query, tx_hash, property_id, transaction_type)
        logger.info(f"Transaction {tx_hash} enregistrée en base")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la transaction: {str(e)}")

@router.post("/sync-from-blockchain")
async def sync_properties_from_blockchain(background_tasks: BackgroundTasks):
    """Synchronisation des propriétés depuis la blockchain vers la base de données"""
    try:
        background_tasks.add_task(blockchain_service.sync_all_properties)
        return {"message": "Synchronisation lancée en arrière-plan"}
    except Exception as e:
        logger.error(f"Erreur lors du lancement de la synchronisation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du lancement de la synchronisation"
        )
