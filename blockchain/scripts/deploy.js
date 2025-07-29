const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Déploiement du Registre Foncier Décentralisé sur CELO...");

  // Récupération du déployeur
  const [deployer] = await ethers.getSigners();
  console.log("Déploiement avec le compte:", deployer.address);
  console.log("Solde du compte:", ethers.formatEther(await deployer.getBalance()), "CELO");

  // Configuration du contrat
  const contractName = "LandRegistry";
  const name = "Registre Foncier Décentralisé";
  const symbol = "RFD";

  console.log("\\n📋 Paramètres de déploiement:");
  console.log("- Nom:", name);
  console.log("- Symbole:", symbol);
  console.log("- Réseau:", hre.network.name);

  // Déploiement du contrat LandRegistry
  console.log("\\n🏗️ Déploiement du contrat principal...");
  const LandRegistry = await ethers.getContractFactory(contractName);
  const landRegistry = await LandRegistry.deploy(name, symbol);

  console.log("⏳ Attente de la confirmation...");
  await landRegistry.deployed();

  console.log("\\n✅ Contrat déployé avec succès!");
  console.log("📍 Adresse du contrat:", landRegistry.address);
  console.log("🔗 Transaction hash:", landRegistry.deployTransaction.hash);

  // Vérification de la configuration initiale
  console.log("\\n🔍 Vérification de la configuration...");
  const contractName_ = await landRegistry.name();
  const contractSymbol = await landRegistry.symbol();
  const totalSupply = await landRegistry.getTotalProperties();

  console.log("- Nom du contrat:", contractName_);
  console.log("- Symbole:", contractSymbol);
  console.log("- Propriétés enregistrées:", totalSupply.toString());

  // Sauvegarde des informations de déploiement
  const deploymentInfo = {
    network: hre.network.name,
    contractName: contractName,
    contractAddress: landRegistry.address,
    deployerAddress: deployer.address,
    deploymentTransaction: landRegistry.deployTransaction.hash,
    deploymentTimestamp: new Date().toISOString(),
    constructorArgs: [name, symbol],
    abi: JSON.parse(landRegistry.interface.format("json"))
  };

  // Création du dossier deployments s'il n'existe pas
  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  // Sauvegarde dans un fichier JSON
  const deploymentFile = path.join(deploymentsDir, `${hre.network.name}.json`);
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));

  console.log("\\n💾 Informations de déploiement sauvegardées dans:", deploymentFile);

  // Configuration des rôles initiaux (si en développement)
  if (hre.network.name === "localhost" || hre.network.name === "alfajores") {
    console.log("\\n👤 Configuration des rôles de développement...");
    
    try {
      // Rôles à attribuer
      const NOTARY_ROLE = await landRegistry.NOTARY_ROLE();
      const SURVEYOR_ROLE = await landRegistry.SURVEYOR_ROLE();
      const TAX_AUTHORITY_ROLE = await landRegistry.TAX_AUTHORITY_ROLE();

      // Attribution des rôles au déployeur pour les tests
      await landRegistry.grantRole(NOTARY_ROLE, deployer.address);
      await landRegistry.grantRole(SURVEYOR_ROLE, deployer.address);
      await landRegistry.grantRole(TAX_AUTHORITY_ROLE, deployer.address);

      console.log("✅ Rôles attribués au déployeur pour les tests");
    } catch (error) {
      console.log("⚠️ Erreur lors de l'attribution des rôles:", error.message);
    }
  }

  // Instructions post-déploiement
  console.log("\\n📝 Instructions post-déploiement:");
  console.log("1. Mettez à jour le fichier .env avec la nouvelle adresse du contrat:");
  console.log(`   CONTRACT_ADDRESS=${landRegistry.address}`);
  console.log("\\n2. Pour vérifier le contrat sur l'explorateur:");
  console.log(`   npx hardhat verify --network ${hre.network.name} ${landRegistry.address} "${name}" "${symbol}"`);
  console.log("\\n3. Configurez les rôles d'accès selon vos besoins");
  console.log("\\n4. Testez les fonctionnalités de base avant la mise en production");

  return landRegistry.address;
}

// Gestion des erreurs
main()
  .then((contractAddress) => {
    console.log("\\n🎉 Déploiement terminé avec succès!");
    console.log("📍 Adresse finale du contrat:", contractAddress);
    process.exit(0);
  })
  .catch((error) => {
    console.error("\\n❌ Erreur lors du déploiement:", error);
    process.exit(1);
  });
