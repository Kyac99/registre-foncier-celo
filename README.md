# 🏠 Registre Foncier Décentralisé (RFD) - MVP CELO

## 🌟 Vue d'ensemble

Le Registre Foncier Décentralisé est une solution innovante de gestion des propriétés foncières utilisant la blockchain CELO et le stockage décentralisé IPFS. Ce MVP offre une plateforme sécurisée, transparente et accessible pour l'enregistrement, la vérification et la recherche de propriétés foncières au Burkina Faso.

## ✨ Fonctionnalités Principales

### 🔐 Enregistrement Sécurisé
- **Enregistrement multi-étapes** : Interface intuitive en 3 étapes
- **Géolocalisation automatique** : Coordonnées GPS précises
- **Upload de documents** : Stockage décentralisé sur IPFS
- **Validation blockchain** : Horodatage cryptographique sur CELO

### 🔍 Recherche Avancée
- **Filtres multiples** : Type, localisation, superficie, prix
- **Recherche géographique** : Rayon de proximité configurable
- **Suggestions intelligentes** : Auto-complétion en temps réel
- **Export de données** : Formats CSV, XLSX, JSON

### 📄 Gestion Documentaire
- **Stockage IPFS** : Documents cryptographiquement vérifiables
- **Types multiples** : Actes, plans, permis, certificats
- **Vérification par autorités** : Workflow d'approbation
- **Historique complet** : Traçabilité des modifications

### 📊 Tableau de Bord
- **Métriques en temps réel** : Statistiques du registre
- **Visualisations avancées** : Graphiques interactifs
- **Activités récentes** : Suivi des actions utilisateurs
- **Alertes automatiques** : Notifications pour les administrateurs

## 🏗️ Architecture Technique

```
registre-foncier-celo/
├── 🚀 backend/                 # API FastAPI + PostgreSQL
│   ├── routers/               # Endpoints REST
│   │   ├── blockchain.py      # Interactions CELO
│   │   ├── documents.py       # Gestion IPFS
│   │   ├── properties.py      # CRUD propriétés
│   │   ├── search.py          # Recherche avancée
│   │   └── users.py           # Authentification
│   ├── services/              # Logique métier
│   │   ├── blockchain_service.py
│   │   ├── ipfs_service.py
│   │   └── search_service.py
│   ├── schemas/               # Validation Pydantic
│   └── config/                # Configuration
├── ⚛️ frontend/                # Interface React + TypeScript
│   ├── components/            # Composants réutilisables
│   │   ├── Dashboard.tsx      # Tableau de bord
│   │   ├── PropertyRegistration.tsx
│   │   ├── PropertySearch.tsx
│   │   ├── PropertyDetails.tsx
│   │   └── WalletConnect.tsx
│   ├── services/              # Services API
│   └── contexts/              # Contextes React
├── ⛓️ blockchain/              # Smart Contracts Solidity
│   ├── contracts/
│   │   └── LandRegistry.sol   # Contrat principal
│   ├── scripts/               # Déploiement
│   └── hardhat.config.js
├── 🗄️ database/               # Schémas PostgreSQL
│   ├── migrations/
│   └── schemas/
└── 🐳 docker-compose.yml      # Orchestration services
```

## 🚀 Démarrage Rapide

### Prérequis
- **Node.js** 18+ et npm/yarn
- **Python** 3.9+ et pip
- **PostgreSQL** 14+ avec extension PostGIS
- **Docker & Docker Compose** (optionnel)

### Installation

1. **Clonage du repository**
```bash
git clone https://github.com/Kyac99/registre-foncier-celo.git
cd registre-foncier-celo
```

2. **Configuration de l'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

3. **Installation des dépendances**
```bash
# Installation globale
npm run install:all

# Ou manuellement
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
cd ../blockchain && npm install
```

4. **Base de données**
```bash
# Avec Docker
docker-compose up -d postgres

# Configuration manuelle
npm run db:setup
npm run db:migrate
```

5. **Smart Contracts**
```bash
# Déploiement sur Alfajores Testnet
cd blockchain
npm run deploy:testnet
```

6. **Lancement des services**
```bash
# Avec Docker (recommandé)
docker-compose up -d

# Ou manuellement
npm run dev
```

L'application sera accessible sur :
- **Frontend** : http://localhost:3000
- **API Backend** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs

## 🔧 Configuration

### Variables d'environnement (.env)

```env
# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/registre_foncier
POSTGRES_DB=registre_foncier
POSTGRES_USER=rfd_user
POSTGRES_PASSWORD=secure_password

# Backend API
BACKEND_PORT=8000
API_SECRET_KEY=your-super-secret-key-here
DEBUG=true
ENVIRONMENT=development

# Blockchain CELO
CELO_NETWORK=alfajores
CELO_RPC_URL=https://alfajores-forno.celo-testnet.org
CONTRACT_ADDRESS=0x...
PRIVATE_KEY=0x...

# IPFS
IPFS_API_URL=http://localhost:5001/api/v0
IPFS_GATEWAY=https://ipfs.io/ipfs

# CORS et sécurité
CORS_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost", "127.0.0.1"]

# Features
BLOCKCHAIN_DOCUMENT_REGISTRATION=true
```

