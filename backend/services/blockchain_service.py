"""
Service pour les interactions avec la blockchain CELO
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import json
import time
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)

class BlockchainService:
    def __init__(self):
        self.w3: Optional[Web3] = None
        self.contract = None
        self.contract_abi = None
        self.contract_address = settings.CONTRACT_ADDRESS
        self.private_key = settings.PRIVATE_KEY
        self.account = None
        
        if self.private_key:
            self.account = Account.from_key(self.private_key)
        
    async def initialize(self):
        """Initialisation de la connexion à la blockchain"""
        try:
            # Configuration Web3
            self.w3 = Web3(Web3.HTTPProvider(settings.CELO_RPC_URL))
            
            # Middleware pour CELO (réseau PoA)
            if settings.CELO_NETWORK in ['alfajores', 'celo']:
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Vérification de la connexion
            if not await self._is_connected():
                raise Exception("Impossible de se connecter au réseau CELO")
            
            # Chargement du contrat
            await self._load_contract()
            
            logger.info(f"Service blockchain initialisé sur {settings.CELO_NETWORK}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur d'initialisation blockchain: {str(e)}")
            return False
    
    async def _is_connected(self) -> bool:
        """Vérification de la connexion"""
        try:
            if not self.w3:
                return False
            return await asyncio.get_event_loop().run_in_executor(
                None, self.w3.isConnected
            )
        except Exception:
            return False
    
    async def _load_contract(self):
        """Chargement du contrat intelligent"""
        try:
            # Charger l'ABI depuis le fichier de build
            with open(f"blockchain/artifacts/contracts/LandRegistry.sol/LandRegistry.json", 'r') as f:
                contract_json = json.load(f)
                self.contract_abi = contract_json['abi']
            
            # Créer l'instance du contrat
            if self.contract_address and self.contract_abi:
                self.contract = self.w3.eth.contract(
                    address=Web3.toChecksumAddress(self.contract_address),
                    abi=self.contract_abi
                )
                logger.info(f"Contrat chargé à l'adresse {self.contract_address}")
            else:
                logger.warning("Adresse de contrat ou ABI manquante")
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement du contrat: {str(e)}")
            raise
    
    async def get_latest_block(self) -> int:
        """Récupération du dernier bloc"""
        try:
            if not self.w3:
                await self.initialize()
            
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.blockNumber
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du bloc: {str(e)}")
            raise
    
    async def get_gas_price(self) -> float:
        """Prix du gas actuel"""
        try:
            if not self.w3:
                await self.initialize()
            
            gas_price_wei = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.gasPrice
            )
            
            # Conversion en CELO
            return float(self.w3.fromWei(gas_price_wei, 'ether'))
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix du gas: {str(e)}")
            return 0.0
    
    async def get_contract_info(self) -> Dict[str, Any]:
        """Informations sur le contrat"""
        try:
            if not self.contract:
                await self.initialize()
            
            # Vérification que le contrat est déployé
            code = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.getCode(self.contract_address)
            )
            
            deployed = len(code) > 2  # Plus que '0x'
            
            info = {
                "deployed": deployed,
                "address": self.contract_address,
                "network": settings.CELO_NETWORK,
                "abi_loaded": self.contract_abi is not None
            }
            
            if deployed and self.contract:
                try:
                    # Appeler une fonction read-only pour tester
                    owner = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.contract.functions.owner().call()
                    )
                    info["owner"] = owner
                    info["functional"] = True
                except Exception:
                    info["functional"] = False
            
            return info
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos contrat: {str(e)}")
            return {"deployed": False, "error": str(e)}
    
    async def register_property(
        self, 
        property_id: str, 
        owner_address: str, 
        metadata_hash: str,
        coordinates: Optional[tuple] = None,
        area: Optional[float] = None
    ) -> str:
        """Enregistrement d'une propriété sur la blockchain"""
        try:
            if not self.contract or not self.account:
                await self.initialize()
                if not self.contract:
                    raise Exception("Contrat non disponible")
            
            # Préparation des paramètres
            lat = int(coordinates[0] * 1000000) if coordinates else 0
            lng = int(coordinates[1] * 1000000) if coordinates else 0
            area_int = int(area * 100) if area else 0  # Stockage en cm²
            
            # Construction de la transaction
            function_call = self.contract.functions.registerProperty(
                property_id,
                Web3.toChecksumAddress(owner_address),
                metadata_hash,
                lat,
                lng,
                area_int
            )
            
            # Estimation du gas
            gas_estimate = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.estimateGas({'from': self.account.address})
            )
            
            # Préparation de la transaction
            transaction = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.buildTransaction({
                    'from': self.account.address,
                    'gas': int(gas_estimate * 1.2),  # Marge de sécurité
                    'gasPrice': self.w3.eth.gasPrice,
                    'nonce': self.w3.eth.getTransactionCount(self.account.address)
                })
            )
            
            # Signature et envoi
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            tx_hash = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
            )
            
            logger.info(f"Propriété {property_id} enregistrée, tx: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de propriété: {str(e)}")
            raise
    
    async def get_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Récupération d'une propriété depuis la blockchain"""
        try:
            if not self.contract:
                await self.initialize()
            
            # Appel de la fonction du contrat
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.contract.functions.getProperty(property_id).call()
            )
            
            if not result[0]:  # exists
                return None
            
            return {
                "exists": result[0],
                "owner": result[1],
                "metadata_hash": result[2],
                "timestamp": datetime.fromtimestamp(result[3]),
                "verified": result[4],
                "verifier": result[5] if result[5] != "0x0000000000000000000000000000000000000000" else None,
                "latitude": result[6] / 1000000.0 if result[6] != 0 else None,
                "longitude": result[7] / 1000000.0 if result[7] != 0 else None,
                "area": result[8] / 100.0 if result[8] != 0 else None
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de propriété: {str(e)}")
            return None
    
    async def verify_property(self, property_id: str, verifier_address: str) -> str:
        """Vérification d'une propriété par une autorité"""
        try:
            if not self.contract or not self.account:
                await self.initialize()
            
            # Vérification des permissions
            is_verifier = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.contract.functions.isAuthorizedVerifier(
                    Web3.toChecksumAddress(verifier_address)
                ).call()
            )
            
            if not is_verifier:
                raise Exception("Adresse non autorisée pour la vérification")
            
            # Construction de la transaction
            function_call = self.contract.functions.verifyProperty(property_id)
            
            gas_estimate = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.estimateGas({'from': self.account.address})
            )
            
            transaction = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.buildTransaction({
                    'from': self.account.address,
                    'gas': int(gas_estimate * 1.2),
                    'gasPrice': self.w3.eth.gasPrice,
                    'nonce': self.w3.eth.getTransactionCount(self.account.address)
                })
            )
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            tx_hash = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
            )
            
            logger.info(f"Propriété {property_id} vérifiée, tx: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification: {str(e)}")
            raise
    
    async def transfer_property(
        self, 
        property_id: str, 
        from_address: str, 
        to_address: str
    ) -> str:
        """Transfert de propriété"""
        try:
            if not self.contract or not self.account:
                await self.initialize()
            
            # Vérification de la propriété
            current_owner = await self.get_property_owner(property_id)
            if current_owner.lower() != from_address.lower():
                raise Exception("Seul le propriétaire peut transférer la propriété")
            
            # Construction de la transaction
            function_call = self.contract.functions.transferProperty(
                property_id,
                Web3.toChecksumAddress(to_address)
            )
            
            gas_estimate = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.estimateGas({'from': self.account.address})
            )
            
            transaction = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.buildTransaction({
                    'from': self.account.address,
                    'gas': int(gas_estimate * 1.2),
                    'gasPrice': self.w3.eth.gasPrice,
                    'nonce': self.w3.eth.getTransactionCount(self.account.address)
                })
            )
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            tx_hash = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
            )
            
            logger.info(f"Propriété {property_id} transférée, tx: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Erreur lors du transfert: {str(e)}")
            raise
    
    async def get_property_owner(self, property_id: str) -> str:
        """Récupération du propriétaire actuel"""
        try:
            property_data = await self.get_property(property_id)
            if not property_data:
                raise Exception("Propriété non trouvée")
            return property_data["owner"]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du propriétaire: {str(e)}")
            raise
    
    async def get_transaction_status(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Statut d'une transaction"""
        try:
            if not self.w3:
                await self.initialize()
            
            # Récupération de la transaction
            tx = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.getTransaction(tx_hash)
            )
            
            if not tx:
                return None
            
            # Récupération du reçu
            try:
                receipt = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.w3.eth.getTransactionReceipt(tx_hash)
                )
                
                current_block = await self.get_latest_block()
                confirmations = current_block - receipt.blockNumber
                
                return {
                    "status": "confirmed" if receipt.status == 1 else "failed",
                    "block_number": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "confirmations": confirmations,
                    "transaction_hash": tx_hash
                }
                
            except Exception:
                # Transaction en attente
                return {
                    "status": "pending",
                    "block_number": None,
                    "gas_used": None,
                    "confirmations": 0,
                    "transaction_hash": tx_hash
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
            return None
    
    async def get_properties_by_owner(self, owner_address: str) -> List[Dict[str, Any]]:
        """Liste des propriétés d'un propriétaire"""
        try:
            if not self.contract:
                await self.initialize()
            
            # Récupération des événements PropertyRegistered
            events = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.contract.events.PropertyRegistered.createFilter(
                    fromBlock=0,
                    argument_filters={'owner': Web3.toChecksumAddress(owner_address)}
                ).get_all_entries()
            )
            
            properties = []
            for event in events:
                property_id = event.args.propertyId
                property_data = await self.get_property(property_id)
                if property_data:
                    property_data["property_id"] = property_id
                    properties.append(property_data)
            
            return properties
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des propriétés: {str(e)}")
            return []
    
    async def is_authorized_verifier(self, address: str) -> bool:
        """Vérification si une adresse est autorisée à vérifier"""
        try:
            if not self.contract:
                await self.initialize()
            
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.contract.functions.isAuthorizedVerifier(
                    Web3.toChecksumAddress(address)
                ).call()
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des permissions: {str(e)}")
            return False
    
    async def register_document(
        self, 
        document_id: str, 
        ipfs_hash: str, 
        file_hash: str
    ) -> str:
        """Enregistrement d'un document sur la blockchain"""
        try:
            if not self.contract or not self.account:
                await self.initialize()
            
            # Construction de la transaction (fonction hypothétique)
            function_call = self.contract.functions.registerDocument(
                document_id,
                ipfs_hash,
                file_hash
            )
            
            gas_estimate = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.estimateGas({'from': self.account.address})
            )
            
            transaction = await asyncio.get_event_loop().run_in_executor(
                None, lambda: function_call.buildTransaction({
                    'from': self.account.address,
                    'gas': int(gas_estimate * 1.2),
                    'gasPrice': self.w3.eth.gasPrice,
                    'nonce': self.w3.eth.getTransactionCount(self.account.address)
                })
            )
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            tx_hash = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
            )
            
            logger.info(f"Document {document_id} enregistré, tx: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du document: {str(e)}")
            raise
    
    async def sync_all_properties(self):
        """Synchronisation de toutes les propriétés depuis la blockchain"""
        try:
            logger.info("Démarrage de la synchronisation blockchain")
            
            if not self.contract:
                await self.initialize()
            
            # Récupération de tous les événements PropertyRegistered
            events = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.contract.events.PropertyRegistered.createFilter(
                    fromBlock=0
                ).get_all_entries()
            )
            
            logger.info(f"Synchronisation de {len(events)} propriétés")
            
            # TODO: Mettre à jour la base de données avec les données blockchain
            # Ceci nécessiterait une connexion à la base de données
            
            logger.info("Synchronisation blockchain terminée")
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {str(e)}")
            raise