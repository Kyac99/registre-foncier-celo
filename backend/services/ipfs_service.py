"""
Service de gestion IPFS pour le stockage décentralisé des documents
Intégration avec Pinata et support du chiffrement
"""

import aiohttp
import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Optional, Any, BinaryIO
from pathlib import Path
import mimetypes
from cryptography.fernet import Fernet
import base64

from config.settings import settings

logger = logging.getLogger(__name__)

class IPFSService:
    """
    Service pour la gestion des fichiers IPFS
    Support Pinata et nœud IPFS local
    """
    
    def __init__(self):
        self.pinata_api_key = settings.PINATA_API_KEY
        self.pinata_secret = settings.PINATA_SECRET_KEY
        self.gateway_url = settings.IPFS_GATEWAY
        self.encryption_key = settings.ENCRYPTION_KEY.encode()[:32]  # Clé de 32 bytes pour Fernet
        self.fernet = Fernet(base64.urlsafe_b64encode(self.encryption_key))
        
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        metadata: Optional[Dict] = None,
        encrypt: bool = False
    ) -> Dict[str, Any]:
        """
        Upload un fichier vers IPFS via Pinata
        """
        try:
            # Chiffrement du contenu si demandé
            if encrypt:
                file_content = self.fernet.encrypt(file_content)
            
            # Calcul du hash du fichier
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Détection du type MIME
            mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            
            # Préparation des métadonnées
            pinata_metadata = {
                "name": filename,
                "keyvalues": {
                    "filename": filename,
                    "filesize": str(len(file_content)),
                    "mimetype": mime_type,
                    "filehash": file_hash,
                    "encrypted": str(encrypt).lower(),
                    "upload_date": str(asyncio.get_event_loop().time())
                }
            }
            
            if metadata:
                pinata_metadata["keyvalues"].update(metadata)
            
            # Upload vers Pinata
            ipfs_hash = await self._upload_to_pinata(file_content, filename, pinata_metadata)
            
            if ipfs_hash:
                logger.info(f"✅ Fichier uploadé sur IPFS: {filename} -> {ipfs_hash}")
                
                return {
                    "success": True,
                    "ipfs_hash": ipfs_hash,
                    "filename": filename,
                    "size": len(file_content),
                    "mime_type": mime_type,
                    "file_hash": file_hash,
                    "encrypted": encrypt,
                    "gateway_url": f"{self.gateway_url}/ipfs/{ipfs_hash}"
                }
            else:
                raise Exception("Échec de l'upload vers Pinata")
                
        except Exception as e:
            logger.error(f"❌ Erreur upload IPFS {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _upload_to_pinata(
        self,
        file_content: bytes,
        filename: str,
        metadata: Dict
    ) -> Optional[str]:
        """
        Upload direct vers l'API Pinata
        """
        if not self.pinata_api_key or not self.pinata_secret:
            raise ValueError("Clés API Pinata non configurées")
        
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        
        headers = {
            "pinata_api_key": self.pinata_api_key,
            "pinata_secret_api_key": self.pinata_secret
        }
        
        # Préparation du multipart/form-data
        data = aiohttp.FormData()
        data.add_field('file', file_content, filename=filename)
        data.add_field('pinataMetadata', json.dumps(metadata))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('IpfsHash')
                else:
                    error_text = await response.text()
                    raise Exception(f"Erreur Pinata API: {response.status} - {error_text}")
    
    async def download_file(
        self,
        ipfs_hash: str,
        decrypt: bool = False
    ) -> Dict[str, Any]:
        """
        Télécharge un fichier depuis IPFS
        """
        try:
            # Récupération du fichier
            file_content = await self._download_from_gateway(ipfs_hash)
            
            if not file_content:
                raise Exception("Fichier non trouvé sur IPFS")
            
            # Déchiffrement si nécessaire
            if decrypt:
                try:
                    file_content = self.fernet.decrypt(file_content)
                except Exception as e:
                    logger.warning(f"Échec déchiffrement {ipfs_hash}: {e}")
            
            # Récupération des métadonnées
            metadata = await self.get_file_metadata(ipfs_hash)
            
            return {
                "success": True,
                "content": file_content,
                "metadata": metadata,
                "size": len(file_content)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur téléchargement IPFS {ipfs_hash}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _download_from_gateway(self, ipfs_hash: str) -> Optional[bytes]:
        """
        Télécharge depuis la passerelle IPFS
        """
        url = f"{self.gateway_url}/ipfs/{ipfs_hash}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Erreur téléchargement gateway: {response.status}")
                    return None
    
    async def get_file_metadata(self, ipfs_hash: str) -> Dict[str, Any]:
        """
        Récupère les métadonnées d'un fichier depuis Pinata
        """
        if not self.pinata_api_key or not self.pinata_secret:
            return {}
        
        try:
            url = f"https://api.pinata.cloud/data/pinList?hashContains={ipfs_hash}"
            
            headers = {
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_api_key": self.pinata_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        rows = result.get('rows', [])
                        if rows:
                            pin_data = rows[0]
                            return {
                                "ipfs_hash": pin_data.get('ipfs_pin_hash'),
                                "size": pin_data.get('size'),
                                "timestamp": pin_data.get('date_pinned'),
                                "metadata": pin_data.get('metadata', {})
                            }
            
        except Exception as e:
            logger.warning(f"Erreur récupération métadonnées {ipfs_hash}: {e}")
        
        return {}
    
    async def pin_file(self, ipfs_hash: str, name: str = None) -> bool:
        """
        Épingle un fichier existant sur Pinata
        """
        if not self.pinata_api_key or not self.pinata_secret:
            return False
        
        try:
            url = "https://api.pinata.cloud/pinning/pinByHash"
            
            headers = {
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_api_key": self.pinata_secret,
                "Content-Type": "application/json"
            }
            
            data = {
                "hashToPin": ipfs_hash
            }
            
            if name:
                data["pinataMetadata"] = {"name": name}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"❌ Erreur épinglage {ipfs_hash}: {e}")
            return False
    
    async def unpin_file(self, ipfs_hash: str) -> bool:
        """
        Désépingle un fichier de Pinata
        """
        if not self.pinata_api_key or not self.pinata_secret:
            return False
        
        try:
            url = f"https://api.pinata.cloud/pinning/unpin/{ipfs_hash}"
            
            headers = {
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_api_key": self.pinata_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"❌ Erreur désépinglage {ipfs_hash}: {e}")
            return False
    
    async def list_pinned_files(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Liste les fichiers épinglés sur Pinata
        """
        if not self.pinata_api_key or not self.pinata_secret:
            return []
        
        try:
            url = f"https://api.pinata.cloud/data/pinList?pageLimit={limit}&pageOffset={offset}"
            
            headers = {
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_api_key": self.pinata_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('rows', [])
            
        except Exception as e:
            logger.error(f"❌ Erreur liste fichiers: {e}")
        
        return []
    
    def generate_file_hash(self, content: bytes) -> str:
        """
        Génère un hash SHA-256 du contenu
        """
        return hashlib.sha256(content).hexdigest()
    
    def encrypt_content(self, content: bytes) -> bytes:
        """
        Chiffre le contenu avec Fernet
        """
        return self.fernet.encrypt(content)
    
    def decrypt_content(self, encrypted_content: bytes) -> bytes:
        """
        Déchiffre le contenu avec Fernet
        """
        return self.fernet.decrypt(encrypted_content)
    
    def validate_ipfs_hash(self, ipfs_hash: str) -> bool:
        """
        Valide le format d'un hash IPFS
        """
        if not ipfs_hash:
            return False
        
        # Hash IPFS v0 (Qm...)
        if ipfs_hash.startswith('Qm') and len(ipfs_hash) == 46:
            return True
        
        # Hash IPFS v1 (baf...)
        if ipfs_hash.startswith('baf') and len(ipfs_hash) >= 50:
            return True
        
        return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de stockage Pinata
        """
        if not self.pinata_api_key or not self.pinata_secret:
            return {}
        
        try:
            url = "https://api.pinata.cloud/data/userPinnedDataTotal"
            
            headers = {
                "pinata_api_key": self.pinata_api_key,
                "pinata_secret_api_key": self.pinata_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
            
        except Exception as e:
            logger.error(f"❌ Erreur stats stockage: {e}")
        
        return {}

# Instance globale du service IPFS
ipfs_service = IPFSService()
