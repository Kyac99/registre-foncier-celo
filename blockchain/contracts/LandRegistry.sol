// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title LandRegistry
 * @dev Registre Foncier Décentralisé sur CELO
 * @author Kyac99
 */
contract LandRegistry is ERC721, ERC721URIStorage, AccessControl, ReentrancyGuard, Pausable {
    using Counters for Counters.Counter;

    // Rôles pour le contrôle d'accès
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant NOTARY_ROLE = keccak256("NOTARY_ROLE");
    bytes32 public constant SURVEYOR_ROLE = keccak256("SURVEYOR_ROLE");
    bytes32 public constant TAX_AUTHORITY_ROLE = keccak256("TAX_AUTHORITY_ROLE");

    // Compteur pour les IDs de propriétés
    Counters.Counter private _propertyIdCounter;

    // Structure pour représenter une propriété
    struct Property {
        uint256 id;
        string location;
        string coordinates; // Coordonnées GPS ou GeoJSON
        uint256 area; // Surface en m²
        uint256 value; // Valeur estimée en cUSD (wei)
        PropertyType propertyType;
        PropertyStatus status;
        uint256 registrationDate;
        uint256 lastTransferDate;
        string documentHash; // Hash IPFS du document officiel
        address registrar; // Notaire qui a enregistré
        bool verified; // Vérifié par un géomètre
    }

    // Types de propriétés
    enum PropertyType {
        RESIDENTIAL,
        COMMERCIAL,
        INDUSTRIAL,
        AGRICULTURAL,
        FOREST,
        OTHER
    }

    // Statuts de propriétés
    enum PropertyStatus {
        ACTIVE,
        DISPUTED,
        FROZEN,
        TRANSFERRED
    }

    // Mapping des propriétés
    mapping(uint256 => Property) public properties;
    mapping(string => uint256) private _locationToPropertyId;
    mapping(address => uint256[]) private _ownerProperties;

    // Événements
    event PropertyRegistered(
        uint256 indexed propertyId,
        address indexed owner,
        string location,
        uint256 value,
        address registrar
    );

    event PropertyTransferred(
        uint256 indexed propertyId,
        address indexed from,
        address indexed to,
        uint256 value
    );

    event PropertyVerified(
        uint256 indexed propertyId,
        address indexed surveyor,
        bool verified
    );

    event PropertyStatusChanged(
        uint256 indexed propertyId,
        PropertyStatus oldStatus,
        PropertyStatus newStatus
    );

    event PropertyValueUpdated(
        uint256 indexed propertyId,
        uint256 oldValue,
        uint256 newValue,
        address updater
    );

    constructor(
        string memory name,
        string memory symbol
    ) ERC721(name, symbol) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ADMIN_ROLE, msg.sender);
    }

    /**
     * @dev Enregistre une nouvelle propriété
     * @param owner Propriétaire de la parcelle
     * @param location Localisation (adresse ou description)
     * @param coordinates Coordonnées GPS ou GeoJSON
     * @param area Surface en m²
     * @param value Valeur estimée en cUSD
     * @param propertyType Type de propriété
     * @param documentHash Hash IPFS du document officiel
     * @param tokenURI URI des métadonnées NFT
     */
    function registerProperty(
        address owner,
        string memory location,
        string memory coordinates,
        uint256 area,
        uint256 value,
        PropertyType propertyType,
        string memory documentHash,
        string memory tokenURI
    ) external onlyRole(NOTARY_ROLE) whenNotPaused returns (uint256) {
        require(owner != address(0), "Invalid owner address");
        require(bytes(location).length > 0, "Location cannot be empty");
        require(area > 0, "Area must be greater than 0");
        require(_locationToPropertyId[location] == 0, "Property already exists at this location");

        _propertyIdCounter.increment();
        uint256 propertyId = _propertyIdCounter.current();

        // Mint du NFT pour le propriétaire
        _safeMint(owner, propertyId);
        _setTokenURI(propertyId, tokenURI);

        // Création de la propriété
        properties[propertyId] = Property({
            id: propertyId,
            location: location,
            coordinates: coordinates,
            area: area,
            value: value,
            propertyType: propertyType,
            status: PropertyStatus.ACTIVE,
            registrationDate: block.timestamp,
            lastTransferDate: block.timestamp,
            documentHash: documentHash,
            registrar: msg.sender,
            verified: false
        });

        // Mise à jour des mappings
        _locationToPropertyId[location] = propertyId;
        _ownerProperties[owner].push(propertyId);

        emit PropertyRegistered(propertyId, owner, location, value, msg.sender);
        return propertyId;
    }

    /**
     * @dev Transfère une propriété vers un nouveau propriétaire
     * @param propertyId ID de la propriété
     * @param newOwner Nouveau propriétaire
     * @param newValue Nouvelle valeur de transaction
     */
    function transferProperty(
        uint256 propertyId,
        address newOwner,
        uint256 newValue
    ) external onlyRole(NOTARY_ROLE) whenNotPaused {
        require(_exists(propertyId), "Property does not exist");
        require(newOwner != address(0), "Invalid new owner address");
        require(properties[propertyId].status == PropertyStatus.ACTIVE, "Property is not transferable");

        address currentOwner = ownerOf(propertyId);
        require(currentOwner != newOwner, "Cannot transfer to same owner");

        // Mise à jour de la propriété
        properties[propertyId].value = newValue;
        properties[propertyId].lastTransferDate = block.timestamp;
        properties[propertyId].status = PropertyStatus.TRANSFERRED;

        // Mise à jour des listes de propriétés
        _removePropertyFromOwner(currentOwner, propertyId);
        _ownerProperties[newOwner].push(propertyId);

        // Transfert du NFT
        _transfer(currentOwner, newOwner, propertyId);

        // Rétablir le statut actif après transfert
        properties[propertyId].status = PropertyStatus.ACTIVE;

        emit PropertyTransferred(propertyId, currentOwner, newOwner, newValue);
    }

    /**
     * @dev Vérifie une propriété (par un géomètre)
     * @param propertyId ID de la propriété
     * @param isVerified Statut de vérification
     */
    function verifyProperty(
        uint256 propertyId,
        bool isVerified
    ) external onlyRole(SURVEYOR_ROLE) whenNotPaused {
        require(_exists(propertyId), "Property does not exist");
        
        properties[propertyId].verified = isVerified;
        
        emit PropertyVerified(propertyId, msg.sender, isVerified);
    }

    /**
     * @dev Change le statut d'une propriété
     * @param propertyId ID de la propriété
     * @param newStatus Nouveau statut
     */
    function changePropertyStatus(
        uint256 propertyId,
        PropertyStatus newStatus
    ) external onlyRole(ADMIN_ROLE) whenNotPaused {
        require(_exists(propertyId), "Property does not exist");
        
        PropertyStatus oldStatus = properties[propertyId].status;
        properties[propertyId].status = newStatus;
        
        emit PropertyStatusChanged(propertyId, oldStatus, newStatus);
    }

    /**
     * @dev Met à jour la valeur d'une propriété
     * @param propertyId ID de la propriété
     * @param newValue Nouvelle valeur
     */
    function updatePropertyValue(
        uint256 propertyId,
        uint256 newValue
    ) external onlyRole(TAX_AUTHORITY_ROLE) whenNotPaused {
        require(_exists(propertyId), "Property does not exist");
        require(newValue > 0, "Value must be greater than 0");
        
        uint256 oldValue = properties[propertyId].value;
        properties[propertyId].value = newValue;
        
        emit PropertyValueUpdated(propertyId, oldValue, newValue, msg.sender);
    }

    /**
     * @dev Récupère une propriété par son ID
     * @param propertyId ID de la propriété
     */
    function getProperty(uint256 propertyId) external view returns (Property memory) {
        require(_exists(propertyId), "Property does not exist");
        return properties[propertyId];
    }

    /**
     * @dev Récupère l'ID d'une propriété par sa localisation
     * @param location Localisation de la propriété
     */
    function getPropertyIdByLocation(string memory location) external view returns (uint256) {
        return _locationToPropertyId[location];
    }

    /**
     * @dev Récupère toutes les propriétés d'un propriétaire
     * @param owner Adresse du propriétaire
     */
    function getPropertiesByOwner(address owner) external view returns (uint256[] memory) {
        return _ownerProperties[owner];
    }

    /**
     * @dev Récupère le nombre total de propriétés enregistrées
     */
    function getTotalProperties() external view returns (uint256) {
        return _propertyIdCounter.current();
    }

    /**
     * @dev Pause le contrat (fonction d'urgence)
     */
    function pause() external onlyRole(ADMIN_ROLE) {
        _pause();
    }

    /**
     * @dev Débloque le contrat
     */
    function unpause() external onlyRole(ADMIN_ROLE) {
        _unpause();
    }

    /**
     * @dev Retire une propriété de la liste d'un propriétaire
     * @param owner Propriétaire
     * @param propertyId ID de la propriété
     */
    function _removePropertyFromOwner(address owner, uint256 propertyId) private {
        uint256[] storage ownerProps = _ownerProperties[owner];
        for (uint256 i = 0; i < ownerProps.length; i++) {
            if (ownerProps[i] == propertyId) {
                ownerProps[i] = ownerProps[ownerProps.length - 1];
                ownerProps.pop();
                break;
            }
        }
    }

    // Overrides nécessaires pour la compatibilité des interfaces
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal override whenNotPaused {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
    }

    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }

    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
