"""
Service de gestion de la blockchain CELO
Interaction avec le smart contract du registre foncier
"""

from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import asyncio
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)

class CeloBlockchainService:
    """
    Service pour interagir avec la blockchain CELO
    """
    
    def __init__(self):
        self.w3 = None
        self.contract = None
        self.account = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialise la connexion à CELO"""
        try:
            # Configuration de Web3 pour CELO
            self.w3 = Web3(Web3.HTTPProvider(settings.CELO_RPC_URL))
            
            # Ajout du middleware POA pour CELO
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Vérification de la connexion
            if not self.w3.is_connected():
                raise ConnectionError("Impossible de se connecter au réseau CELO")
            
            logger.info(f"✅ Connexion CELO établie - Réseau: {settings.CELO_NETWORK}")
            logger.info(f"🔗 Block number: {self.w3.eth.block_number}")
            
            # Configuration du compte si clé privée fournie
            if settings.PRIVATE_KEY:
                self.account = self.w3.eth.account.from_key(settings.PRIVATE_KEY)
                logger.info(f"👤 Compte configuré: {self.account.address}")
            
            # Chargement du contrat si adresse fournie
            if settings.CONTRACT_ADDRESS:
                self._load_contract()
                
        except Exception as e:
            logger.error(f"❌ Erreur initialisation blockchain: {e}")
            raise
    
    def _load_contract(self):
        """Charge le smart contract du registre foncier"""
        try:
            # Chargement de l'ABI depuis le fichier de déploiement
            import os
            from pathlib import Path
            
            deployment_file = Path(__file__).parent.parent.parent / "blockchain" / "deployments" / f"{settings.CELO_NETWORK}.json"
            
            if deployment_file.exists():
                with open(deployment_file, 'r') as f:
                    deployment_data = json.load(f)
                    abi = deployment_data['abi']
            else:
                # ABI de base si fichier non trouvé
                abi = self._get_basic_abi()
            
            self.contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(settings.CONTRACT_ADDRESS),
                abi=abi
            )
            
            logger.info(f"📋 Smart contract chargé: {settings.CONTRACT_ADDRESS}")
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement contrat: {e}")
            raise
    
    def _get_basic_abi(self) -> List[Dict]:
        """ABI de base pour le contrat LandRegistry"""
        return [
            {
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "location", "type": "string"},
                    {"name": "coordinates", "type": "string"},
                    {"name": "area", "type": "uint256"},
                    {"name": "value", "type": "uint256"},
                    {"name": "propertyType", "type": "uint8"},
                    {"name": "documentHash", "type": "string"},
                    {"name": "tokenURI", "type": "string"}
                ],
                "name": "registerProperty",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "inputs": [{"name": "propertyId", "type": "uint256"}],
                "name": "getProperty",
                "outputs": [
                    {
                        "components": [
                            {"name": "id", "type": "uint256"},
                            {"name": "location", "type": "string"},
                            {"name": "coordinates", "type": "string"},
                            {"name": "area", "type": "uint256"},
                            {"name": "value", "type": "uint256"},
                            {"name": "propertyType", "type": "uint8"},
                            {"name": "status", "type": "uint8"},
                            {"name": "registrationDate", "type": "uint256"},
                            {"name": "lastTransferDate", "type": "uint256"},
                            {"name": "documentHash", "type": "string"},
                            {"name": "registrar", "type": "address"},
                            {"name": "verified", "type": "bool"}
                        ],
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getTotalProperties",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
    
    async def register_property(
        self,
        owner_address: str,
        location: str,
        coordinates: str,
        area: int,
        value: int,
        property_type: int,
        document_hash: str,
        token_uri: str
    ) -> Dict[str, Any]:
        """
        Enregistre une propriété sur la blockchain
        """
        if not self.contract or not self.account:
            raise ValueError("Contrat ou compte non configuré")
        
        try:
            # Préparation de la transaction
            function = self.contract.functions.registerProperty(
                self.w3.to_checksum_address(owner_address),
                location,
                coordinates,
                area,
                value,
                property_type,
                document_hash,
                token_uri
            )
            
            # Estimation du gas
            gas_estimate = await asyncio.to_thread(
                function.estimate_gas,
                {'from': self.account.address}
            )
            
            # Construction de la transaction
            tx = await asyncio.to_thread(
                function.build_transaction,
                {
                    'from': self.account.address,
                    'gas': int(gas_estimate * 1.2),  # Marge de sécurité
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address)
                }
            )
            
            # Signature et envoi
            signed_tx = self.w3.eth.account.sign_transaction(tx, settings.PRIVATE_KEY)
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction,
                signed_tx.rawTransaction
            )
            
            # Attente de la confirmation
            receipt = await self._wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Extraction de l'ID de propriété depuis les logs
                property_id = self._extract_property_id_from_receipt(receipt)
                
                logger.info(f"✅ Propriété enregistrée - ID: {property_id}, TX: {tx_hash.hex()}")
                
                return {
                    "success": True,
                    "property_id": property_id,
                    "transaction_hash": tx_hash.hex(),
                    "block_number": receipt.blockNumber,
                    "gas_used": receipt.gasUsed
                }
            else:
                raise Exception("Transaction échouée")
                
        except Exception as e:
            logger.error(f"❌ Erreur enregistrement propriété: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_property(self, property_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'une propriété depuis la blockchain
        """
        if not self.contract:
            raise ValueError("Contrat non configuré")
        
        try:
            property_data = await asyncio.to_thread(
                self.contract.functions.getProperty(property_id).call
            )
            
            return {
                "id": property_data[0],
                "location": property_data[1],
                "coordinates": property_data[2],
                "area": property_data[3],
                "value": property_data[4],
                "property_type": property_data[5],
                "status": property_data[6],
                "registration_date": datetime.fromtimestamp(property_data[7]) if property_data[7] > 0 else None,
                "last_transfer_date": datetime.fromtimestamp(property_data[8]) if property_data[8] > 0 else None,
                "document_hash": property_data[9],
                "registrar": property_data[10],
                "verified": property_data[11]
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération propriété {property_id}: {e}")
            return None
    
    async def get_total_properties(self) -> int:
        """
        Récupère le nombre total de propriétés enregistrées
        """
        if not self.contract:
            return 0
        
        try:
            total = await asyncio.to_thread(
                self.contract.functions.getTotalProperties().call
            )
            return total
        except Exception as e:
            logger.error(f"❌ Erreur récupération total: {e}")
            return 0
    
    async def get_properties_by_owner(self, owner_address: str) -> List[int]:
        """
        Récupère les IDs des propriétés d'un propriétaire
        """
        if not self.contract:
            return []
        
        try:
            properties = await asyncio.to_thread(
                self.contract.functions.getPropertiesByOwner(
                    self.w3.to_checksum_address(owner_address)
                ).call
            )
            return list(properties)
        except Exception as e:
            logger.error(f"❌ Erreur récupération propriétés owner {owner_address}: {e}")
            return []
    
    async def listen_to_events(self, callback):
        """
        Écoute les événements du contrat en temps réel
        """
        if not self.contract:
            logger.warning("Contrat non configuré pour l'écoute d'événements")
            return
        
        try:
            # Filtre pour tous les événements
            event_filter = self.contract.events.PropertyRegistered.create_filter(
                fromBlock='latest'
            )
            
            while True:
                for event in event_filter.get_new_entries():
                    await callback(event)
                await asyncio.sleep(2)  # Polling toutes les 2 secondes
                
        except Exception as e:
            logger.error(f"❌ Erreur écoute événements: {e}")
    
    async def _wait_for_transaction_receipt(self, tx_hash, timeout=120):
        """Attend la confirmation d'une transaction"""
        return await asyncio.to_thread(
            self.w3.eth.wait_for_transaction_receipt,
            tx_hash,
            timeout=timeout
        )
    
    def _extract_property_id_from_receipt(self, receipt) -> Optional[int]:
        """Extrait l'ID de propriété depuis le receipt"""
        try:
            for log in receipt.logs:
                if len(log.topics) > 0:
                    # Recherche de l'événement PropertyRegistered
                    decoded = self.contract.events.PropertyRegistered().process_log(log)
                    return decoded['args']['propertyId']
        except Exception as e:
            logger.warning(f"Impossible d'extraire l'ID de propriété: {e}")
        return None
    
    def get_network_info(self) -> Dict[str, Any]:
        """Retourne les informations du réseau"""
        if not self.w3:
            return {}
        
        try:
            return {
                "network": settings.CELO_NETWORK,
                "connected": self.w3.is_connected(),
                "block_number": self.w3.eth.block_number,
                "gas_price": self.w3.eth.gas_price,
                "account": self.account.address if self.account else None,
                "contract_address": settings.CONTRACT_ADDRESS
            }
        except Exception as e:
            logger.error(f"❌ Erreur info réseau: {e}")
            return {"error": str(e)}

# Instance globale du service blockchain
blockchain_service = CeloBlockchainService()
