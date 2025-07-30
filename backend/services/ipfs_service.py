"""
Service pour les interactions avec IPFS
Stockage et récupération de fichiers décentralisés
"""

import asyncio
import aiohttp
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from io import BytesIO
import base64

from config.settings import settings

logger = logging.getLogger(__name__)

class IPFSService:
    def __init__(self):
        self.api_url = settings.IPFS_API_URL or "http://localhost:5001/api/v0"
        self.gateway_url = settings.IPFS_GATEWAY or "https://ipfs.io/ipfs"
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Récupération de la session HTTP réutilisable"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session
    
    async def close(self):
        """Fermeture de la session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def upload_file(self, file_content: bytes, filename: str) -> str:
        """Upload d'un fichier sur IPFS"""
        try:
            session = await self._get_session()
            
            # Préparation des données multipart
            data = aiohttp.FormData()
            data.add_field('file', 
                          file_content, 
                          filename=filename,
                          content_type='application/octet-stream')
            
            # Upload vers IPFS
            async with session.post(f"{self.api_url}/add", data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Erreur IPFS upload: {error_text}")
                
                result = await response.json()
                ipfs_hash = result.get('Hash')
                
                if not ipfs_hash:
                    raise Exception("Hash IPFS non reçu")
                
                logger.info(f"Fichier {filename} uploadé sur IPFS: {ipfs_hash}")
                
                # Vérification optionnelle
                await self._verify_upload(ipfs_hash, len(file_content))
                
                return ipfs_hash
                
        except Exception as e:
            logger.error(f"Erreur lors de l'upload IPFS: {str(e)}")
            raise
    
    async def download_file(self, ipfs_hash: str) -> Optional[bytes]:
        """Téléchargement d'un fichier depuis IPFS"""
        try:
            session = await self._get_session()
            
            # Tentative avec l'API locale d'abord
            try:
                async with session.post(f"{self.api_url}/cat", 
                                      params={'arg': ipfs_hash}) as response:
                    if response.status == 200:
                        content = await response.read()
                        logger.info(f"Fichier {ipfs_hash} téléchargé via API locale")
                        return content
            except Exception as e:
                logger.warning(f"API locale IPFS indisponible: {str(e)}")
            
            # Fallback vers la gateway publique
            gateway_url = f"{self.gateway_url}/{ipfs_hash}"
            async with session.get(gateway_url) as response:
                if response.status == 200:
                    content = await response.read()
                    logger.info(f"Fichier {ipfs_hash} téléchargé via gateway publique")
                    return content
                else:
                    logger.error(f"Erreur gateway IPFS {response.status}: {await response.text()}")
                    return None
                    
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement IPFS: {str(e)}")
            return None
    
    async def store_metadata(self, metadata: Dict[str, Any]) -> str:
        """Stockage de métadonnées JSON sur IPFS"""
        try:
            # Conversion en JSON
            json_data = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            json_bytes = json_data.encode('utf-8')
            
            # Upload sur IPFS
            ipfs_hash = await self.upload_file(json_bytes, "metadata.json")
            
            logger.info(f"Métadonnées stockées sur IPFS: {ipfs_hash}")
            return ipfs_hash
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage des métadonnées: {str(e)}")
            raise
    
    async def get_metadata(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """Récupération de métadonnées JSON depuis IPFS"""
        try:
            content = await self.download_file(ipfs_hash)
            if not content:
                return None
            
            # Décodage JSON
            json_data = content.decode('utf-8')
            metadata = json.loads(json_data)
            
            logger.info(f"Métadonnées récupérées depuis IPFS: {ipfs_hash}")
            return metadata
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métadonnées: {str(e)}")
            return None
    
    async def upload_directory(self, files: Dict[str, bytes]) -> str:
        """Upload d'un répertoire de fichiers"""
        try:
            session = await self._get_session()
            
            # Préparation des données multipart
            data = aiohttp.FormData()
            for filename, content in files.items():
                data.add_field('file', 
                              content, 
                              filename=filename,
                              content_type='application/octet-stream')
            
            # Upload avec l'option recursive
            params = {'recursive': 'true', 'wrap-with-directory': 'true'}
            async with session.post(f"{self.api_url}/add", 
                                  data=data, 
                                  params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Erreur IPFS upload directory: {error_text}")
                
                # Traitement des résultats multiples
                response_text = await response.text()
                lines = response_text.strip().split('\n')
                
                directory_hash = None
                for line in lines:
                    result = json.loads(line)
                    if result.get('Name') == '':  # Le répertoire racine
                        directory_hash = result.get('Hash')
                
                if not directory_hash:
                    raise Exception("Hash du répertoire IPFS non reçu")
                
                logger.info(f"Répertoire uploadé sur IPFS: {directory_hash}")
                return directory_hash
                
        except Exception as e:
            logger.error(f"Erreur lors de l'upload du répertoire IPFS: {str(e)}")
            raise
    
    async def list_directory(self, ipfs_hash: str) -> List[Dict[str, Any]]:
        """Liste des fichiers dans un répertoire IPFS"""
        try:
            session = await self._get_session()
            
            async with session.post(f"{self.api_url}/ls", 
                                  params={'arg': ipfs_hash}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Erreur IPFS ls: {error_text}")
                
                result = await response.json()
                objects = result.get('Objects', [])
                
                files = []
                for obj in objects:
                    links = obj.get('Links', [])
                    for link in links:
                        files.append({
                            'name': link.get('Name'),
                            'hash': link.get('Hash'),
                            'size': link.get('Size'),
                            'type': link.get('Type')
                        })
                
                return files
                
        except Exception as e:
            logger.error(f"Erreur lors du listage IPFS: {str(e)}")
            return []
    
    async def pin_file(self, ipfs_hash: str) -> bool:
        """Épinglage d'un fichier pour éviter la suppression"""
        try:
            session = await self._get_session()
            
            async with session.post(f"{self.api_url}/pin/add", 
                                  params={'arg': ipfs_hash}) as response:
                if response.status == 200:
                    result = await response.json()
                    pinned_hash = result.get('Pins', [])
                    
                    if ipfs_hash in pinned_hash:
                        logger.info(f"Fichier {ipfs_hash} épinglé sur IPFS")
                        return True
                
                logger.warning(f"Échec de l'épinglage IPFS: {await response.text()}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'épinglage IPFS: {str(e)}")
            return False
    
    async def unpin_file(self, ipfs_hash: str) -> bool:
        """Dés-épinglage d'un fichier"""
        try:
            session = await self._get_session()
            
            async with session.post(f"{self.api_url}/pin/rm", 
                                  params={'arg': ipfs_hash}) as response:
                if response.status == 200:
                    logger.info(f"Fichier {ipfs_hash} dés-épinglé sur IPFS")
                    return True
                
                logger.warning(f"Échec du dés-épinglage IPFS: {await response.text()}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors du dés-épinglage IPFS: {str(e)}")
            return False
    
    async def get_file_stats(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """Statistiques d'un fichier IPFS"""
        try:
            session = await self._get_session()
            
            async with session.post(f"{self.api_url}/object/stat", 
                                  params={'arg': ipfs_hash}) as response:
                if response.status == 200:
                    stats = await response.json()
                    logger.info(f"Stats récupérées pour {ipfs_hash}")
                    return stats
                
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats IPFS: {str(e)}")
            return None
    
    async def _verify_upload(self, ipfs_hash: str, expected_size: int) -> bool:
        """Vérification de l'upload"""
        try:
            # Tentative de récupération du fichier
            content = await self.download_file(ipfs_hash)
            if not content:
                logger.warning(f"Impossible de vérifier l'upload {ipfs_hash}")
                return False
            
            # Vérification de la taille
            if len(content) != expected_size:
                logger.error(f"Taille incorrecte pour {ipfs_hash}: {len(content)} vs {expected_size}")
                return False
            
            logger.info(f"Upload vérifié avec succès: {ipfs_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification: {str(e)}")
            return False
    
    async def get_node_info(self) -> Optional[Dict[str, Any]]:
        """Informations sur le noeud IPFS"""
        try:
            session = await self._get_session()
            
            async with session.post(f"{self.api_url}/id") as response:
                if response.status == 200:
                    info = await response.json()
                    return info
                
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos noeud: {str(e)}")
            return None
    
    async def health_check(self) -> bool:
        """Vérification de la santé du service IPFS"""
        try:
            node_info = await self.get_node_info()
            if node_info:
                logger.info("Service IPFS opérationnel")
                return True
            
            logger.warning("Service IPFS indisponible")
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors du health check IPFS: {str(e)}")
            return False
    
    def get_public_url(self, ipfs_hash: str) -> str:
        """URL publique pour accéder à un fichier IPFS"""
        return f"{self.gateway_url}/{ipfs_hash}"
    
    async def calculate_file_hash(self, content: bytes) -> str:
        """Calcul du hash IPFS d'un contenu (simulation)"""
        try:
            # Simulation du hash IPFS (utilisé pour la validation)
            # En réalité, IPFS utilise un algorithme plus complexe
            sha256_hash = hashlib.sha256(content).hexdigest()
            return f"Qm{sha256_hash[:44]}"  # Format approximatif
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul de hash: {str(e)}")
            raise
    
    async def batch_upload(self, files: List[Dict[str, Union[str, bytes]]]) -> Dict[str, str]:
        """Upload en lot de plusieurs fichiers"""
        try:
            results = {}
            
            for file_info in files:
                filename = file_info.get('filename', 'unknown')
                content = file_info.get('content', b'')
                
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                try:
                    ipfs_hash = await self.upload_file(content, filename)
                    results[filename] = ipfs_hash
                    
                    # Épinglage automatique pour les fichiers importants
                    if file_info.get('pin', False):
                        await self.pin_file(ipfs_hash)
                        
                except Exception as e:
                    logger.error(f"Erreur upload {filename}: {str(e)}")
                    results[filename] = f"ERROR: {str(e)}"
            
            logger.info(f"Upload en lot terminé: {len(results)} fichiers traités")
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'upload en lot: {str(e)}")
            raise
    
    async def create_property_archive(
        self, 
        property_data: Dict[str, Any], 
        documents: List[Dict[str, Any]]
    ) -> str:
        """Création d'une archive complète d'une propriété"""
        try:
            # Préparation des fichiers à archiver
            files = {}
            
            # Métadonnées de la propriété
            files['property.json'] = json.dumps(property_data, ensure_ascii=False, indent=2).encode('utf-8')
            
            # Documents (si disponibles)
            for i, doc in enumerate(documents):
                if doc.get('content'):
                    ext = doc.get('filename', '').split('.')[-1] or 'bin'
                    files[f"document_{i}.{ext}"] = doc['content']
            
            # Index des fichiers
            index = {
                'property_id': property_data.get('property_id'),
                'created_at': property_data.get('registration_date'),
                'files': list(files.keys()),
                'archive_version': '1.0'
            }
            files['index.json'] = json.dumps(index, ensure_ascii=False, indent=2).encode('utf-8')
            
            # Upload du répertoire
            archive_hash = await self.upload_directory(files)
            logger.info(f"Archive propriété créée: {archive_hash}")
            
            return archive_hash
            
        except Exception as e:
            logger.error(f"Erreur lors de la création d'archive: {str(e)}")
            raise
    
    # Méthodes pour la compatibilité avec les anciens appels
    async def add_json(self, data: Dict[str, Any]) -> str:
        """Alias pour store_metadata"""
        return await self.store_metadata(data)
    
    async def get_json(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """Alias pour get_metadata"""
        return await self.get_metadata(ipfs_hash)
    
    async def cat(self, ipfs_hash: str) -> Optional[bytes]:
        """Alias pour download_file"""
        return await self.download_file(ipfs_hash)