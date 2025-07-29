# 🏠 Registre Foncier Décentralisé (RFD) - CELO

## 🌟 Vue d'ensemble

Registre foncier décentralisé sur blockchain CELO permettant l'enregistrement, la traçabilité et la vérification transparente des propriétés foncières.

## 🏗️ Architecture Modulaire

```
registre-foncier-celo/
├── 📁 blockchain/          # Smart contracts CELO
├── 📁 backend/             # API FastAPI + PostgreSQL
├── 📁 frontend/            # Interface React
├── 📁 database/            # Schémas et migrations SQL
├── 📁 docs/                # Documentation technique
├── 📁 scripts/             # Scripts d'automatisation
└── 📁 config/              # Configurations environnement
```

## 🚀 Démarrage Rapide

### Prérequis
- Node.js 18+
- Python 3.9+
- PostgreSQL 14+ avec PostGIS
- Docker (optionnel)

### Installation

```bash
git clone https://github.com/Kyac99/registre-foncier-celo.git
cd registre-foncier-celo

# Installation des dépendances
npm run install:all

# Configuration de la base de données
npm run db:setup

# Déploiement des smart contracts (testnet)
npm run blockchain:deploy:testnet

# Lancement en mode développement
npm run dev
```

## 🌐 Environnements

- **Développement**: Alfajores Testnet
- **Production**: CELO Mainnet

## 📚 Documentation

- [Guide de déploiement](docs/deployment.md)
- [API Reference](docs/api.md)
- [Architecture technique](docs/architecture.md)
- [Guide utilisateur](docs/user-guide.md)

## 🔐 Sécurité

- Smart contracts audités
- Chiffrement des données sensibles
- Authentification multi-facteurs
- Sauvegarde automatique

## 🤝 Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/new-feature`)
3. Commit (`git commit -m 'Add new feature'`)
4. Push (`git push origin feature/new-feature`)
5. Ouvrir une Pull Request

## 📄 Licence

MIT License - voir [LICENSE](LICENSE) pour les détails.

## 📞 Support

Pour toute question ou support technique, ouvrir une [issue](https://github.com/Kyac99/registre-foncier-celo/issues).