### Configuration PostgreSQL avec PostGIS

```sql
-- Extension géospatiale requise
CREATE EXTENSION IF NOT EXISTS postgis;

-- Utilisateur de base de données
CREATE USER rfd_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE registre_foncier TO rfd_user;
```

## 🌐 Déploiement

### Production avec Docker

```bash
# Construction des images
docker-compose -f docker-compose.prod.yml build

# Déploiement
docker-compose -f docker-compose.prod.yml up -d

# Mise à l'échelle
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

### Variables de production

```env
ENVIRONMENT=production
DEBUG=false
CELO_NETWORK=celo
DATABASE_URL=postgresql://user:password@db-host:5432/registre_foncier
CORS_ORIGINS=["https://your-domain.com"]
```

## 🧪 Tests

```bash
# Tests backend
cd backend
pytest tests/ -v --cov=.

# Tests frontend
cd frontend
npm test

# Tests d'intégration
npm run test:integration

# Tests smart contracts
cd blockchain
npm test
```

## 📊 Monitoring & Métriques

### Endpoints de santé
- **API Health** : `GET /health`
- **Blockchain Status** : `GET /api/v1/blockchain/status`
- **Database Status** : Inclus dans `/health`

### Métriques disponibles
- Nombre total de propriétés
- Taux de vérification
- Performance des requêtes
- Utilisation IPFS
- Status blockchain

## 🔐 Sécurité

### Mesures implémentées
- **Authentification JWT** avec expiration
- **Validation des données** avec Pydantic
- **CORS configuré** pour les domaines autorisés
- **Hash cryptographique** des documents
- **Signature blockchain** des transactions
- **Chiffrement des clés privées**

### Recommandations
- Utilisez HTTPS en production
- Configurez un pare-feu approprié
- Sauvegardez régulièrement la base de données
- Monitorer les logs d'erreur

## 🤝 Contribution

### Workflow de développement

1. **Fork** du repository
2. **Création** d'une branche feature
```bash
git checkout -b feature/nouvelle-fonctionnalite
```
3. **Développement** avec tests
4. **Commit** avec messages conventionnels
```bash
git commit -m "feat: ajout de la recherche par proximité"
```
5. **Push** et création d'une Pull Request

### Standards de code
- **Python** : PEP 8, Black, isort
- **TypeScript** : ESLint, Prettier
- **Solidity** : Solhint
- **Tests** : Couverture > 80%

## 📖 Documentation API

La documentation interactive complète est disponible sur :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

### Endpoints principaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/properties` | POST | Enregistrer une propriété |
| `/api/v1/properties/{id}` | GET | Détails d'une propriété |
| `/api/v1/search/properties` | GET | Recherche avancée |
| `/api/v1/documents/upload` | POST | Upload de document |
| `/api/v1/blockchain/status` | GET | Status blockchain |

## 🛠️ Scripts Utiles

```bash
# Développement
npm run dev              # Lancement dev complet
npm run dev:backend      # Backend uniquement
npm run dev:frontend     # Frontend uniquement

# Base de données
npm run db:setup         # Configuration initiale
npm run db:migrate       # Migrations
npm run db:seed          # Données de test

# Blockchain
npm run blockchain:deploy:testnet   # Déploiement testnet
npm run blockchain:deploy:mainnet   # Déploiement mainnet
npm run blockchain:verify           # Vérification contrats

# Qualité
npm run lint             # Linting global
npm run test:all         # Tests complets
npm run build            # Build production

# Maintenance
npm run backup:db        # Sauvegarde base
npm run clean            # Nettoyage
```

## 🌍 Réseaux Supportés

| Réseau | Chain ID | RPC URL | Explorateur |
|--------|----------|---------|-------------|
| **Alfajores (Testnet)** | 44787 | https://alfajores-forno.celo-testnet.org | https://alfajores-blockscout.celo-testnet.org |
| **CELO (Mainnet)** | 42220 | https://forno.celo.org | https://explorer.celo.org |

## 📞 Support

- **Issues GitHub** : [Ouvrir une issue](https://github.com/Kyac99/registre-foncier-celo/issues)
- **Discussions** : [GitHub Discussions](https://github.com/Kyac99/registre-foncier-celo/discussions)
- **Documentation** : [Wiki du projet](https://github.com/Kyac99/registre-foncier-celo/wiki)

## 📄 Licence

Ce projet est sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- **CELO Foundation** pour l'infrastructure blockchain
- **IPFS** pour le stockage décentralisé
- **FastAPI** pour le framework backend
- **React** et **Tailwind CSS** pour l'interface utilisateur
- **Communauté open source** pour les outils et bibliothèques

---

**Développé avec ❤️ pour la digitalisation du foncier en Afrique de l'Ouest**

*Registre Foncier Décentralisé - Transparence, Sécurité, Accessibilité*